from typing import Optional

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.app_templates import (
    AppTemplatesFormatter,
    BaseAppTemplatesFormatter,
    SimpleAppTemplatesFormatter,
)
from .root import Root
from .utils import command, group, option


@group()
def app_template() -> None:
    """
    Application Templates operations.
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
    List available application templates.
    """
    if root.quiet:
        templates_fmtr: BaseAppTemplatesFormatter = SimpleAppTemplatesFormatter()
    else:
        templates_fmtr = AppTemplatesFormatter()

    templates = []
    with root.status("Fetching app templates") as status:
        async with root.client.apps.list_templates(
            cluster_name=cluster, org_name=org, project_name=project
        ) as it:
            async for template in it:
                templates.append(template)
                status.update(f"Fetching app templates ({len(templates)} loaded)")

    with root.pager():
        if templates:
            root.print(templates_fmtr(templates))
        else:
            if not root.quiet:
                root.print("No app templates found.")


app_template.add_command(ls)
