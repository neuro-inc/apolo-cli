import glob as globmodule  # avoid conflict with subcommand "glob"
import logging
import sys
from collections.abc import Awaitable, Callable, Sequence

import click
from rich.text import Text
from yarl import URL

from apolo_sdk import (
    Bucket,
    Client,
    FileFilter,
    FileStatusType,
    IllegalArgumentError,
    ResourceNotFound,
)

from .click_types import (
    BUCKET,
    BUCKET_CREDENTIAL,
    BUCKET_NAME,
    CLUSTER,
    ORG,
    PROJECT,
    PlatformURIType,
)
from .const import EX_OSFILE
from .formatters.blob_storage import (
    BaseBlobFormatter,
    LongBlobFormatter,
    SimpleBlobFormatter,
)
from .formatters.bucket_credentials import (
    BaseBucketCredentialsFormatter,
    BucketCredentialFormatter,
    BucketCredentialsFormatter,
    SimpleBucketCredentialsFormatter,
)
from .formatters.buckets import (
    BaseBucketsFormatter,
    BucketFormatter,
    BucketsFormatter,
    SimpleBucketsFormatter,
)
from .formatters.storage import DeleteProgress, create_storage_progress, get_painter
from .formatters.utils import URIFormatter, get_datetime_formatter, uri_formatter
from .parse_utils import parse_timedelta
from .root import Root
from .storage import calc_filters, calc_ignore_file_names, filter_option
from .utils import (
    argument,
    command,
    format_size,
    group,
    option,
    resolve_bucket,
    resolve_bucket_credential,
)

log = logging.getLogger(__name__)


@group(name="blob")
def blob_storage() -> None:
    """
    Blob storage operations.
    """


# Bucket level commands


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Look on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Look on a specified org (the current org by default).",
)
@option("--all-orgs", is_flag=True, default=False, help="Show buckets in all orgs.")
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
@option(
    "--all-projects", is_flag=True, default=False, help="Show buckets in all projects."
)
@option("--full-uri", is_flag=True, help="Output full bucket URI.")
@option("--long-format", is_flag=True, help="Output all info about bucket.")
async def lsbucket(
    root: Root,
    full_uri: bool,
    long_format: bool,
    cluster: str | None,
    org: str | None,
    all_orgs: bool,
    project: str | None,
    all_projects: bool,
) -> None:
    """
    List buckets.
    """
    if root.quiet:
        buckets_fmtr: BaseBucketsFormatter = SimpleBucketsFormatter()
    else:
        if full_uri:
            uri_fmtr: URIFormatter = str
        else:
            uri_fmtr = uri_formatter(
                project_name=root.client.config.project_name_or_raise,
                cluster_name=root.client.cluster_name,
                org_name=root.client.config.org_name,
            )
        buckets_fmtr = BucketsFormatter(
            uri_fmtr,
            datetime_formatter=get_datetime_formatter(root.iso_datetime_format),
            long_format=long_format,
        )

    if all_orgs:
        org_name = None
    else:
        org_name = org

    if all_projects:
        project_name = None
    else:
        project_name = project or root.client.config.project_name_or_raise

    buckets = []
    with root.status("Fetching buckets") as status:
        async with root.client.buckets.list(
            cluster_name=cluster,
            org_name=org_name,
            project_name=project_name,
        ) as it:
            async for bucket in it:
                buckets.append(bucket)
                status.update(f"Fetching buckets ({len(buckets)} loaded)")

    with root.pager():
        root.print(buckets_fmtr(buckets))


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform in a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Perform in a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Perform in a specified project (the current project by default).",
)
@option(
    "--name",
    type=BUCKET_NAME,
    metavar="NAME",
    help="Optional bucket name",
    default=None,
)
async def mkbucket(
    root: Root,
    name: str | None = None,
    cluster: str | None = None,
    org: str | None = None,
    project: str | None = None,
) -> None:
    """
    Create a new bucket.
    """
    org_name = org
    bucket = await root.client.buckets.create(
        name=name,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )
    bucket_fmtr = BucketFormatter(
        str, datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    with root.pager():
        root.print(bucket_fmtr(bucket))


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform in a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Perform in a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Perform in a specified project (the current project by default).",
)
@option(
    "--name",
    type=BUCKET_NAME,
    metavar="NAME",
    help="Optional bucket name",
    default=None,
)
@option(
    "--provider",
    type=click.Choice(["aws", "gcp", "azure"], case_sensitive=False),
    metavar="PROVIDER",
    help="Bucket provider that hosts bucket",
    required=True,
)
@option(
    "--provider-bucket-name",
    type=str,
    metavar="EXTERNAL_NAME",
    help="Name of bucket (or container in case of Azure) inside the provider",
    required=True,
)
@option(
    "--aws-access-key-id",
    type=str,
    metavar="AWS_ACCESS_KEY_ID",
    help="AWS access_key_id to use to access the bucket. "
    " Required when PROVIDER is 'aws'",
    default=None,
)
@option(
    "--aws-secret-access-key",
    type=str,
    metavar="AWS_SECRET_ACCESS_KEY",
    help="AWS secret_access_key to use to access the bucket. "
    "Required when PROVIDER is 'aws'",
    default=None,
)
@option(
    "--aws-region-name",
    type=str,
    metavar="AWS_REGION",
    help="AWS region to use to access the bucket.",
    default="us-east-1",
)
@option(
    "--aws-endpoint-url",
    type=str,
    metavar="AWS_ENDPOINT",
    help="AWS endpoint to use to access the bucket. "
    "Usually you need to set this if "
    "you use non-AWS S3 compatible provider",
    default=None,
)
@option(
    "--azure-storage-account-url",
    type=str,
    metavar="AZURE_STORAGE_ACCOUNT_URL",
    help="Azure account url. Usually it has following format: "
    "https://<account_id>.blob.core.windows.net "
    "Required when PROVIDER is 'azure'",
    default=None,
)
@option(
    "--azure-storage-sas-token",
    type=str,
    metavar="AZURE_SAS",
    help="Azure shared access signature token that grants access to imported bucket. "
    "Either this or AZURE_STORAGE_CREDENTIAL is required when PROVIDER is 'azure'",
    default=None,
)
@option(
    "--azure-storage-credential",
    type=str,
    metavar="AZURE_STORAGE_CREDENTIAL",
    help="Azure storage credential that grants access to imported bucket. "
    "Either this or AZURE_SAS is required when PROVIDER is 'azure'",
    default=None,
)
@option(
    "--gcp-sa-credential",
    type=str,
    metavar="GCP_SA_CREDNETIAL",
    help="GCP service account credential in form of base64 encoded json "
    "string that grants access to imported bucket. "
    "Required when PROVIDER is 'gcp'",
    default=None,
)
async def importbucket(
    root: Root,
    provider: str,
    provider_bucket_name: str,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_region_name: str = "us-east-1",
    aws_endpoint_url: str | None = None,
    azure_storage_account_url: str | None = None,
    azure_storage_sas_token: str | None = None,
    azure_storage_credential: str | None = None,
    gcp_sa_credential: str | None = None,
    name: str | None = None,
    cluster: str | None = None,
    org: str | None = None,
    project: str | None = None,
) -> None:
    """
    Import an existing bucket.
    """
    org_name = org
    provider_type = Bucket.Provider(provider)
    credentials = {}
    if provider_type == Bucket.Provider.AWS:
        if aws_access_key_id is None:
            raise ValueError("--aws-access-key-id is required when PROVIDER is 'aws'")
        if aws_secret_access_key is None:
            raise ValueError(
                "--aws-secret-access-key is required when PROVIDER is 'aws'"
            )
        credentials["access_key_id"] = aws_access_key_id
        credentials["secret_access_key"] = aws_secret_access_key
        credentials["region_name"] = aws_region_name
        if aws_endpoint_url:
            credentials["endpoint_url"] = aws_endpoint_url
    elif provider_type == Bucket.Provider.AZURE:
        if azure_storage_account_url is None:
            raise ValueError(
                "--azure-storage-account-url is required when PROVIDER is 'azure'"
            )
        credentials["storage_endpoint"] = azure_storage_account_url
        if azure_storage_credential is not None:
            credentials["credential"] = azure_storage_credential
        elif azure_storage_sas_token is not None:
            credentials["sas_token"] = azure_storage_sas_token
        else:
            raise ValueError(
                "Either --azure-storage-credential or --azure-storage-sas-token "
                "should be specified when PROVIDER is 'azure'"
            )
    elif provider_type == Bucket.Provider.GCP:
        if gcp_sa_credential is None:
            raise ValueError("--gcp-sa-credential is required when PROVIDER is 'gcp'")
        credentials["key_data"] = gcp_sa_credential
    else:
        raise ValueError(
            f"Importing of buckets with provider {provider} is not supported"
        )

    bucket = await root.client.buckets.import_external(
        provider=provider_type,
        provider_bucket_name=provider_bucket_name,
        credentials=credentials,
        name=name,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )
    bucket_fmtr = BucketFormatter(
        str, datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    with root.pager():
        root.print(bucket_fmtr(bucket))


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Look on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Look on a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
@argument("bucket", type=BUCKET)
@option("--full-uri", is_flag=True, help="Output full bucket URI.")
async def statbucket(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    bucket: str,
    full_uri: bool,
) -> None:
    """
    Get bucket BUCKET.
    """
    org_name = org
    bucket_obj = await root.client.buckets.get(
        bucket,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )
    if bucket_obj.imported:
        bc = await root.client.buckets.request_tmp_credentials(
            bucket,
            cluster_name=bucket_obj.cluster_name,
            org_name=bucket_obj.org_name,
            project_name=bucket_obj.project_name,
        )
        credentials = bc.credentials
    else:
        credentials = None
    if full_uri:
        uri_fmtr: URIFormatter = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=cluster or root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    bucket_fmtr = BucketFormatter(
        uri_fmtr, datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    with root.pager():
        root.print(bucket_fmtr(bucket_obj, credentials))


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Look on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Look on a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
@argument("bucket", type=BUCKET)
async def du(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    bucket: str,
) -> None:
    """
    Get storage usage for BUCKET.
    """
    org_name = org
    bucket_obj = await root.client.buckets.get(
        bucket,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )

    bucket_str = bucket_obj.name or bucket_obj.id
    if bucket_obj.owner != root.client.config.username:
        bucket_str += f" (owner {bucket_obj.owner})"

    base_str = f"Calculating bucket {bucket_str} disk usage"

    with root.status(base_str) as status:
        async with root.client.buckets.get_disk_usage(
            bucket_obj.id,
            cluster_name=bucket_obj.cluster_name,
            org_name=bucket_obj.org_name,
            project_name=bucket_obj.project_name,
        ) as usage_it:
            async for usage in usage_it:
                status.update(
                    f"{base_str}: total size {format_size(usage.total_bytes)}, "
                    f"objects count {usage.object_count}"
                )
    root.print(
        f"Bucket {bucket_str} disk usage:\n"
        f"Total size: {format_size(usage.total_bytes)}\n"
        f"Objects count: {usage.object_count}"
    )


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Perform on a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Perform on a specified project (the current project by default).",
)
@option(
    "-f",
    "--force",
    is_flag=True,
    help="Force removal of all blobs inside bucket",
)
@argument("buckets", type=BUCKET, nargs=-1, required=True)
async def rmbucket(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    force: bool,
    buckets: Sequence[str],
) -> None:
    """
    Remove bucket BUCKET.
    """
    org_name = org
    for bucket in buckets:
        bucket_id = await resolve_bucket(
            bucket,
            client=root.client,
            cluster_name=cluster,
            org_name=org_name,
            project_name=project,
        )
        if force:
            bucket_obj = await root.client.buckets.get(bucket_id, cluster_name=cluster)
            await root.client.buckets.blob_rm(bucket_obj.uri, recursive=True)
        await root.client.buckets.rm(bucket_id, cluster)
        if root.verbosity >= 0:
            root.print(f"Bucket with id '{bucket_id}' was successfully removed.")


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Perform on a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Perform on a specified project (the current project by default).",
)
@argument("bucket", type=BUCKET, required=True)
@argument(
    "public_level",
    type=click.Choice(["public", "private"], case_sensitive=False),
    required=True,
)
async def set_bucket_publicity(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    bucket: str,
    public_level: str,
) -> None:
    """
    Change public access settings for BUCKET

    Examples:

      apolo blob set-bucket-publicity my-bucket public
      apolo blob set-bucket-publicity my-bucket private
    """
    public = public_level == "public"
    org_name = org
    await root.client.buckets.set_public_access(
        bucket,
        public,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )
    if root.verbosity >= 0:
        root.print(
            f"Bucket '{bucket}' was made {'public' if public else 'non-public'}."
        )


# Object level commands


@command()
@click.argument(
    "paths",
    nargs=-1,
    type=PlatformURIType(allowed_schemes=["blob"]),
)
@option(
    "--human-readable",
    "-h",
    is_flag=True,
    help="with -l print human readable sizes (e.g., 2K, 540M).",
)
@option("-l", "format_long", is_flag=True, help="use a long listing format.")
@option(
    "-r",
    "--recursive",
    is_flag=True,
    help="List all keys under the URL path provided, not just 1 level depths.",
)
@option("--full-uri", is_flag=True, help="Output full bucket URI.")
async def ls(
    root: Root,
    paths: Sequence[URL],
    human_readable: bool,
    format_long: bool,
    recursive: bool,
    full_uri: bool,
) -> None:
    """
    List buckets or bucket contents.
    """
    formatter: BaseBlobFormatter
    if full_uri:
        uri_fmtr: URIFormatter = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    if format_long:
        # Similar to `ls -l`
        formatter = LongBlobFormatter(
            human_readable=human_readable, color=root.color, uri_formatter=uri_fmtr
        )
    else:
        # Similar to `ls -1`, default for non-terminal on UNIX. We show full uris of
        # blobs, thus column formatting does not work too well.
        if root.tty and not root.quiet:
            formatter = SimpleBlobFormatter(root.color, uri_fmtr)
        else:
            formatter = SimpleBlobFormatter(False, uri_fmtr)

    if not paths:
        # List Buckets instead of blobs in bucket

        with root.pager():
            async with root.client.buckets.list() as bucket_it:
                async for bucket in bucket_it:
                    root.print(formatter(bucket))
    else:
        for uri in paths:
            if root.verbosity > 0:
                painter = get_painter(root.color)
                uri_text = painter.paint(str(uri), FileStatusType.DIRECTORY)
                root.print(Text.assemble("List of ", uri_text, ":"))

            with root.pager():
                async with root.client.buckets.list_blobs(
                    uri=uri,
                    recursive=recursive,
                ) as blobs_it:
                    async for entry in blobs_it:
                        root.print(formatter(entry))


@command()
@option("--full-uri", is_flag=True, help="Output full bucket URI.")
@click.argument(
    "patterns",
    nargs=-1,
    required=False,
    type=PlatformURIType(allowed_schemes=["blob"]),
)
async def glob(root: Root, full_uri: bool, patterns: Sequence[URL]) -> None:
    """
    List resources that match PATTERNS.
    """
    if full_uri:
        uri_fmtr: URIFormatter = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    for pattern in patterns:
        if root.verbosity > 0:
            painter = get_painter(root.color)
            uri_text = painter.paint(str(pattern), FileStatusType.FILE)
            root.print(Text.assemble("Using pattern ", uri_text, ":"))

        async with root.client.buckets.glob_blobs(uri=pattern) as blobs_it:
            async for entry in blobs_it:
                root.print(uri_fmtr(entry.uri))


@command()
@click.argument(
    "sources",
    nargs=-1,
    required=False,
    type=PlatformURIType(allowed_schemes=["file", "blob"]),
)
@click.argument(
    "destination",
    required=False,
    type=PlatformURIType(allowed_schemes=["file", "blob"]),
)
@option("-r", "--recursive", is_flag=True, help="Recursive copy, off by default")
@option(
    "--glob/--no-glob",
    is_flag=True,
    default=True,
    show_default=True,
    help="Expand glob patterns in SOURCES with explicit scheme.",
)
@option(
    "-t",
    "--target-directory",
    metavar="DIRECTORY",
    default=None,
    type=PlatformURIType(allowed_schemes=["file", "blob"], complete_file=False),
    help="Copy all SOURCES into DIRECTORY.",
)
@option(
    "-T",
    "--no-target-directory",
    is_flag=True,
    help="Treat DESTINATION as a normal file.",
)
@option(
    "-u",
    "--update",
    is_flag=True,
    help="Copy only when the SOURCE file is newer than the destination file "
    "or when the destination file is missing.",
)
@option(
    "--continue",
    "continue_",
    is_flag=True,
    help="Continue copying partially-copied files. "
    "Only for copying from Blob Storage.",
)
@filter_option(
    "--exclude",
    "filters",
    is_exclude=True,
    help=("Exclude files and directories that match the specified pattern."),
)
@filter_option(
    "--include",
    "filters",
    is_exclude=False,
    help=("Don't exclude files and directories that match the specified pattern."),
)
@option(
    "--exclude-from-files",
    metavar="FILES",
    default=None,
    help=(
        "A list of file names that contain patterns for exclusion files "
        "and directories. Used only for uploading. "
        "The default can be changed using the storage.cp-exclude-from-files "
        'configuration variable documented in "apolo help user-config"'
    ),
)
@option(
    "-p/-P",
    "--progress/--no-progress",
    is_flag=True,
    default=True,
    help="Show progress, on by default.",
)
async def cp(
    root: Root,
    sources: Sequence[URL],
    destination: URL | None,
    recursive: bool,
    glob: bool,
    target_directory: URL | None,
    no_target_directory: bool,
    update: bool,
    continue_: bool,
    filters: tuple[tuple[bool, str], ...] | None,
    exclude_from_files: str,
    progress: bool,
) -> None:
    """
    Copy blobs into and from Blob Storage.

    Either SOURCES or DESTINATION should have `blob://` scheme.
    If scheme is omitted, file:// scheme is assumed. It is currently not possible to
    copy files between Blob Storage (`blob://`) destination, nor with `storage://`
    scheme paths.

    Use `/dev/stdin` and `/dev/stdout` file names to upload a file from standard input
    or output to stdout.

    Any number of --exclude and --include options can be passed.  The
    filters that appear later in the command take precedence over filters
    that appear earlier in the command.  If neither --exclude nor
    --include options are specified the default can be changed using the
    storage.cp-exclude configuration variable documented in
    "apolo help user-config".

    File permissions, modification times and other attributes will not be passed to
    Blob Storage metadata during upload.
    """
    if target_directory:
        if no_target_directory:
            raise click.UsageError(
                "Cannot combine --target-directory (-t) and --no-target-directory (-T)"
            )
        if destination is None:
            raise click.MissingParameter(
                param_type="argument", param_hint='"SOURCES..."'
            )
        sources = *sources, destination
        destination = None
    else:
        if destination is None:
            raise click.MissingParameter(
                param_type="argument", param_hint='"DESTINATION"'
            )
        if not sources:
            raise click.MissingParameter(
                param_type="argument", param_hint='"SOURCES..."'
            )

        # From gsutil:
        #
        # There's an additional wrinkle when working with subdirectories: the resulting
        # names depend on whether the destination subdirectory exists. For example,
        # if gs://my-bucket/subdir exists as a subdirectory, the command:

        # gsutil cp -r dir1/dir2 gs://my-bucket/subdir

        # will create the blob gs://my-bucket/subdir/dir2/a/b/c. In contrast, if
        # gs://my-bucket/subdir does not exist, this same gsutil cp command will create
        # the blob gs://my-bucket/subdir/a/b/c.
        if no_target_directory or not await _is_dir(root, destination):
            target_directory = None
        else:
            target_directory = destination
            destination = None

    ignore_file_names = await calc_ignore_file_names(root.client, exclude_from_files)
    filters = await calc_filters(root.client, filters)
    sources = await _expand(sources, root, glob, allow_file=True)
    if no_target_directory and len(sources) > 1:
        raise click.UsageError(f"Extra operand after {str(sources[1])!r}")

    file_filter = FileFilter()
    for exclude, pattern in filters:
        log.debug("%s %s", "Exclude" if exclude else "Include", pattern)
        file_filter.append(exclude, pattern)

    show_progress = root.tty and progress

    errors = False
    for source in sources:
        # `src.name` will return empty string if URL has trailing slash, ie.:
        # `apolo blob cp data/ blob:my_bucket` -> dst == blob:my_bucket/file.txt
        # `apolo blob cp data blob:my_bucket` -> dst == blob:my_bucket/data/file.txt
        # `apolo blob cp blob:my_bucket data` -> dst == data/my_bucket/file.txt
        # `apolo blob cp blob:my_bucket/ data` -> dst == data/file.txt
        if target_directory:
            destination = target_directory / source.name
        assert destination

        progress_blob = create_storage_progress(root, show_progress)
        try:
            with progress_blob.begin(source, destination):
                if source.scheme == "file" and destination.scheme == "blob":
                    if continue_:
                        raise click.UsageError(
                            "Option --continue is not supported for copying to "
                            "Blob Storage"
                        )

                    if recursive and await _is_dir(root, source):
                        await root.client.buckets.upload_dir(
                            source,
                            destination,
                            update=update,
                            filter=file_filter.match,
                            ignore_file_names=frozenset(ignore_file_names),
                            progress=progress_blob,
                        )
                    else:
                        await root.client.buckets.upload_file(
                            source, destination, update=update, progress=progress_blob
                        )
                elif source.scheme == "blob" and destination.scheme == "file":
                    if recursive and await _is_dir(root, source):
                        await root.client.buckets.download_dir(
                            source,
                            destination,
                            continue_=continue_,
                            update=update,
                            filter=file_filter.match,
                            progress=progress_blob,
                        )
                    else:
                        await root.client.buckets.download_file(
                            source,
                            destination,
                            continue_=continue_,
                            update=update,
                            progress=progress_blob,
                        )
                else:
                    raise RuntimeError(
                        f"Copy operation of the file with scheme '{source.scheme}'"
                        f" to the file with scheme '{destination.scheme}'"
                        f" is not supported."
                        " Checkout 'apolo-extras data --help',"
                        " maybe it will suite your use-case?"
                    )
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot copy {source} to {destination}: {error}")
            errors = True

    if errors:
        sys.exit(EX_OSFILE)


async def _is_dir(root: Root, uri: URL) -> bool:
    if uri.scheme == "blob":
        return await root.client.buckets.blob_is_dir(uri)

    elif uri.scheme == "file":
        path = root.client.parse.uri_to_path(uri)
        return path.is_dir()
    return False


async def _expand(
    paths: Sequence[URL], root: Root, glob: bool, allow_file: bool = False
) -> list[URL]:
    uris = []
    for path in paths:
        if root.verbosity > 0:
            painter = get_painter(root.color)
            uri_text = painter.paint(str(path), FileStatusType.FILE)
            root.print(Text.assemble("Expand", uri_text))

        if glob and globmodule.has_magic(path.path):
            if path.scheme == "blob":
                async with root.client.buckets.glob_blobs(path) as blob_iter:
                    async for blob in blob_iter:
                        uris.append(blob.uri)
            elif allow_file and path.scheme == "file":
                uri_path = str(root.client.parse.uri_to_path(path))
                for p in globmodule.iglob(uri_path, recursive=True):
                    uris.append(path.with_path(p))
            else:
                uris.append(path)
        else:
            uris.append(path)
    return uris


@command()
@argument(
    "paths",
    nargs=-1,
    required=True,
    type=PlatformURIType(allowed_schemes=["file", "blob"]),
)
@option(
    "--recursive",
    "-r",
    is_flag=True,
    help="remove directories and their contents recursively",
)
@option(
    "--glob/--no-glob",
    is_flag=True,
    default=True,
    show_default=True,
    help="Expand glob patterns in PATHS",
)
@option(
    "-p/-P",
    "--progress/--no-progress",
    is_flag=True,
    default=None,
    help="Show progress, on by default in TTY mode, off otherwise.",
)
async def rm(
    root: Root,
    paths: Sequence[URL],
    recursive: bool,
    glob: bool,
    progress: bool | None,
) -> None:
    """
    Remove blobs from bucket.
    """
    errors = False
    show_progress = root.tty if progress is None else progress

    for uri in await _expand(paths, root, glob):
        try:
            progress_obj = DeleteProgress(root) if show_progress else None
            await root.client.buckets.blob_rm(
                uri, recursive=recursive, progress=progress_obj
            )
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot remove {uri}: {error}")
            errors = True
        else:
            if root.verbosity > 0:
                painter = get_painter(root.color)
                uri_text = painter.paint(str(uri), FileStatusType.FILE)
                root.print(Text.assemble(f"removed ", uri_text))
    if errors:
        sys.exit(EX_OSFILE)


@command()
@argument(
    "path",
    required=True,
    type=PlatformURIType(allowed_schemes=["file", "blob"]),
)
@option(
    "--expires",
    type=str,
    metavar="TIMEDELTA",
    help="Duration this signature will be valid in the format '1h2m3s'",
    show_default=True,
    default="1h",
)
async def sign_url(
    root: Root,
    path: URL,
    expires: str,
) -> None:
    """
    Make signed url for blob in bucket.
    """
    expires_delta = parse_timedelta(expires)
    signed_url = await root.client.buckets.make_signed_url(
        path, int(expires_delta.total_seconds())
    )

    root.print(signed_url, soft_wrap=True)


# Bucket credentials commands


def make_bucket_getter(
    client: Client, cluster_name: str | None = None
) -> Callable[[str], Awaitable[Bucket]]:
    async def _get_bucket(id: str) -> Bucket:
        return await client.buckets.get(id, cluster_name=cluster_name)

    return _get_bucket


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Look on a specified cluster (the current cluster by default).",
)
async def lscredentials(root: Root, cluster: str | None) -> None:
    """
    List bucket credentials.
    """
    if root.quiet:
        fmtr: BaseBucketCredentialsFormatter = SimpleBucketCredentialsFormatter()
    else:
        fmtr = BucketCredentialsFormatter(make_bucket_getter(root.client, cluster))

    credentials = []
    with root.status("Fetching credentials") as status:
        async with root.client.buckets.persistent_credentials_list(
            cluster_name=cluster
        ) as it:
            async for credential in it:
                credentials.append(credential)
                status.update(f"Fetching credentials ({len(credentials)} loaded)")

    with root.pager():
        root.print(await fmtr(credentials))


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform in a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Perform in a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Perform in a specified project (the current project by default).",
)
@option(
    "--name",
    type=str,
    metavar="NAME",
    help="Optional bucket credential name",
    default=None,
)
@option(
    "--read-only",
    is_flag=True,
    help="Make read-only credential",
)
@argument("buckets", type=BUCKET, nargs=-1, required=True)
async def mkcredentials(
    root: Root,
    buckets: Sequence[str],
    name: str | None = None,
    cluster: str | None = None,
    org: str | None = None,
    project: str | None = None,
    read_only: bool = False,
) -> None:
    """
    Create a new bucket credential.
    """
    org_name = org
    bucket_ids = [
        await resolve_bucket(
            bucket,
            client=root.client,
            cluster_name=cluster,
            org_name=org_name,
            project_name=project,
        )
        for bucket in buckets
    ]
    credential = await root.client.buckets.persistent_credentials_create(
        name=name, cluster_name=cluster, read_only=read_only, bucket_ids=bucket_ids
    )

    fmtr = BucketCredentialFormatter(make_bucket_getter(root.client, cluster))
    with root.pager():
        root.print(await fmtr(credential), soft_wrap=True)


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Look on a specified cluster (the current cluster by default).",
)
@argument("bucket_credential", type=BUCKET_CREDENTIAL)
async def statcredentials(
    root: Root, cluster: str | None, bucket_credential: str
) -> None:
    """
    Get bucket credential BUCKET_CREDENTIAL.
    """
    credential_id = await resolve_bucket_credential(
        bucket_credential, client=root.client, cluster_name=cluster
    )
    credential_obj = await root.client.buckets.persistent_credentials_get(
        credential_id, cluster_name=cluster
    )

    fmtr = BucketCredentialFormatter(make_bucket_getter(root.client, cluster))
    with root.pager():
        root.print(await fmtr(credential_obj), soft_wrap=True)


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform on a specified cluster (the current cluster by default).",
)
@argument("credentials", type=BUCKET_CREDENTIAL, nargs=-1, required=True)
async def rmcredentials(
    root: Root, cluster: str | None, credentials: Sequence[str]
) -> None:
    """
    Remove bucket credential BUCKET_CREDENTIAL.
    """
    for credential in credentials:
        credential_id = await resolve_bucket_credential(
            credential, client=root.client, cluster_name=cluster
        )
        await root.client.buckets.persistent_credentials_rm(
            credential_id, cluster_name=cluster
        )
        if root.verbosity >= 0:
            root.print(
                f"Bucket credential with id '{credential_id}' was successfully removed."
            )


blob_storage.add_command(lsbucket)
blob_storage.add_command(mkbucket)
blob_storage.add_command(importbucket)
blob_storage.add_command(statbucket)
blob_storage.add_command(rmbucket)
blob_storage.add_command(set_bucket_publicity)

blob_storage.add_command(lscredentials)
blob_storage.add_command(mkcredentials)
blob_storage.add_command(statcredentials)
blob_storage.add_command(rmcredentials)

blob_storage.add_command(cp)
blob_storage.add_command(ls)
blob_storage.add_command(glob)
blob_storage.add_command(rm)
blob_storage.add_command(sign_url)
blob_storage.add_command(du)
