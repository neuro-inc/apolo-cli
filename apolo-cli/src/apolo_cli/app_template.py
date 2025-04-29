from typing import Optional

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.app_templates import (
    AppTemplatesFormatter,
    BaseAppTemplatesFormatter,
    SimpleAppTemplatesFormatter,
)
from .root import Root
from .utils import alias, argument, command, group, option


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
async def list(
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


@command()
@argument("name")
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
async def list_versions(
    root: Root,
    name: str,
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    List app template versions.
    """
    if root.quiet:
        templates_fmtr: BaseAppTemplatesFormatter = SimpleAppTemplatesFormatter(
            is_version_list=True
        )
    else:
        templates_fmtr = AppTemplatesFormatter()

    templates = []
    with root.status(f"Fetching versions for app template '{name}'") as status:
        async with root.client.apps.list_template_versions(
            name=name, cluster_name=cluster, org_name=org, project_name=project
        ) as it:
            async for template in it:
                templates.append(template)
                status.update(f"Fetching versions ({len(templates)} loaded)")

    with root.pager():
        if templates:
            root.print(templates_fmtr(templates))
        else:
            if not root.quiet:
                root.print(f"No versions found for app template '{name}'.")


# Register commands with the app_template group
app_template.add_command(list)
app_template.add_command(alias(list, "ls", help="Alias to list", deprecated=False))
app_template.add_command(list_versions)
app_template.add_command(
    alias(list_versions, "ls-versions", help="Alias to list-versions", deprecated=False)
)
