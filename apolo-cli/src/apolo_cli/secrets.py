import pathlib
from typing import Optional

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.secrets import (
    BaseSecretsFormatter,
    SecretsFormatter,
    SimpleSecretsFormatter,
)
from .formatters.utils import URIFormatter, uri_formatter
from .root import Root
from .utils import argument, command, group, option


@group()
def secret() -> None:
    """
    Operations with secrets.
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
@option("--all-orgs", is_flag=True, default=False, help="Show secrets in all orgs.")
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
@option(
    "--all-projects", is_flag=True, default=False, help="Show secrets in all projects."
)
@option("--full-uri", is_flag=True, help="Output full secret URI.")
async def ls(
    root: Root,
    full_uri: bool,
    cluster: Optional[str],
    org: Optional[str],
    all_orgs: bool,
    project: Optional[str],
    all_projects: bool,
) -> None:
    """
    List secrets.
    """
    if root.quiet:
        secrets_fmtr: BaseSecretsFormatter = SimpleSecretsFormatter()
    else:
        if full_uri:
            uri_fmtr: URIFormatter = str
        else:
            uri_fmtr = uri_formatter(
                cluster_name=root.client.cluster_name,
                org_name=root.client.config.org_name,
                project_name=root.client.config.project_name_or_raise,
            )
        secrets_fmtr = SecretsFormatter(
            uri_fmtr,
        )

    if all_orgs:
        org_name = None
    else:
        org_name = org

    if all_projects:
        project_name = None
    else:
        project_name = project or root.client.config.project_name_or_raise

    secrets = []
    with root.status("Fetching secrets") as status:
        async with root.client.secrets.list(
            cluster_name=cluster, org_name=org_name, project_name=project_name
        ) as it:
            async for secret in it:
                secrets.append(secret)
                status.update(f"Fetching secrets ({len(secrets)} loaded)")

    with root.pager():
        root.print(secrets_fmtr(secrets))


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform on a specified cluster (the current cluster by default).",
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
@argument("key")
@argument("value")
async def add(
    root: Root,
    key: str,
    value: str,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Add secret KEY with data VALUE.

    If VALUE starts with @ it points to a file with secrets content.

    Examples:

      apolo secret add KEY_NAME VALUE
      apolo secret add KEY_NAME @path/to/file.txt
    """
    org_name = org
    await root.client.secrets.add(
        key,
        read_data(value),
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
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
    help="Look on a specified org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
@option(
    "-f",
    "--file",
    "output_file",
    type=pathlib.Path,
    help="Save secret to file instead of displaying it.",
)
@argument("key")
async def get(
    root: Root,
    key: str,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
    output_file: Optional[pathlib.Path],
) -> None:
    """
    Get secret KEY.

    If --file is specified, the secret content will be saved to the file.
    Otherwise, it will be displayed on stdout.

    Examples:

      apolo secret get KEY_NAME
      apolo secret get KEY_NAME --file secret.txt
    """
    org_name = org
    secret_data = await root.client.secrets.get(
        key,
        cluster_name=cluster,
        org_name=org_name,
        project_name=project,
    )

    if output_file:
        output_file.expanduser().write_bytes(secret_data)
        if not root.quiet:
            root.print(f"Secret '{key}' saved to {output_file}")
    else:
        try:
            content = secret_data.decode("utf-8")
            root.print(content, end="")
        except UnicodeDecodeError:
            if not root.quiet:
                root.print(
                    f"Secret '{key}' contains binary data. "
                    "Use --file option to save it.",
                    err=True,
                )
            else:
                raise


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Perform on a specified cluster (the current cluster by default).",
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
@argument("key")
async def rm(
    root: Root,
    key: str,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Remove secret KEY.
    """

    org_name = org
    await root.client.secrets.rm(
        key, cluster_name=cluster, org_name=org_name, project_name=project
    )
    if root.verbosity > 0:
        root.print(f"Secret with key '{key}' was successfully removed")


secret.add_command(ls)
secret.add_command(add)
secret.add_command(get)
secret.add_command(rm)


def read_data(value: str) -> bytes:
    if value.startswith("@"):
        # Read from file
        data = pathlib.Path(value[1:]).expanduser().read_bytes()
    else:
        data = value.encode("utf-8")
    return data
