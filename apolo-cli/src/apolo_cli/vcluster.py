import logging

from .click_types import CLUSTER, ORG, PROJECT
from .formatters.utils import get_datetime_formatter
from .formatters.vcluster import (
    BaseKubeConfigFormatter,
    KubeConfigFormatter,
    SimpleKubeConfigFormatter,
)
from .parse_utils import parse_timedelta
from .root import Root
from .utils import argument, command, group, option

log = logging.getLogger(__name__)


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
@option("--long-format", is_flag=True, help="Output all info about service accounts.")
@option(
    "--all-users",
    is_flag=True,
    default=False,
    help="Show accounts for all project users.",
)
async def list_service_accounts(
    root: Root,
    all_users: bool,
    long_format: bool,
    cluster: str | None,
    org: str | None,
    project: str | None,
) -> None:
    """List kubernetes service accounts"""
    if root.quiet:
        fmtr: BaseKubeConfigFormatter = SimpleKubeConfigFormatter()
    else:
        fmtr = KubeConfigFormatter(
            datetime_formatter=get_datetime_formatter(root.iso_datetime_format),
            long_format=long_format,
        )

    accs = []
    with root.status("Fetching apps") as status:
        async with root.client.vcluster.list_service_accounts(
            cluster_name=cluster,
            org_name=org,
            project_name=project,
            all_users=all_users,
        ) as it:
            async for acc in it:
                accs.append(acc)
                status.update(f"Fetching service accounts ({len(accs)} loaded)")

    with root.pager():
        root.print(fmtr(accs))


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
    acc = await root.client.vcluster.delete_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
    )
    root.print(f"Deleted {acc.name}")


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
@option(
    "--ttl",
    type=str,
    metavar="TTL",
    help=(
        "Expiration time in the format '1y2m3d4h5m6s' " "(some parts may be missing)."
    ),
    show_default=True,
)
async def create_service_account(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    name: str,
    ttl: str | None,
) -> None:
    """Create kubernetes service account"""
    log.debug(
        f"Create kube service account {name} for cluster={cluster}, "
        f"org={org}, project={project}, user={root.client.config.username}"
    )
    if ttl is None:
        sa_ttl = root.client.vcluster.DEFAULT_TTL
    else:
        sa_ttl = parse_timedelta(ttl)
    log.debug(f"TTL: {sa_ttl}")
    await root.client.vcluster.create_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
        ttl=sa_ttl,
    )
    root.print(f"Created {name}")

    await root.client.vcluster.activate_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
    )
    root.print(f"Kube config is switched to {name}")


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
async def activate_service_account(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    name: str,
) -> None:
    """Activate kubernetes service account"""
    log.debug(
        f"Activate kube service account {name} for cluster={cluster}, "
        f"org={org}, project={project}, user={root.client.config.username}"
    )
    await root.client.vcluster.activate_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
    )
    root.print(f"Kube config is switched to {name}")


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
@option(
    "--ttl",
    type=str,
    metavar="TTL",
    help=(
        "Expiration time in the format '1y2m3d4h5m6s' " "(some parts may be missing)."
    ),
    show_default=True,
)
async def regenerate_service_account(
    root: Root,
    cluster: str | None,
    org: str | None,
    project: str | None,
    name: str,
    ttl: str | None,
) -> None:
    """Regenerate kubernetes service account"""
    log.debug(
        f"Regenerate kube service account {name} for cluster={cluster}, "
        f"org={org}, project={project}, user={root.client.config.username}"
    )
    if ttl is None:
        sa_ttl = root.client.vcluster.DEFAULT_TTL
    else:
        sa_ttl = parse_timedelta(ttl)
    log.debug(f"TTL: {sa_ttl}")
    await root.client.vcluster.regenerate_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
        ttl=sa_ttl,
    )
    root.print(f"Regenerated config for {name}")

    await root.client.vcluster.activate_service_account(
        name,
        cluster_name=cluster,
        org_name=org,
        project_name=project,
    )
    root.print(f"Kube config is switched to {name}")


vcluster.add_command(activate_service_account)
vcluster.add_command(create_service_account)
vcluster.add_command(delete_service_account)
vcluster.add_command(list_service_accounts)
vcluster.add_command(regenerate_service_account)
