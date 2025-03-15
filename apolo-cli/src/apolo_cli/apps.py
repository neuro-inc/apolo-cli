from typing import Optional

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.apps import AppsFormatter, BaseAppsFormatter, SimpleAppsFormatter
from .root import Root
from .utils import argument, command, group, option


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
    with root.status(f"Uninstalling app {app_id}"):
        await root.client.apps.uninstall(
            app_id=app_id,
            cluster_name=cluster,
            org_name=org,
            project_name=project,
        )
    root.print(f"App {app_id} uninstalled")


app.add_command(ls)
app.add_command(uninstall)
