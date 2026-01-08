import builtins
import codecs
import json
import sys
from pathlib import Path

import click
import yaml

from apolo_sdk import (
    AppEvent,
    AppState,
    AppValue,
    IllegalArgumentError,
)

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.app_values import (
    AppValuesFormatter,
    BaseAppValuesFormatter,
    SimpleAppValuesFormatter,
)
from .formatters.apps import (
    AppEventsFormatter,
    AppRevisionsFormatter,
    AppsFormatter,
    BaseAppEventsFormatter,
    BaseAppsFormatter,
    SimpleAppEventsFormatter,
    SimpleAppRevisionsFormatter,
    SimpleAppsFormatter,
)
from .job import _parse_date
from .root import Root
from .utils import alias, argument, command, group, json_default, option


@group()
def vcluster() -> None:
    """
    Operations with virtual kubernetes clusters.
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
async def list_service_accounts(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
) -> None:
    """List kubernetes service accounts"""
    accs = []
    with root.status("Fetching apps") as status:
        async with root.client.vcluster.list_service_accounts(
            cluster_name=cluster,
            org_name=org,
            project_name=project,
        ) as it:
            async for acc in it:
                accs.append(acc)
                status.update(f"Fetching service accounts ({len(accs)} loaded)")

    with root.pager():
        for acc in accs:
            root.print(f"{acc.user} {acc.name}")


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
async def delete_service_account(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    name: str,
) -> None:
    """Delete kubernetes service account"""
    await root.client.vcluster.delete_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
    )
    root.print(f"Deleted {name}")


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
async def create_service_account(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    name: str,
) -> None:
    """Create kubernetes service account"""
    js = await root.client.vcluster.create_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
    )
    root.print(f"Created {name}")

    kube_dir = Path("~/.kube").resolve()
    config_file = kube_dir / "config"
    old_config_file = kube_dir / "config.bak"
    if config_file.exists():
        if old_config_file.exists():
            # On Windows .rename() doesn't override the file silently
            old_config_file.unlink()
        config_file.rename(old_config_file)
    with config_file.open("rw") as f:
        f.write(json.dumps(js))


vcluster.add_command(create_service_account)
vcluster.add_command(list_service_accounts)
vcluster.add_command(delete_service_account)
