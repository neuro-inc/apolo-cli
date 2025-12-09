from collections.abc import Sequence
from datetime import timedelta

from yarl import URL

from .click_types import (
    CLUSTER,
    DISK,
    DISK_NAME,
    ORG,
    PROJECT,
    PlatformURIType,
    UnionType,
)
from .formatters.disks import (
    BaseDisksFormatter,
    DiskFormatter,
    DisksFormatter,
    SimpleDisksFormatter,
)
from .formatters.utils import URIFormatter, get_datetime_formatter, uri_formatter
from .parse_utils import parse_memory
from .root import Root
from .utils import argument, calc_timeout_unused, command, group, option, resolve_disk

DEFAULT_DISK_LIFE_SPAN = "1d"


@group()
def disk() -> None:
    """
    Operations with disks.
    """


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
@option("--all-orgs", is_flag=True, default=False, help="Show disks in all orgs.")
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
@option(
    "--all-projects", is_flag=True, default=False, help="Show disks in all projects."
)
@option("--full-uri", is_flag=True, help="Output full disk URI.")
@option("--long-format", is_flag=True, help="Output all info about disk.")
async def ls(
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
    List disks.
    """
    if root.quiet:
        disks_fmtr: BaseDisksFormatter = SimpleDisksFormatter()
    else:
        if full_uri:
            uri_fmtr: URIFormatter = str
        else:
            uri_fmtr = uri_formatter(
                project_name=root.client.config.project_name_or_raise,
                cluster_name=root.client.cluster_name,
                org_name=root.client.config.org_name,
            )
        disks_fmtr = DisksFormatter(
            uri_fmtr,
            long_format=long_format,
            datetime_formatter=get_datetime_formatter(root.iso_datetime_format),
        )

    if all_orgs:
        org_name = None
    else:
        org_name = org

    if all_projects:
        project_name = None
    else:
        project_name = project or root.client.config.project_name_or_raise

    disks = []
    with root.status("Fetching disks") as status:
        async with root.client.disks.list(
            cluster_name=cluster, org_name=org_name, project_name=project_name
        ) as it:
            async for disk in it:
                disks.append(disk)
                status.update(f"Fetching disks ({len(disks)} loaded)")

    with root.pager():
        root.print(disks_fmtr(disks))


@command()
@argument("storage")
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
    "--timeout-unused",
    type=str,
    metavar="TIMEDELTA",
    help=(
        "Optional disk lifetime limit after last usage "
        "in the format '1d2h3m4s' (some parts may be missing). "
        "Set '0' to disable. Default value '1d' can be changed "
        "in the user config."
    ),
)
@option(
    "--name",
    type=DISK_NAME,
    metavar="NAME",
    help="Optional disk name",
    default=None,
)
@option(
    "--project",
    type=PROJECT,
    help="Create disk in a specified project (the current project by default).",
)
async def create(
    root: Root,
    storage: str,
    timeout_unused: str | None = None,
    name: str | None = None,
    cluster: str | None = None,
    org: str | None = None,
    project: str | None = None,
) -> None:
    """
    Create a disk

    Create a disk with at least storage amount STORAGE.

    To specify the amount, you can use the following suffixes: "kKMGTPEZY"
    To use decimal quantities, append "b" or "B". For example:
    - 1K or 1k is 1024 bytes
    - 1Kb or 1KB is 1000 bytes
    - 20G is 20 * 2 ^ 30 bytes
    - 20Gb or 20GB is 20.000.000.000 bytes

    Note that server can have big granularity (for example, 1G)
    so it will possibly round-up the amount you requested.

    Examples:

      apolo disk create 10G
      apolo disk create 500M
    """
    timeout_unused_seconds = await calc_timeout_unused(
        root.client, timeout_unused, DEFAULT_DISK_LIFE_SPAN, "disk"
    )
    disk_timeout_unused = None
    if timeout_unused_seconds:
        disk_timeout_unused = timedelta(seconds=timeout_unused_seconds)
    org_name = org

    disk = await root.client.disks.create(
        parse_memory(storage),
        timeout_unused=disk_timeout_unused,
        name=name,
        cluster_name=cluster,
        project_name=project,
        org_name=org_name,
    )
    disk_fmtr = DiskFormatter(
        str, datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    with root.pager():
        root.print(disk_fmtr(disk))


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
@argument(
    "disk", type=UnionType("disk", PlatformURIType(allowed_schemes=("disk",)), DISK)
)
@option("--full-uri", is_flag=True, help="Output full disk URI.")
async def get(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    disk: str | URL,
    full_uri: bool,
) -> None:
    """
    Get disk DISK_ID.
    """
    org_name = org
    disk_id = await resolve_disk(
        disk,
        client=root.client,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )
    disk_obj = await root.client.disks.get(disk_id, cluster_name=cluster)

    if full_uri:
        uri_fmtr: URIFormatter = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    disk_fmtr = DiskFormatter(
        uri_fmtr, datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    with root.pager():
        root.print(disk_fmtr(disk_obj))


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
@argument(
    "disks",
    type=UnionType("disk", PlatformURIType(allowed_schemes=("disk",)), DISK),
    nargs=-1,
    required=True,
)
async def rm(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    disks: Sequence[str],
) -> None:
    """
    Remove disk DISK_ID.
    """
    org_name = org
    for disk in disks:
        disk_id = await resolve_disk(
            disk,
            client=root.client,
            cluster_name=cluster,
            org_name=org_name,
            project_name=project,
        )
        await root.client.disks.rm(disk_id, cluster_name=cluster)
        if root.verbosity >= 0:
            root.print(f"Disk with id '{disk_id}' was successfully removed.")


disk.add_command(ls)
disk.add_command(create)
disk.add_command(get)
disk.add_command(rm)
