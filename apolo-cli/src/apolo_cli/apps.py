from typing import Optional

from rich.table import Table, box

from .click_types import CLUSTER, ORG, PROJECT
from .root import Root
from .utils import argument, command, group


@group()
def app() -> None:
    """
    Operations with applications.
    """


@command()
@argument("cluster", type=CLUSTER, required=False)
@argument("org", type=ORG, required=False)
@argument("project", type=PROJECT, required=False)
async def list(
    root: Root,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    List all app instances.
    """
    client = root.client

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Display Name")
    table.add_column("Template")
    table.add_column("Version")
    table.add_column("State")

    count = 0
    async with client.apps.list(
        cluster_name=cluster, org_name=org, project_name=project
    ) as it:
        async for instance in it:
            count += 1
            table.add_row(
                instance.id,
                instance.name,
                instance.display_name,
                instance.template_name,
                instance.template_version,
                instance.state,
            )

    if count:
        root.print(table)
    else:
        root.print("No app instances found.")


app.add_command(list)
