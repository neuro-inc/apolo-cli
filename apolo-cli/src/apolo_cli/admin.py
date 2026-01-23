from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from typing import Any

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.markup import escape as rich_escape

from apolo_sdk import (
    _AMDGPUPreset,
    _Balance,
    _Cluster,
    _ClusterUserRoleType,
    _ConfigCluster,
    _IntelGPUPreset,
    _NvidiaGPUPreset,
    _OrgCluster,
    _OrgUserRoleType,
    _Project,
    _ProjectUser,
    _ProjectUserRoleType,
    _Quota,
    _ResourcePreset,
    _TPUPreset,
)
from apolo_sdk._server_cfg import (
    AMDGPUPreset,
    IntelGPUPreset,
    NvidiaGPUPreset,
    TPUPreset,
)

from apolo_cli.formatters.config import BalanceFormatter

from .click_types import MEMORY, NVIDIA_MIG, NvidiaMIG
from .defaults import JOB_CPU_NUMBER, JOB_MEMORY_AMOUNT, PRESET_PRICE
from .formatters.admin import (
    ClustersFormatter,
    ClusterUserFormatter,
    ClusterUserWithInfoFormatter,
    OrgClusterFormatter,
    OrgClustersFormatter,
    OrgFormatter,
    OrgsFormatter,
    OrgUserFormatter,
    ProjectFormatter,
    ProjectsFormatter,
    ProjectUserFormatter,
)
from .formatters.config import AdminQuotaFormatter
from .root import Root
from .utils import argument, command, group, option

log = logging.getLogger(__name__)

UNLIMITED = "unlimited"


def _get_org(root: Root, org: str | None) -> str:
    org_name = org or root.client.config.org_name
    if not org_name:
        raise ValueError("Org name is required")
    return org_name


@group()
def admin() -> None:
    """Cluster administration commands."""


@command()
async def get_clusters(root: Root) -> None:
    """
    Print the list of available clusters.
    """
    fmt = ClustersFormatter()
    with root.status("Fetching the list of clusters"):
        config_clusters = await root.client._clusters.list()
        admin_clusters = await root.client._admin.list_clusters()
    clusters: dict[str, tuple[_Cluster | None, _ConfigCluster | None]] = {}
    for config_cluster in config_clusters:
        clusters[config_cluster.name] = (None, config_cluster)
    for admin_cluster in admin_clusters:
        if admin_cluster.name in clusters:
            clusters[admin_cluster.name] = (
                admin_cluster,
                clusters[admin_cluster.name][1],
            )
        else:
            clusters[admin_cluster.name] = (admin_cluster, None)
    with root.pager():
        root.print(fmt(clusters))


@command(hidden=True)
async def get_admin_clusters(root: Root) -> None:
    """
    Print the list of clusters on platform-admin side.
    """
    with root.status("Fetching the list of clusters"):
        clusters = await root.client._admin.list_clusters()
    with root.pager():
        for cluster in clusters:
            root.print(cluster.name)


@command()
@option(
    "--default-credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "--default-jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-role",
    default=_ClusterUserRoleType.USER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
    show_default=True,
    help="Default role for new users added to cluster",
)
@argument("cluster_name", required=True, type=str)
@argument("config", required=True, type=click.File(encoding="utf8", lazy=False))
async def add_cluster(
    root: Root,
    cluster_name: str,
    default_credits: str,
    default_jobs: str,
    default_role: str,
) -> None:
    """
    Create a new cluster.

    Creates cluster entry on admin side and then start its provisioning using
    provided config.
    """
    await root.client._admin.create_cluster(
        cluster_name,
        default_credits=_parse_credits_value(default_credits),
        default_quota=_Quota(_parse_jobs_value(default_jobs)),
        default_role=_ClusterUserRoleType(default_role),
    )
    if not root.quiet:
        root.print(f"Cluster {cluster_name} successfully added")


@command()
@option(
    "--default-credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "--default-jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-role",
    default=_ClusterUserRoleType.USER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
    show_default=True,
    help="Default role for new users added to cluster",
)
@argument("cluster_name", required=True, type=str)
async def update_cluster(
    root: Root,
    cluster_name: str,
    default_credits: str,
    default_jobs: str,
    default_role: str,
) -> None:
    """
    Update a cluster.
    """
    await root.client._admin.update_cluster(
        _Cluster(
            name=cluster_name,
            default_credits=_parse_credits_value(default_credits),
            default_quota=_Quota(_parse_jobs_value(default_jobs)),
            default_role=_ClusterUserRoleType(default_role),
        )
    )
    if not root.quiet:
        root.print(f"Cluster {cluster_name} successfully updated")


@command()
@option("--force", default=False, help="Skip prompt", is_flag=True)
@argument("cluster_name", required=True, type=str)
async def remove_cluster(root: Root, cluster_name: str, force: bool) -> None:
    """
    Drop a cluster

    Completely removes cluster from the system.
    """

    if not force:
        with patch_stdout():
            answer: str = await PromptSession().prompt_async(
                f"Are you sure that you want to drop cluster '{cluster_name}' (y/n)?"
            )
        if answer != "y":
            return
    await root.client._admin.delete_cluster(cluster_name)


@command()
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
@option(
    "--details/--no-details",
    default=False,
    help="Include detailed user info",
    is_flag=True,
)
@argument("cluster_name", required=False, default=None, type=str)
async def get_cluster_users(
    root: Root,
    org: str | None,
    details: bool,
    cluster_name: str | None,
) -> None:
    """
    List users in specified cluster
    """
    cluster_name = cluster_name or root.client.config.cluster_name
    with root.status(
        f"Fetching the list of cluster users of cluster [b]{cluster_name}[/b]"
    ):
        users = await root.client._admin.list_cluster_users(  # type: ignore
            cluster_name=cluster_name,
            with_user_info=details,
            org_name=_get_org(root, org),
        )
        users = sorted(users, key=lambda user: (user.user_name, user.org_name or ""))
    with root.pager():
        if details:
            root.print(ClusterUserWithInfoFormatter()(users))
        else:
            root.print(ClusterUserFormatter()(users))


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@argument(
    "role",
    required=False,
    default=None,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
@option(
    "-j",
    "--jobs",
    metavar="AMOUNT",
    type=str,
    default=None,
    show_default=True,
    help="Maximum running jobs quota (`unlimited' stands for no limit)",
)
async def add_cluster_user(
    root: Root,
    cluster_name: str,
    user_name: str,
    role: str | None,
    jobs: str | None,
    org: str | None,
) -> None:
    """
    Add user access to a specified cluster.

    The command supports one of three user roles: admin, manager or user.
    """
    # Use cluster defaults credits/quota for "user-like" roles.
    # Unlimited for other roles.
    if jobs is None and role in (None, "user", "member"):
        quota = None
    else:
        quota = _Quota(total_running_jobs=_parse_jobs_value(jobs or UNLIMITED))
    user = await root.client._admin.create_cluster_user(
        cluster_name,
        user_name,
        _ClusterUserRoleType(role),
        org_name=_get_org(root, org),
        quota=quota,
    )
    assert user.role
    if not root.quiet:
        root.print(
            f"Added [bold]{rich_escape(user.user_name)}[/bold] to cluster "
            f"[bold]{rich_escape(cluster_name)}[/bold] as "
            + (
                f"member of org [bold]{rich_escape(org)}[/bold] as "
                if org is not None
                else ""
            )
            + f"[bold]{rich_escape(user.role)}[/bold]. Quotas set:",
            markup=True,
        )
        quota_fmt = AdminQuotaFormatter()
        root.print(quota_fmt(user.quota))


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@argument(
    "role",
    required=True,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
async def update_cluster_user(
    root: Root,
    cluster_name: str,
    user_name: str,
    role: str,
    org: str | None,
) -> None:
    cluster_user = await root.client._admin.get_cluster_user(
        cluster_name, user_name, org_name=_get_org(root, org)
    )
    cluster_user = replace(cluster_user, role=_ClusterUserRoleType(role))
    await root.client._admin.update_cluster_user(cluster_user)

    if not root.quiet:
        root.print(
            f"New role for user [bold]{rich_escape(cluster_user.user_name)}[/bold] "
            + (
                f"as member of org [bold]{rich_escape(org)}[/bold] "
                if org is not None
                else ""
            )
            + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
            markup=True,
            end=" ",
        )
        root.print(str(cluster_user.role))


def _parse_finite_decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
        if result.is_finite():
            return result
    except (ValueError, LookupError, InvalidOperation):
        pass
    raise click.BadParameter(f"{value} is not valid decimal number")


def _parse_credits_value(value: str) -> Decimal | None:
    if value == UNLIMITED:
        return None
    return _parse_finite_decimal(value)


def _parse_jobs_value(value: str) -> int | None:
    if value == UNLIMITED:
        return None
    try:
        result = int(value, 10)
        if result >= 0:
            return result
    except ValueError:
        pass
    raise click.BadParameter("jobs quota should be non-negative integer")


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
async def remove_cluster_user(
    root: Root, cluster_name: str, user_name: str, org: str | None
) -> None:
    """
    Remove user access from the cluster.
    """
    await root.client._admin.delete_cluster_user(
        cluster_name, user_name, org_name=_get_org(root, org)
    )
    if not root.quiet:
        root.print(
            f"Removed [bold]{rich_escape(user_name)}[/bold] "
            + (
                f"as member of org [bold]{rich_escape(org)}[/bold] "
                if org is not None
                else ""
            )
            + f"from cluster [bold]{rich_escape(cluster_name)}[/bold]",
            markup=True,
        )


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@argument("org", required=True, type=str)
async def get_user_quota(
    root: Root,
    cluster_name: str,
    user_name: str,
    org: str,
) -> None:
    """
    Get info about user quota in given cluster
    """
    org_name = _get_org(root, org)
    cluster_user = await root.client._admin.get_cluster_user(
        cluster_name=cluster_name,
        user_name=user_name,
        org_name=org_name,
    )
    org_user = await root.client._admin.get_org_user(
        org_name=org_name, user_name=user_name
    )
    quota_fmt = AdminQuotaFormatter()
    balance_fmt = BalanceFormatter()
    root.print(
        f"Quota and balance for [u]{rich_escape(cluster_user.user_name)}[/u] "
        + (
            f"as member of org [bold]{rich_escape(org)}[/bold] "
            if org is not None
            else ""
        )
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(quota_fmt(cluster_user.quota))
    root.print(balance_fmt(org_user.balance))


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@option(
    "-j",
    "--jobs",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
async def set_user_quota(
    root: Root,
    cluster_name: str,
    user_name: str,
    jobs: str,
    org: str | None,
) -> None:
    """
    Set user quota to given values
    """
    user_with_quota = await root.client._admin.update_cluster_user_quota(
        cluster_name=cluster_name,
        user_name=user_name,
        quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
        org_name=_get_org(root, org),
    )
    fmt = AdminQuotaFormatter()
    root.print(
        f"New quotas for [u]{rich_escape(user_with_quota.user_name)}[/u] "
        + (
            f"as member of org [bold]{rich_escape(org)}[/bold] "
            if org is not None
            else ""
        )
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(fmt(user_with_quota.quota))


@command()
@argument("org", required=True, type=str)
@argument("user_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
async def set_user_credits(
    root: Root,
    org: str,
    user_name: str,
    credits: str,
) -> None:
    """
    Set user credits to given value
    """
    org_name = _get_org(root, org)
    credits_decimal = _parse_credits_value(credits)
    user_with_quota = await root.client._admin.update_org_user_balance(
        user_name=user_name,
        credits=credits_decimal,
        org_name=org_name,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for [u]{rich_escape(user_with_quota.user_name)}[/u] "
        + f"as member of org [bold]{rich_escape(org)}[/bold]:",
        markup=True,
    )
    root.print(fmt(user_with_quota.balance))


@command()
@argument("org", required=True, type=str)
@argument("user_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Credits amount to add",
)
async def add_user_credits(root: Root, org: str, user_name: str, credits: str) -> None:
    """
    Add given values to user credits
    """
    org_name = _get_org(root, org)
    additional_credits = _parse_finite_decimal(credits)
    user_with_quota = await root.client._admin.update_org_user_balance_by_delta(
        org_name, user_name, delta=additional_credits
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for [u]{rich_escape(user_with_quota.user_name)}[/u] "
        + f"as member of org [bold]{rich_escape(org)}[/bold]:",
        markup=True,
    )
    root.print(fmt(user_with_quota.balance))


@command()
@argument("preset_name")
@option(
    "--credits-per-hour",
    metavar="AMOUNT",
    type=str,
    help="Price of running job of this preset for an hour in credits",
    default=PRESET_PRICE,
    show_default=True,
)
@option(
    "-c",
    "--cpu",
    metavar="NUMBER",
    type=float,
    help="Number of CPUs",
    default=JOB_CPU_NUMBER,
    show_default=True,
)
@option(
    "-m",
    "--memory",
    metavar="AMOUNT",
    type=MEMORY,
    help="Memory amount",
    default=JOB_MEMORY_AMOUNT,
    show_default=True,
)
@option(
    "-g",
    "--nvidia-gpu",
    metavar="NUMBER",
    type=int,
    help="Number of Nvidia GPUs",
)
@option(
    "--nvidia-gpu-model",
    metavar="GPU_MODEL_FREE_TEXT",
    type=str,
    help="Nvidia GPU model",
    required=False,
)
@option(
    "--nvidia-mig",
    metavar="NVIDIA_MIG",
    type=NVIDIA_MIG,
    multiple=True,
    help="Nvidia MIG configuration in format PROFILE[:MODEL]=COUNT",
)
@option(
    "--amd-gpu",
    metavar="NUMBER",
    type=int,
    help="Number of AMD GPUs",
)
@option(
    "--amd-gpu-model",
    metavar="GPU_MODEL_FREE_TEXT",
    type=str,
    help="AMD GPU model",
    required=False,
)
@option(
    "--intel-gpu",
    metavar="NUMBER",
    type=int,
    help="Number of Intel GPUs",
)
@option(
    "--intel-gpu-model",
    metavar="GPU_MODEL_FREE_TEXT",
    type=str,
    help="Intel GPU model",
    required=False,
)
@option("--tpu-type", metavar="TYPE", type=str, help="TPU type")
@option(
    "tpu_software_version",
    "--tpu-sw-version",
    metavar="VERSION",
    type=str,
    help="TPU software version",
)
@option(
    "--scheduler/--no-scheduler",
    "-p/-P",
    help="Use round robin scheduler for jobs",
    default=False,
    show_default=True,
)
@option(
    "--preemptible-node/--non-preemptible-node",
    help="Use a lower-cost preemptible instance",
    default=False,
    show_default=True,
)
@option(
    "resource_pool_names",
    "-r",
    "--resource-pool",
    help=(
        "Name of the resource pool where job will be scheduled "
        "(multiple values are supported)"
    ),
    multiple=True,
)
async def add_resource_preset(
    root: Root,
    preset_name: str,
    credits_per_hour: str,
    cpu: float,
    memory: int,
    nvidia_gpu: int | None,
    nvidia_gpu_model: str | None,
    nvidia_mig: Sequence[NvidiaMIG] | None,
    amd_gpu: int | None,
    amd_gpu_model: str | None,
    intel_gpu: int | None,
    intel_gpu_model: str | None,
    tpu_type: str | None,
    tpu_software_version: str | None,
    scheduler: bool,
    preemptible_node: bool,
    resource_pool_names: Sequence[str],
) -> None:
    """
    Add new resource preset
    """
    presets = dict(root.client.config.presets)
    if preset_name in presets:
        raise ValueError(f"Preset '{preset_name}' already exists")
    if nvidia_gpu:
        nvidia_gpu_preset = _NvidiaGPUPreset(
            count=nvidia_gpu,
            model=nvidia_gpu_model,
        )
    else:
        nvidia_gpu_preset = None
    if nvidia_mig:
        nvidia_mig_presets = {
            mig.profile_name: _NvidiaGPUPreset(
                count=mig.count,
                model=mig.model,
            )
            for mig in nvidia_mig
        }
    else:
        nvidia_mig_presets = None
    if amd_gpu:
        amd_gpu_preset = _AMDGPUPreset(
            count=amd_gpu,
            model=amd_gpu_model,
        )
    else:
        amd_gpu_preset = None
    if intel_gpu:
        intel_gpu_preset = _IntelGPUPreset(
            count=intel_gpu,
            model=intel_gpu_model,
        )
    else:
        intel_gpu_preset = None
    if tpu_type and tpu_software_version:
        tpu_preset = _TPUPreset(type=tpu_type, software_version=tpu_software_version)
    else:
        tpu_preset = None
    preset = _ResourcePreset(
        name=preset_name,
        credits_per_hour=_parse_finite_decimal(credits_per_hour),
        cpu=cpu,
        memory=memory,
        nvidia_gpu=nvidia_gpu_preset,
        nvidia_migs=nvidia_mig_presets,
        amd_gpu=amd_gpu_preset,
        intel_gpu=intel_gpu_preset,
        tpu=tpu_preset,
        scheduler_enabled=scheduler,
        preemptible_node=preemptible_node,
        resource_pool_names=tuple(resource_pool_names),
    )
    await root.client._clusters.add_resource_preset(
        root.client.config.cluster_name, preset
    )
    await root.client.config.fetch()
    if not root.quiet:
        root.print(
            f"Added resource preset [b]{rich_escape(preset_name)}[/b] "
            f"in cluster [b]{rich_escape(root.client.config.cluster_name)}[/b]",
            markup=True,
        )


@command()
@argument("preset_name")
@option(
    "--credits-per-hour",
    metavar="AMOUNT",
    type=str,
    help="Price of running job of this preset for an hour in credits",
)
@option(
    "-c",
    "--cpu",
    metavar="NUMBER",
    type=float,
    help="Number of CPUs",
)
@option(
    "-m",
    "--memory",
    metavar="AMOUNT",
    type=MEMORY,
    help="Memory amount",
)
@option(
    "-g",
    "--nvidia-gpu",
    metavar="NUMBER",
    type=int,
    help="Number of Nvidia GPUs",
)
@option(
    "--nvidia-gpu-model",
    metavar="GPU_MODEL_FREE_TEXT",
    type=str,
    help="Nvidia GPU model",
)
@option(
    "--nvidia-mig",
    metavar="NVIDIA_MIG",
    type=NVIDIA_MIG,
    multiple=True,
    help="Nvidia MIG configuration, PROFILE[:MODEL]=COUNT",
)
@option(
    "--amd-gpu",
    metavar="NUMBER",
    type=int,
    help="Number of AMD GPUs",
)
@option(
    "--amd-gpu-model",
    metavar="GPU_MODEL_FREE_TEXT",
    type=str,
    help="AMD GPU model",
)
@option(
    "--intel-gpu",
    metavar="NUMBER",
    type=int,
    help="Number of Intel GPUs",
)
@option(
    "--intel-gpu-model",
    metavar="GPU_MODEL_FREE_TEXT",
    type=str,
    help="Intel GPU model",
)
@option("--tpu-type", metavar="TYPE", type=str, help="TPU type")
@option(
    "tpu_software_version",
    "--tpu-sw-version",
    metavar="VERSION",
    type=str,
    help="TPU software version",
)
@option(
    "--scheduler/--no-scheduler",
    "-p/-P",
    help="Use round robin scheduler for jobs",
    default=None,
)
@option(
    "--preemptible-node/--non-preemptible-node",
    help="Use a lower-cost preemptible instance",
    default=None,
)
@option(
    "resource_pool_names",
    "-r",
    "--resource-pool",
    help=(
        "Name of the resource pool where job will be scheduled "
        "(multiple values are supported)"
    ),
    multiple=True,
)
async def update_resource_preset(
    root: Root,
    preset_name: str,
    credits_per_hour: str | None,
    cpu: float | None,
    memory: int | None,
    nvidia_gpu: int | None,
    nvidia_gpu_model: str | None,
    nvidia_mig: Sequence[NvidiaMIG] | None,
    amd_gpu: int | None,
    amd_gpu_model: str | None,
    intel_gpu: int | None,
    intel_gpu_model: str | None,
    tpu_type: str | None,
    tpu_software_version: str | None,
    scheduler: bool | None,
    preemptible_node: bool | None,
    resource_pool_names: Sequence[str],
) -> None:
    """
    Update existing resource preset
    """
    presets = dict(root.client.config.presets)
    try:
        preset = presets[preset_name]
    except KeyError:
        raise ValueError(f"Preset '{preset_name}' does not exists")

    kwargs: dict[str, Any] = {
        "credits_per_hour": (
            _parse_finite_decimal(credits_per_hour)
            if credits_per_hour is not None
            else None
        ),
        "cpu": cpu,
        "memory": memory,
        "scheduler_enabled": scheduler,
        "preemptible_node": preemptible_node,
        "resource_pool_names": resource_pool_names,
    }
    if nvidia_gpu:
        kwargs["nvidia_gpu"] = NvidiaGPUPreset(
            count=nvidia_gpu,
            model=nvidia_gpu_model,
        )
    if nvidia_mig:
        kwargs["nvidia_migs"] = {
            mig.profile_name: NvidiaGPUPreset(
                count=mig.count,
                model=mig.model,
            )
            for mig in nvidia_mig
        }
    if amd_gpu:
        kwargs["amd_gpu"] = AMDGPUPreset(
            count=amd_gpu,
            model=amd_gpu_model,
        )
    if intel_gpu:
        kwargs["intel_gpu"] = IntelGPUPreset(
            count=intel_gpu,
            model=intel_gpu_model,
        )
    if tpu_type and tpu_software_version:
        kwargs["tpu"] = TPUPreset(type=tpu_type, software_version=tpu_software_version)
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    preset = replace(preset, **kwargs)
    if preset.nvidia_gpu:
        nvidia_gpu_preset = _NvidiaGPUPreset(
            count=preset.nvidia_gpu.count,
            model=preset.nvidia_gpu.model,
            memory=preset.nvidia_gpu.memory,
        )
    else:
        nvidia_gpu_preset = None
    if preset.nvidia_migs:
        nvidia_mig_presets = {
            key: _NvidiaGPUPreset(
                count=value.count,
                model=value.model,
            )
            for key, value in preset.nvidia_migs.items()
        }
    else:
        nvidia_mig_presets = None
    if preset.amd_gpu:
        amd_gpu_preset = _AMDGPUPreset(
            count=preset.amd_gpu.count,
            model=preset.amd_gpu.model,
            memory=preset.amd_gpu.memory,
        )
    else:
        amd_gpu_preset = None
    if preset.intel_gpu:
        intel_gpu_preset = _IntelGPUPreset(
            count=preset.intel_gpu.count,
            model=preset.intel_gpu.model,
            memory=preset.intel_gpu.memory,
        )
    else:
        intel_gpu_preset = None
    if preset.tpu:
        tpu_preset = _TPUPreset(
            type=preset.tpu.type, software_version=preset.tpu.software_version
        )
    else:
        tpu_preset = None
    await root.client._clusters.update_resource_preset(
        root.client.config.cluster_name,
        _ResourcePreset(
            name=preset_name,
            credits_per_hour=preset.credits_per_hour,
            cpu=preset.cpu,
            memory=preset.memory,
            nvidia_gpu=nvidia_gpu_preset,
            nvidia_migs=nvidia_mig_presets,
            amd_gpu=amd_gpu_preset,
            intel_gpu=intel_gpu_preset,
            tpu=tpu_preset,
            scheduler_enabled=preset.scheduler_enabled,
            preemptible_node=preset.preemptible_node,
            resource_pool_names=preset.resource_pool_names,
        ),
    )
    await root.client.config.fetch()
    if not root.quiet:
        root.print(
            f"Updated resource preset [b]{rich_escape(preset_name)}[/b] "
            f"in cluster [b]{rich_escape(root.client.config.cluster_name)}[/b]",
            markup=True,
        )


@command()
@argument("preset_name")
async def remove_resource_preset(root: Root, preset_name: str) -> None:
    """
    Remove resource preset
    """
    presets = dict(root.client.config.presets)
    if preset_name not in presets:
        raise ValueError(f"Preset '{preset_name}' not found")
    del presets[preset_name]
    await root.client._clusters.remove_resource_preset(
        root.client.config.cluster_name, preset_name
    )
    await root.client.config.fetch()
    if not root.quiet:
        root.print(
            f"Removed resource preset [b]{rich_escape(preset_name)}[/b] "
            f"from cluster [b]{rich_escape(root.client.config.cluster_name)}[/b]",
            markup=True,
        )


# Orgs:


@command()
async def get_orgs(root: Root) -> None:
    """
    Print the list of available orgs.
    """
    fmt = OrgsFormatter()
    with root.status("Fetching the list of orgs"):
        orgs = await root.client._admin.list_orgs()
    with root.pager():
        root.print(fmt(orgs))


@command()
@argument("org_name", required=True, type=str)
@option("--skip-default-tenants", default=False, hidden=True, is_flag=True)
async def add_org(
    root: Root, org_name: str, skip_default_tenants: bool = False
) -> None:
    """
    Create a new org.
    """
    await root.client._admin.create_org(
        org_name, skip_auto_add_to_clusters=skip_default_tenants
    )
    await root.client.config.fetch()


@command()
@option("--force", default=False, help="Skip prompt", is_flag=True)
@argument("org_name", required=True, type=str)
async def remove_org(root: Root, org_name: str, force: bool) -> None:
    """
    Drop an org

    Completely removes org from the system.
    """
    orgs = await root.client._admin.list_orgs()
    if not any(org.name == org_name for org in orgs):
        raise ValueError(f"Organization '{org_name}' is not found.")

    if not force:
        with patch_stdout():
            answer: str = await PromptSession().prompt_async(
                f"Are you sure that you want to drop org '{org_name}' (y/n)?"
            )
        if answer != "y":
            return
    await root.client._admin.delete_org(org_name)


@command()
@argument("org_name", required=True, type=str)
async def get_org_users(root: Root, org_name: str) -> None:
    """
    List users in specified org
    """
    fmt = OrgUserFormatter()
    with root.status(f"Fetching the list of org users of org [b]{org_name}[/b]"):
        users = await root.client._admin.list_org_users(org_name, with_user_info=True)
    with root.pager():
        root.print(fmt(users))


@command()
@argument("org_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@argument(
    "role",
    required=False,
    default=_OrgUserRoleType.USER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_OrgUserRoleType)]),
)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    default=None,
    show_default=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
async def add_org_user(
    root: Root,
    org_name: str,
    user_name: str,
    role: str,
    credits: str | None,
) -> None:
    """
    Add user access to specified org.

    The command supports one of three user roles: admin, manager or user.
    """
    if credits is None and role == "user":
        balance = None
    else:
        balance = _Balance(credits=_parse_credits_value(credits or UNLIMITED))

    user = await root.client._admin.create_org_user(
        org_name=org_name,
        user_name=user_name,
        role=_OrgUserRoleType(role),
        balance=balance,
    )
    if not root.quiet:
        root.print(
            f"Added [bold]{rich_escape(user.user_name)}[/bold] to org "
            f"[bold]{rich_escape(org_name)}[/bold] as "
            f"[bold]{rich_escape(user.role)}[/bold]",
            markup=True,
        )
        balance_fmt = BalanceFormatter()
        root.print(balance_fmt(user.balance))


@command()
@argument("org_name", required=True, type=str)
@argument("user_name", required=True, type=str)
async def remove_org_user(root: Root, org_name: str, user_name: str) -> None:
    """
    Remove user access from the org.
    """
    await root.client._admin.delete_org_user(org_name, user_name)
    if not root.quiet:
        root.print(
            f"Removed [bold]{rich_escape(user_name)}[/bold] from org "
            f"[bold]{rich_escape(org_name)}[/bold]",
            markup=True,
        )


@command()
@argument("cluster_name", required=True, type=str)
async def get_cluster_orgs(root: Root, cluster_name: str) -> None:
    """
    Print the list of all orgs in the cluster
    """
    fmt = OrgClustersFormatter()
    with root.status(f"Fetching the list of orgs of cluster [b]{cluster_name}[/b]"):
        org_clusters = await root.client._admin.list_org_clusters(
            cluster_name=cluster_name
        )
    with root.pager():
        root.print(fmt(org_clusters))


@command()
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "-j",
    "--jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "--default-jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-role",
    default=_ClusterUserRoleType.USER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
    show_default=True,
    help="Default role for new users added to org cluster",
)
@option(
    "--storage-size",
    metavar="AMOUNT",
    type=MEMORY,
    help="Storage size, ignored for storage types with elastic storage size",
)
async def add_org_cluster(
    root: Root,
    cluster_name: str,
    org_name: str,
    credits: str,
    jobs: str,
    default_credits: str,
    default_jobs: str,
    default_role: str,
    storage_size: int | None,
) -> None:
    """
    Add org access to specified cluster.

    """
    if storage_size:
        storage_size *= 1024**2

    org_cluster = await root.client._admin.create_org_cluster(
        cluster_name=cluster_name,
        org_name=org_name,
        balance=_Balance(credits=_parse_credits_value(credits)),
        quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
        default_credits=_parse_credits_value(default_credits),
        default_quota=_Quota(_parse_jobs_value(default_jobs)),
        default_role=_ClusterUserRoleType(default_role),
        storage_size=storage_size,
    )
    if not root.quiet:
        root.print(
            f"Added org [bold]{rich_escape(org_name)}[/bold] to "
            f"[bold]{rich_escape(cluster_name)}[/bold]. Info:",
            markup=True,
        )
        fmt = OrgClusterFormatter()
        root.print(fmt(org_cluster, skip_cluster_org=True))


@command()
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "-j",
    "--jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "--default-jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-role",
    default=_ClusterUserRoleType.USER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
    show_default=True,
    help="Default role for new users added to org cluster",
)
async def update_org_cluster(
    root: Root,
    cluster_name: str,
    org_name: str,
    credits: str,
    jobs: str,
    default_credits: str,
    default_jobs: str,
    default_role: str,
) -> None:
    """
    Update org cluster quotas.

    """
    org_cluster = _OrgCluster(
        cluster_name=cluster_name,
        org_name=org_name,
        balance=_Balance(credits=_parse_credits_value(credits)),
        quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
        default_credits=_parse_credits_value(default_credits),
        default_quota=_Quota(_parse_jobs_value(default_jobs)),
        default_role=_ClusterUserRoleType(default_role),
    )
    await root.client._admin.update_org_cluster(org_cluster)
    if not root.quiet:
        root.print(
            f"Org [bold]{rich_escape(org_name)}[/bold] info in cluster"
            f" [bold]{rich_escape(cluster_name)}[/bold] successfully updated. "
            f"New info:",
            markup=True,
        )
        fmt = OrgClusterFormatter()
        root.print(fmt(org_cluster, skip_cluster_org=True))


@command()
@option("--force", default=False, help="Skip prompt", is_flag=True)
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
async def remove_org_cluster(
    root: Root, cluster_name: str, org_name: str, force: bool
) -> None:
    """
    Drop an org cluster

    Completely removes org from the cluster.
    """

    if not force:
        with patch_stdout():
            answer: str = await PromptSession().prompt_async(
                f"Are you sure that you want to drop org '{org_name}' "
                f"from cluster '{cluster_name}' (y/n)?"
            )
        if answer != "y":
            return
    await root.client._admin.delete_org_cluster(cluster_name, org_name)


@command()
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
@option(
    "--default-credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "--default-jobs",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default maximum running jobs quota (`unlimited' stands for no limit)",
)
@option(
    "--default-role",
    default=_ClusterUserRoleType.USER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ClusterUserRoleType)]),
    show_default=True,
    help="Default role for new users added to org cluster",
)
async def set_org_cluster_defaults(
    root: Root,
    cluster_name: str,
    org_name: str,
    default_credits: str,
    default_jobs: str,
    default_role: str,
) -> None:
    """
    Set org cluster defaults to given value
    """
    org_cluster = await root.client._admin.update_org_cluster_defaults(
        cluster_name=cluster_name,
        org_name=org_name,
        default_credits=_parse_credits_value(default_credits),
        default_quota=_Quota(_parse_jobs_value(default_jobs)),
        default_role=_ClusterUserRoleType(default_role),
    )
    if not root.quiet:
        root.print(
            f"Org [bold]{rich_escape(org_name)}[/bold] info in cluster"
            f" [bold]{rich_escape(cluster_name)}[/bold] successfully updated. "
            f"New info:",
            markup=True,
        )
        fmt = OrgClusterFormatter()
        root.print(fmt(org_cluster, skip_cluster_org=True))


@command()
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
async def get_org_cluster_quota(
    root: Root,
    cluster_name: str,
    org_name: str,
) -> None:
    """
    Get info about org quota in given cluster
    """
    org = await root.client._admin.get_org_cluster(
        cluster_name=cluster_name,
        org_name=org_name,
    )
    quota_fmt = AdminQuotaFormatter()
    balance_fmt = BalanceFormatter()
    root.print(
        f"Quota and balance for org [u]{rich_escape(org_name)}[/u] "
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(quota_fmt(org.quota))
    root.print(balance_fmt(org.balance))


@command()
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
@option(
    "-j",
    "--jobs",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Maximum running jobs quota (`unlimited' stands for no limit)",
)
async def set_org_cluster_quota(
    root: Root,
    cluster_name: str,
    org_name: str,
    jobs: str,
) -> None:
    """
    Set org cluster quota to given values
    """
    org = await root.client._admin.update_org_cluster_quota(
        cluster_name=cluster_name,
        org_name=org_name,
        quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
    )
    fmt = AdminQuotaFormatter()
    root.print(
        f"New quotas for org [u]{rich_escape(org_name)}[/u] "
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(fmt(org.quota))


@command()
@argument("org", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
async def set_org_credits(
    root: Root,
    org: str,
    credits: str,
) -> None:
    """
    Set org credits to given value
    """
    org_name = _get_org(root, org)
    credits_decimal = _parse_credits_value(credits)
    updated_org = await root.client._admin.update_org_balance(
        org_name=org_name,
        credits=credits_decimal,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for org [u]{rich_escape(org_name)}[/u] ",
        markup=True,
    )
    root.print(fmt(updated_org.balance))


@command()
@argument("org", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    help="Credits amount to add",
)
async def add_org_credits(
    root: Root,
    org: str,
    credits: str,
) -> None:
    """
    Add given values to org balance
    """
    org_name = _get_org(root, org)
    additional_credits = _parse_finite_decimal(credits)
    assert additional_credits
    updated_org = await root.client._admin.update_org_balance_by_delta(
        org_name,
        delta=additional_credits,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for org [u]{rich_escape(org_name)}[/u] ",
        markup=True,
    )
    root.print(fmt(updated_org.balance))


@command()
@argument("org_name", required=True, type=str)
@option(
    "--user-default-credits",
    metavar="AMOUNT",
    type=str,
    default=UNLIMITED,
    show_default=True,
    help="Default credits amount to set for org users "
    "(`unlimited' stands for no limit)",
)
async def set_org_defaults(
    root: Root,
    org_name: str,
    user_default_credits: str,
) -> None:
    """
    Set org defaults to a given value
    """
    org = await root.client._admin.update_org_defaults(
        org_name=org_name,
        user_default_credits=_parse_credits_value(user_default_credits),
    )
    if not root.quiet:
        root.print(
            f"Org [bold]{rich_escape(org_name)}[/bold] successfully updated. "
            f"New info:",
            markup=True,
        )
        fmt = OrgFormatter()
        root.print(fmt(org))


# Projects


@command()
@argument("cluster_name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
async def get_projects(root: Root, cluster_name: str, org: str | None = None) -> None:
    """
    Print the list of all projects in the cluster
    """
    fmt = ProjectsFormatter()
    with root.status(f"Fetching the list of projects of cluster [b]{cluster_name}[/b]"):
        org_clusters = await root.client._admin.list_projects(
            cluster_name=cluster_name, org_name=_get_org(root, org)
        )
    with root.pager():
        root.print(fmt(org_clusters))


@command()
@argument("cluster_name", required=True, type=str)
@argument("name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
@option(
    "--default-role",
    default=_ProjectUserRoleType.WRITER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ProjectUserRoleType)]),
    show_default=True,
    help="Default role for new users added to project",
)
@option(
    "--default",
    is_flag=True,
    help="Is this project is default, e.g. new cluster users will be automatically "
    "added to it",
)
@option(
    "--no-virtual-kube/--has-virtual-kube",
    default=False,
    help="Has this project virtual kubernetes support (no vkube by default)",
)
async def add_project(
    root: Root,
    name: str,
    cluster_name: str,
    org: str | None,
    default_role: str,
    default: bool = False,
    has_virtual_kube: bool = False,
) -> None:
    """
    Add new project to specified cluster.

    """

    project = await root.client._admin.create_project(
        name=name,
        cluster_name=cluster_name,
        org_name=_get_org(root, org),
        default_role=_ProjectUserRoleType(default_role),
        is_default=default,
        has_virtual_kube=has_virtual_kube,
    )
    if not root.quiet:
        root.print(
            f"Added project [bold]{rich_escape(project.name)}[/bold] to cluster "
            f"[bold]{rich_escape(cluster_name)}[/bold]"
            f"{f' to org [bold]{rich_escape(org)}[/bold]' if org else ''}. Info:",
            markup=True,
        )
        fmt = ProjectFormatter()
        root.print(fmt(project, skip_cluster_org=True))
    await root.client.config.fetch()
    if (
        not root.client.config.project_name
        and root.client.cluster_name == project.cluster_name
    ):
        await root.client.config.switch_project(project.name)
        root.print(
            f"Selected [bold]{rich_escape(project.name)}[/bold] as current project.",
            markup=True,
        )


@command()
@argument("cluster_name", required=True, type=str)
@argument("name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
@option(
    "--default-role",
    default=_ProjectUserRoleType.WRITER.value,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ProjectUserRoleType)]),
    show_default=True,
    help="Default role for new users added to project",
)
@option(
    "--default",
    is_flag=True,
    help="Is this project is default, e.g. new cluster users will be automatically "
    "added to it",
)
async def update_project(
    root: Root,
    name: str,
    cluster_name: str,
    org: str | None,
    default_role: str,
    default: bool = False,
) -> None:
    """
    Update project settings.

    """
    project = _Project(
        name=name,
        cluster_name=cluster_name,
        org_name=_get_org(root, org),
        default_role=_ProjectUserRoleType(default_role),
        is_default=default,
    )
    await root.client._admin.update_project(project)
    if not root.quiet:
        root.print(
            f"Project [bold]{rich_escape(project.name)}[/bold] in cluster "
            f"[bold]{rich_escape(cluster_name)}[/bold] "
            f"{f'in org [bold]{rich_escape(org)}[/bold]' if org else ''} was "
            f"updated. Info:",
            markup=True,
        )
        fmt = ProjectFormatter()
        root.print(fmt(project, skip_cluster_org=True))


@command()
@option("--force", default=False, help="Skip prompt", is_flag=True)
@argument("cluster_name", required=True, type=str)
@argument("name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
async def remove_project(
    root: Root, name: str, cluster_name: str, org: str | None, force: bool
) -> None:
    """
    Drop a project

    Completely removes project from the cluster.
    """

    if not force:
        with patch_stdout():
            answer: str = await PromptSession().prompt_async(
                f"Are you sure that you want to drop project '{name}' "
                f"from cluster '{cluster_name}' {f'in org {org}' if org else ''} (y/n)?"
            )
        if answer != "y":
            return
    await root.client._admin.delete_project(
        project_name=name,
        cluster_name=cluster_name,
        org_name=_get_org(root, org),
    )


@command()
@argument("cluster_name", required=True, type=str)
@argument("project_name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
async def get_project_users(
    root: Root, cluster_name: str, project_name: str, org: str | None
) -> None:
    """
    List users in specified project
    """
    fmt = ProjectUserFormatter()
    with root.status(
        f"Fetching the list of project users of project [b]{project_name}[/b]"
    ):
        users = await root.client._admin.list_project_users(
            project_name=project_name,
            cluster_name=cluster_name,
            org_name=_get_org(root, org),
            with_user_info=True,
        )
    with root.pager():
        root.print(fmt(users))


@command()
@argument("cluster_name", required=True, type=str)
@argument("project_name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
@argument("user_name", required=True, type=str)
@argument(
    "role",
    required=False,
    default=None,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ProjectUserRoleType)]),
)
async def add_project_user(
    root: Root,
    cluster_name: str,
    project_name: str,
    org: str | None,
    user_name: str,
    role: None | None,
) -> None:
    """
    Add user access to specified project.

    The command supports one of 4 user roles: reader, writer, manager or admin.
    """
    user = await root.client._admin.create_project_user(
        project_name=project_name,
        cluster_name=cluster_name,
        org_name=_get_org(root, org),
        user_name=user_name,
        role=_ProjectUserRoleType(role) if role else None,
    )
    if not root.quiet:
        root.print(
            f"Added [bold]{rich_escape(user.user_name)}[/bold] to project "
            f"[bold]{rich_escape(project_name)}[/bold] as "
            f"[bold]{rich_escape(user.role)}[/bold]",
            markup=True,
        )


@command()
@argument("cluster_name", required=True, type=str)
@argument("project_name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
@argument("user_name", required=True, type=str)
@argument(
    "role",
    required=True,
    metavar="[ROLE]",
    type=click.Choice([str(role) for role in list(_ProjectUserRoleType)]),
)
async def update_project_user(
    root: Root,
    cluster_name: str,
    project_name: str,
    org: str | None,
    user_name: str,
    role: str,
) -> None:
    """
    Update user access to specified project.

    The command supports one of 4 user roles: reader, writer, manager or admin.
    """
    user = _ProjectUser(
        project_name=project_name,
        cluster_name=cluster_name,
        org_name=_get_org(root, org),
        user_name=user_name,
        role=_ProjectUserRoleType(role),
    )

    await root.client._admin.update_project_user(user)
    if not root.quiet:
        root.print(
            f"Update [bold]{rich_escape(user.user_name)}[/bold] role in project "
            f"[bold]{rich_escape(project_name)}[/bold] as "
            f"[bold]{rich_escape(user.role)}[/bold]",
            markup=True,
        )


@command()
@argument("cluster_name", required=True, type=str)
@argument("project_name", required=True, type=str)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster projects",
)
@argument("user_name", required=True, type=str)
async def remove_project_user(
    root: Root,
    cluster_name: str,
    project_name: str,
    org: str | None,
    user_name: str,
) -> None:
    """
    Remove user access from the project.
    """
    await root.client._admin.delete_project_user(
        project_name=project_name,
        cluster_name=cluster_name,
        org_name=_get_org(root, org),
        user_name=user_name,
    )
    if not root.quiet:
        root.print(
            f"Removed [bold]{rich_escape(user_name)}[/bold] from project "
            f"[bold]{rich_escape(project_name)}[/bold]",
            markup=True,
        )


admin.add_command(get_clusters)
admin.add_command(get_admin_clusters)
admin.add_command(add_cluster)
admin.add_command(update_cluster)
admin.add_command(remove_cluster)

admin.add_command(get_cluster_users)
admin.add_command(add_cluster_user)
admin.add_command(update_cluster_user)
admin.add_command(remove_cluster_user)

admin.add_command(get_user_quota)
admin.add_command(set_user_quota)
admin.add_command(set_user_credits)
admin.add_command(add_user_credits)

admin.add_command(add_resource_preset)
admin.add_command(update_resource_preset)
admin.add_command(remove_resource_preset)

admin.add_command(get_orgs)
admin.add_command(add_org)
admin.add_command(remove_org)

admin.add_command(get_org_users)
admin.add_command(add_org_user)
admin.add_command(remove_org_user)

admin.add_command(get_cluster_orgs)
admin.add_command(add_org_cluster)
admin.add_command(update_org_cluster)
admin.add_command(remove_org_cluster)

admin.add_command(set_org_cluster_defaults)
admin.add_command(get_org_cluster_quota)
admin.add_command(set_org_cluster_quota)
admin.add_command(set_org_credits)
admin.add_command(add_org_credits)
admin.add_command(set_org_defaults)

admin.add_command(get_projects)
admin.add_command(add_project)
admin.add_command(update_project)
admin.add_command(remove_project)

admin.add_command(get_project_users)
admin.add_command(add_project_user)
admin.add_command(update_project_user)
admin.add_command(remove_project_user)
