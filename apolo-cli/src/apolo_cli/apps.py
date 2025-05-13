import codecs
import sys
from typing import List, Optional

import yaml

from apolo_sdk import AppValue, IllegalArgumentError

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.app_values import (
    AppValuesFormatter,
    BaseAppValuesFormatter,
    SimpleAppValuesFormatter,
)
from .formatters.apps import AppsFormatter, BaseAppsFormatter, SimpleAppsFormatter
from .job import _parse_date
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
async def list(
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


@command()
@argument("app_id", required=False)
@option(
    "-t",
    "--type",
    "value_type",
    help="Filter by value type.",
)
@option(
    "-o",
    "--output",
    "output_format",
    type=str,
    help="Output format (default: table).",
)
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
async def get_values(
    root: Root,
    app_id: Optional[str],
    value_type: Optional[str],
    output_format: Optional[str],
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Get application values.

    APP_ID: Optional ID of the app to get values for.
    """
    if root.quiet:
        values_fmtr: BaseAppValuesFormatter = SimpleAppValuesFormatter()
    else:
        values_fmtr = AppValuesFormatter()

    values: List[AppValue] = []
    with root.status("Fetching app values") as status:
        async with root.client.apps.get_values(
            app_id=app_id,
            value_type=value_type,
            cluster_name=cluster,
            org_name=org,
            project_name=project,
        ) as it:
            async for value in it:
                values.append(value)
                status.update(f"Fetching app values ({len(values)} loaded)")

    with root.pager():
        if values:
            root.print(values_fmtr(values))
        else:
            root.print("No app values found.")


@command()
@argument("app_id")
@option(
    "--since",
    metavar="DATE_OR_TIMEDELTA",
    help="Only return logs after a specific date (including). "
    "Use value of format '1d2h3m4s' to specify moment in "
    "past relatively to current time.",
)
@option(
    "--timestamps",
    is_flag=True,
    help="Include timestamps on each line in the log output.",
)
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
async def logs(
    root: Root,
    app_id: str,
    since: Optional[str],
    timestamps: bool,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Print the logs for an app.
    """
    decoder = codecs.lookup("utf8").incrementaldecoder("replace")

    async with root.client.apps.logs(
        app_id=app_id,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
        since=_parse_date(since) if since else None,
        timestamps=timestamps,
    ) as it:
        async for chunk in it:
            if not chunk:  # pragma: no cover
                txt = decoder.decode(b"", final=True)
                if not txt:
                    break
            else:
                txt = decoder.decode(chunk)
            sys.stdout.write(txt)
            sys.stdout.flush()


app.add_command(list)
app.add_command(alias(list, "ls", help="Alias to list", deprecated=False))
app.add_command(install)
app.add_command(uninstall)
app.add_command(get_values)
app.add_command(logs)
