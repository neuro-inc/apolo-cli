import sys
from typing import Optional

import yaml

from apolo_sdk import IllegalArgumentError

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.apps import AppsFormatter, BaseAppsFormatter, SimpleAppsFormatter
from .root import Root
from .utils import alias, argument, command, group, option


@group()
def app() -> None:
    """
    Operations with applications.
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
@option(
    "--project",
    type=PROJECT,
    help="Look on a specified project (the current project by default).",
)
async def ls(
    root: Root,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    List apps.
    """
    if root.quiet:
        apps_fmtr: BaseAppsFormatter = SimpleAppsFormatter()
    else:
        apps_fmtr = AppsFormatter()

    apps = []
    with root.status("Fetching apps") as status:
        async with root.client.apps.list(
            cluster_name=cluster, org_name=org, project_name=project
        ) as it:
            async for app in it:
                apps.append(app)
                status.update(f"Fetching apps ({len(apps)} loaded)")

    with root.pager():
        if apps:
            root.print(apps_fmtr(apps))
        else:
            root.print("No apps found.")


@command()
@argument("app_id")
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
async def uninstall(
    root: Root,
    app_id: str,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Uninstall an app.

    APP_ID: ID of the app to uninstall
    """
    with root.status(f"Uninstalling app [bold]{app_id}[/bold]"):
        await root.client.apps.uninstall(
            app_id=app_id,
            cluster_name=cluster,
            org_name=org,
            project_name=project,
        )
    if not root.quiet:
        root.print(f"App [bold]{app_id}[/bold] uninstalled", markup=True)


@command()
@option(
    "-f",
    "--file",
    "file_path",
    type=str,
    required=True,
    help="Path to the app YAML file.",
)
@option(
    "--cluster",
    type=CLUSTER,
    help="Specify the cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Specify the org (the current org by default).",
)
@option(
    "--project",
    type=PROJECT,
    help="Specify the project (the current project by default).",
)
async def install(
    root: Root,
    file_path: str,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Install an app from a YAML file.
    """

    with open(file_path) as file:
        app_data = yaml.safe_load(file)

    try:
        with root.status(f"Installing app from [bold]{file_path}[/bold]"):
            await root.client.apps.install(
                app_data=app_data,
                cluster_name=cluster,
                org_name=org,
                project_name=project,
            )
    except IllegalArgumentError as e:
        if e.payload and e.payload.get("errors") and root.verbosity >= 0:
            root.print("[red]Input validation error:[/red]", markup=True)
            for error in e.payload["errors"]:
                path = ".".join(error.get("path", []))
                msg = error.get("message", "")
                root.print(f"  - [bold]{path}[/bold]: {msg}", markup=True)
            sys.exit(1)
        raise e

    if not root.quiet:
        root.print(f"App installed from [bold]{file_path}[/bold]", markup=True)


app.add_command(ls)
app.add_command(alias(ls, "list", help=ls.help, deprecated=False))
app.add_command(install)
app.add_command(uninstall)
