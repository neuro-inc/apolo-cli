import json
from typing import Optional

import yaml

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.app_templates import (
    AppTemplatesFormatter,
    BaseAppTemplatesFormatter,
    SimpleAppTemplatesFormatter,
)
from .root import Root
from .template_schema_utils import _generate_yaml_from_schema
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


@command()
@argument("name")
@option(
    "-V",
    "--version",
    default="latest",
    help="Specify the version of the app template (latest if not specified).",
)
@option(
    "-o",
    "--output",
    "output_format",
    type=str,
    help="Output format (yaml, json). Default is yaml.",
    default="yaml",
)
@option(
    "-f",
    "--file",
    "file_path",
    type=str,
    help="Save output to a file instead of displaying it.",
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
async def get(
    root: Root,
    name: str,
    version: Optional[str],
    output_format: str,
    file_path: Optional[str],
    cluster: Optional[str],
    org: Optional[str],
    project: Optional[str],
) -> None:
    """
    Generate payload for 'app install'.
    """
    with root.status(f"Fetching app template [bold]{name}[/bold]"):
        template = await root.client.apps.get_template(
            name=name,
            version=version,
            cluster_name=cluster,
            org_name=org,
            project_name=project,
        )

    basic_template = {
        "template_name": template.name,
        "template_version": template.version,
        "input": {},
    }

    # Get base URL for schema
    base_url = str(root.client.config.api_url.with_path(""))

    if output_format.lower() == "yaml":
        if template.input:
            content = _generate_yaml_from_schema(
                template.input, template.name, template.version, base_url
            )
        else:
            content = yaml.dump(basic_template, default_flow_style=False)
    elif output_format.lower() == "json":
        if template.input:
            yaml_content = _generate_yaml_from_schema(
                template.input, template.name, template.version, base_url
            )
            content = json.dumps(yaml.safe_load(yaml_content), indent=2)
        else:
            content = json.dumps(basic_template, indent=2)
    else:
        root.print(f"Unknown output format: {output_format}")
        exit(1)

    if file_path:
        with open(file_path, "w") as f:
            f.write(content)
        if not root.quiet:
            root.print(f"Template saved to [bold]{file_path}[/bold]", markup=True)
    else:
        root.print(content)


# Register commands with the app_template group
app_template.add_command(list)
app_template.add_command(alias(list, "ls", help="Alias to list", deprecated=False))
app_template.add_command(list_versions)
app_template.add_command(
    alias(list_versions, "ls-versions", help="Alias to list-versions", deprecated=False)
)
app_template.add_command(get)
