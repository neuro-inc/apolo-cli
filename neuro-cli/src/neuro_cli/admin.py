import asyncio
import configparser
import json
import logging
import os
import pathlib
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from typing import IO, Any, Dict, Mapping, Optional, Tuple

import click
import yaml
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.markup import escape as rich_escape

from neuro_sdk import (
    Preset,
    _Balance,
    _Cluster,
    _ClusterUserRoleType,
    _ConfigCluster,
    _OrgCluster,
    _OrgUserRoleType,
    _Quota,
)

from neuro_cli.formatters.config import BalanceFormatter

from .click_types import MEGABYTE
from .defaults import JOB_CPU_NUMBER, JOB_MEMORY_AMOUNT, PRESET_PRICE
from .formatters.admin import (
    ClustersFormatter,
    ClusterUserFormatter,
    OrgClusterFormatter,
    OrgsFormatter,
    OrgUserFormatter,
)
from .formatters.config import AdminQuotaFormatter
from .root import Root
from .utils import argument, command, group, option

log = logging.getLogger(__name__)

UNLIMITED = "unlimited"


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
        config_clusters = await root.client._admin.list_config_clusters()
        admin_clusters = await root.client._admin.list_clusters()
    clusters: Dict[str, Tuple[Optional[_Cluster], Optional[_ConfigCluster]]] = {}
    for config_cluster in config_clusters.values():
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
    "--skip-provisioning",
    default=False,
    is_flag=True,
    hidden=True,
    help="Do not provision cluster. Used it tests.",
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
@argument("cluster_name", required=True, type=str)
@argument("config", required=True, type=click.File(encoding="utf8", lazy=False))
async def add_cluster(
    root: Root,
    cluster_name: str,
    config: IO[str],
    default_credits: str,
    default_jobs: str,
    skip_provisioning: bool = False,
) -> None:
    """
    Create a new cluster.

    Creates cluster entry on admin side and then start its provisioning using
    provided config.
    """
    config_dict = yaml.safe_load(config)
    await root.client._admin.create_cluster(
        cluster_name,
        default_credits=_parse_credits_value(default_credits),
        default_quota=_Quota(_parse_jobs_value(default_jobs)),
    )
    if skip_provisioning:
        return
    await root.client._admin.setup_cluster_cloud_provider(cluster_name, config_dict)
    if not root.quiet:
        root.print(
            f"Cluster {cluster_name} successfully added "
            "and will be set up within 24 hours"
        )


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
@argument("cluster_name", required=True, type=str)
async def update_cluster(
    root: Root,
    cluster_name: str,
    default_credits: str,
    default_jobs: str,
) -> None:
    """
    Update a cluster.
    """
    await root.client._admin.update_cluster(
        _Cluster(
            name=cluster_name,
            default_credits=_parse_credits_value(default_credits),
            default_quota=_Quota(_parse_jobs_value(default_jobs)),
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
    "--type", prompt="Select cluster type", type=click.Choice(["aws", "gcp", "azure"])
)
async def show_cluster_options(root: Root, type: str) -> None:
    """
    Show available cluster options.
    """
    config_options = await root.client._admin.get_cloud_provider_options(type)
    root.print(
        json.dumps(config_options, sort_keys=True, indent=2),
        crop=False,
        overflow="ignore",
    )


@command()
@argument(
    "config",
    required=False,
    type=click.Path(exists=False, path_type=str),
    default="cluster.yml",
)
@option(
    "--type",
    prompt="Select cluster type",
    type=click.Choice(["aws", "gcp", "azure", "vcd"]),
)
async def generate_cluster_config(root: Root, config: str, type: str) -> None:
    """
    Create a cluster configuration file.
    """
    config_path = pathlib.Path(config)
    if config_path.exists():
        raise ValueError(
            f"Config path {config_path} already exists, "
            "please remove the file or pass the new file name explicitly."
        )
    session: PromptSession[str] = PromptSession()
    if type == "aws":
        content = await generate_aws(session)
    elif type == "gcp":
        content = await generate_gcp(session)
    elif type == "azure":
        content = await generate_azure(session)
    elif type == "vcd":
        content = await generate_vcd(root, session)
    else:
        assert False, "Prompt should prevent this case"
    config_path.write_text(content, encoding="utf-8")
    if not root.quiet:
        root.print(f"Cluster config {config_path} is generated.")


AWS_TEMPLATE = """\
type: aws
region: us-east-1
zones:
- us-east-1a
- us-east-1b
vpc_id: {vpc_id}
credentials:
  access_key_id: {access_key_id}
  secret_access_key: {secret_access_key}
node_pools:
- id: m5_2xlarge_8
  min_size: 1
  max_size: 4
- id: p2_xlarge_4
  min_size: 1
  max_size: 4
- id: p3_2xlarge_8
  min_size: 0
  max_size: 1
storage:
  id: generalpurpose_bursting
"""


async def generate_aws(session: PromptSession[str]) -> str:
    args = {}
    args["vpc_id"] = await session.prompt_async("AWS VPC ID: ")
    access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if access_key_id is None or secret_access_key is None:
        aws_config_file = pathlib.Path(
            os.environ.get("AWS_SHARED_CREDENTIALS_FILE", "~/.aws/credentials")
        )
        aws_config_file = aws_config_file.expanduser().absolute()
        parser = configparser.ConfigParser()
        parser.read(aws_config_file)
        profile = await session.prompt_async(
            "AWS profile name: ", default=os.environ.get("AWS_PROFILE", "default")
        )
        if access_key_id is None:
            access_key_id = parser[profile]["aws_access_key_id"]
        if secret_access_key is None:
            secret_access_key = parser[profile]["aws_secret_access_key"]
    access_key_id = await session.prompt_async(
        "AWS Access Key: ", default=access_key_id
    )
    secret_access_key = await session.prompt_async(
        "AWS Secret Key: ", default=secret_access_key
    )
    args["access_key_id"] = access_key_id
    args["secret_access_key"] = secret_access_key
    return AWS_TEMPLATE.format_map(args)


GCP_TEMPLATE = """\
type: gcp
location_type: multi_zonal
region: us-central1
zones:
- us-central1-a
- us-central1-c
project: {project_name}
credentials: {credentials}
node_pools:
- id: n1_highmem_8
  min_size: 1
  max_size: 4
- id: n1_highmem_8
  min_size: 1
  max_size: 4
  gpu: 1
  gpu_model: nvidia-tesla-k80
- id: n1_highmem_8
  min_size: 0
  max_size: 1
  gpu: 1
  gpu_model: nvidia-tesla-v100
storage:
  id: gcs-nfs
"""


async def generate_gcp(session: PromptSession[str]) -> str:
    args = {}
    args["project_name"] = await session.prompt_async("GCP project name: ")
    credentials_file = await session.prompt_async(
        "Service Account Key File (.json): ",
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
    )
    with open(credentials_file, "rb") as fp:
        data = json.load(fp)
    out = yaml.dump(data)
    args["credentials"] = "\n" + "\n".join("  " + line for line in out.splitlines())
    return GCP_TEMPLATE.format_map(args)


AZURE_TEMPLATE = """\
type: azure
region: centralus
resource_group: {resource_group}
credentials:
  subscription_id: {subscription_id}
  tenant_id: {tenant_id}
  client_id: {client_id}
  client_secret: {client_secret}
node_pools:
- id: standard_d8_v3_8
  min_size: 1
  max_size: 4
- id: standard_nc6_6
  min_size: 1
  max_size: 4
- id: standard_nc6s_v3_6
  min_size: 0
  max_size: 1
storage:
  id: premium_lrs
  file_share_size_gib: {file_share_size_gib}
"""


async def generate_azure(session: PromptSession[str]) -> str:
    args = {}
    args["subscription_id"] = await session.prompt_async(
        "Azure subscription ID: ", default=os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    )
    args["client_id"] = await session.prompt_async(
        "Azure client ID: ", default=os.environ.get("AZURE_CLIENT_ID", "")
    )
    args["tenant_id"] = await session.prompt_async(
        "Azure tenant ID: ", default=os.environ.get("AZURE_TENANT_ID", "")
    )
    args["client_secret"] = await session.prompt_async(
        "Azure client secret: ", default=os.environ.get("AZURE_CLIENT_SECRET", "")
    )
    args["resource_group"] = await session.prompt_async("Azure resource group: ")
    args["file_share_size_gib"] = await session.prompt_async(
        "Azure Files storage size (Gib): "
    )
    return AZURE_TEMPLATE.format_map(args)


VCD_TEMPLATE = """\
type: vcd_{vcd_provider}
url: {url}
organization: {organization}
virtual_data_center: {virtual_data_center}
edge_name: {edge_name}
edge_public_ip: {edge_ip}
edge_external_network_name: {edge_external_network_name}
catalog_name: {catalog_name}
credentials:
  user: {user}
  password: {password}
node_pools:
- id: {kubernetes_node_pool_id}
  role: kubernetes
  name: kubernetes
  min_size: 3
  max_size: 3
  disk_type: {storage_profile_name}
  disk_size_gb: 40
- id: {platform_node_pool_id}
  role: platform
  name: platform
  min_size: 3
  max_size: 3
  disk_type: {storage_profile_name}
  disk_size_gb: 100
storage:
  profile_name: {storage_profile_name}
  size_gib: {storage_size_gib}
"""


async def generate_vcd(root: Root, session: PromptSession[str]) -> str:
    args = {}
    cloud_providers = await root.client._admin.list_cloud_providers()
    cloud_providers = {k: v for k, v in cloud_providers.items() if k.startswith("vcd_")}

    if len(cloud_providers) == 1:
        args["vcd_provider"] = next(iter(cloud_providers.keys()))[4:]
    else:
        args["vcd_provider"] = await session.prompt_async(
            "VCD provider: ", default=os.environ.get("VCD_PROVIDER", "").lower()
        )
    cloud_provider = cloud_providers[f"vcd_{args['vcd_provider']}"]

    args["url"] = await session.prompt_async(
        "Url: ",
        default=os.environ.get("VCD_URL", cloud_provider.get("url", "")),
    )
    args["organization"] = await session.prompt_async(
        "Organization: ",
        default=os.environ.get(
            "VCD_ORGANIZATION", cloud_provider.get("organization", "")
        ),
    )
    args["virtual_data_center"] = await session.prompt_async(
        "Virtual data center: ",
        default=os.environ.get("VCD_VIRTUAL_DATA_CENTER", ""),
    )
    args["user"] = await session.prompt_async(
        "User: ", default=os.environ.get("VCD_USER", "")
    )
    args["password"] = await session.prompt_async(
        "Password: ", default=os.environ.get("VCD_PASSWORD", "")
    )
    args["edge_name"] = await session.prompt_async(
        "Edge name: ",
        default=cloud_provider.get("edge_name_template", "").format(
            organization=args["organization"], vdc=args["virtual_data_center"]
        ),
    )
    args["edge_ip"] = await session.prompt_async("Edge IP: ")
    args["edge_external_network_name"] = await session.prompt_async(
        "Edge external network: ",
        default=cloud_provider.get("edge_external_network_name", ""),
    )
    args["catalog_name"] = await session.prompt_async(
        "Catalog: ", default=cloud_provider.get("catalog_name", "")
    )
    args["storage_profile_name"] = await session.prompt_async(
        "Storage profile: ",
        default=(cloud_provider.get("storage_profile_names") or [""])[0],
    )
    args["storage_size_gib"] = await session.prompt_async("Storage size (Gib): ")
    args["kubernetes_node_pool_id"] = cloud_provider["kubernetes_node_pool_id"]
    args["platform_node_pool_id"] = cloud_provider["platform_node_pool_id"]
    return VCD_TEMPLATE.format_map(args)


@command()
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
@argument("cluster_name", required=False, default=None, type=str)
async def get_cluster_users(
    root: Root, org: Optional[str], cluster_name: Optional[str]
) -> None:
    """
    List users in specified cluster
    """
    fmt = ClusterUserFormatter()
    cluster_name = cluster_name or root.client.config.cluster_name
    with root.status(
        f"Fetching the list of cluster users of cluster [b]{cluster_name}[/b]"
    ):
        users = await root.client._admin.list_cluster_users(
            cluster_name=cluster_name,
            with_user_info=True,
            org_name=org,
        )
        users = sorted(users, key=lambda user: (user.user_name, user.org_name or ""))
    with root.pager():
        root.print(fmt(users))


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@argument(
    "role",
    required=False,
    default=_ClusterUserRoleType.USER.value,
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
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    default=None,
    show_default=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
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
    role: str,
    credits: Optional[str],
    jobs: Optional[str],
    org: Optional[str],
) -> None:
    """
    Add user access to specified cluster.

    The command supports one of 3 user roles: admin, manager or user.
    """
    # Use cluster defaults credits/quota for "user" role. Unlimited for other roles.
    if role == "user" and credits is None:
        balance = None
    else:
        balance = _Balance(credits=_parse_credits_value(credits or UNLIMITED))
    if role == "user" and jobs is None:
        quota = None
    else:
        quota = _Quota(total_running_jobs=_parse_jobs_value(jobs or UNLIMITED))
    user = await root.client._admin.create_cluster_user(
        cluster_name,
        user_name,
        _ClusterUserRoleType(role),
        org_name=org,
        balance=balance,
        quota=quota,
    )
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
        balance_fmt = BalanceFormatter()
        root.print(quota_fmt(user.quota))
        root.print(balance_fmt(user.balance))


def _parse_finite_decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
        if result.is_finite():
            return result
    except (ValueError, LookupError, InvalidOperation):
        pass
    raise click.BadParameter(f"{value} is not valid decimal number")


def _parse_credits_value(value: str) -> Optional[Decimal]:
    if value == UNLIMITED:
        return None
    return _parse_finite_decimal(value)


def _parse_jobs_value(value: str) -> Optional[int]:
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
    root: Root, cluster_name: str, user_name: str, org: Optional[str]
) -> None:
    """
    Remove user access from the cluster.
    """
    await root.client._admin.delete_cluster_user(cluster_name, user_name, org_name=org)
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
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
async def get_user_quota(
    root: Root,
    cluster_name: str,
    user_name: str,
    org: Optional[str],
) -> None:
    """
    Get info about user quota in given cluster
    """
    user_with_quota = await root.client._admin.get_cluster_user(
        cluster_name=cluster_name,
        user_name=user_name,
        org_name=org,
    )
    quota_fmt = AdminQuotaFormatter()
    balance_fmt = BalanceFormatter()
    root.print(
        f"Quota and balance for [u]{rich_escape(user_with_quota.user_name)}[/u] "
        + (
            f"as member of org [bold]{rich_escape(org)}[/bold] "
            if org is not None
            else ""
        )
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(quota_fmt(user_with_quota.quota))
    root.print(balance_fmt(user_with_quota.balance))


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
    org: Optional[str],
) -> None:
    """
    Set user quota to given values
    """
    user_with_quota = await root.client._admin.update_cluster_user_quota(
        cluster_name=cluster_name,
        user_name=user_name,
        quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
        org_name=org,
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
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
async def set_user_credits(
    root: Root,
    cluster_name: str,
    user_name: str,
    credits: str,
    org: Optional[str],
) -> None:
    """
    Set user credits to given value
    """
    credits_decimal = _parse_credits_value(credits)
    user_with_quota = await root.client._admin.update_cluster_user_balance(
        cluster_name=cluster_name,
        user_name=user_name,
        credits=credits_decimal,
        org_name=org,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for [u]{rich_escape(user_with_quota.user_name)}[/u] "
        + (
            f"as member of org [bold]{rich_escape(org)}[/bold] "
            if org is not None
            else ""
        )
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(fmt(user_with_quota.balance))


@command()
@argument("cluster_name", required=True, type=str)
@argument("user_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Credits amount to add",
)
@option(
    "--org",
    metavar="ORG",
    default=None,
    type=str,
    help="org name for org-cluster users",
)
async def add_user_credits(
    root: Root,
    cluster_name: str,
    user_name: str,
    credits: str,
    org: Optional[str],
) -> None:
    """
    Add given values to user quota
    """
    additional_credits = _parse_finite_decimal(credits)
    user_with_quota = await root.client._admin.update_cluster_user_balance_by_delta(
        cluster_name,
        user_name,
        delta=additional_credits,
        org_name=org,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for [u]{rich_escape(user_with_quota.user_name)}[/u] "
        + (
            f"as member of org [bold]{rich_escape(org)}[/bold] "
            if org is not None
            else ""
        )
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(fmt(user_with_quota.balance))


async def _update_presets_and_fetch(root: Root, presets: Mapping[str, Preset]) -> None:
    cluster_name = root.client.config.cluster_name
    await root.client._admin.update_cluster_resource_presets(cluster_name, presets)

    if root.verbosity >= 1:
        _print = root.print
    else:

        def _print(*args: Any, **kwargs: Any) -> None:
            pass

    _print("Requested presets update")

    async def _sync_local_config() -> None:
        _print("Fetching new server config", end="")
        try:
            while dict(root.client.config.presets) != presets:
                _print(".", end="")
                await root.client.config.fetch()
                await asyncio.sleep(0.5)
        finally:
            _print("")

    try:
        await asyncio.wait_for(_sync_local_config(), 10)
    except asyncio.TimeoutError:
        log.warning(
            "Fetched server presets are not same as new values. "
            "Maybe there was some concurrent update?"
        )


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
    type=MEGABYTE,
    help="Memory amount",
    default=JOB_MEMORY_AMOUNT,
    show_default=True,
)
@option(
    "-g",
    "--gpu",
    metavar="NUMBER",
    type=int,
    help="Number of GPUs",
)
@option(
    "--gpu-model",
    metavar="MODEL",
    help="GPU model",
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
async def add_resource_preset(
    root: Root,
    preset_name: str,
    credits_per_hour: str,
    cpu: float,
    memory: int,
    gpu: Optional[int],
    gpu_model: Optional[str],
    tpu_type: Optional[str],
    tpu_software_version: Optional[str],
    scheduler: bool,
    preemptible_node: bool,
) -> None:
    """
    Add new resource preset
    """
    presets = dict(root.client.config.presets)
    if preset_name in presets:
        raise ValueError(f"Preset '{preset_name}' already exists")
    presets[preset_name] = Preset(
        credits_per_hour=_parse_finite_decimal(credits_per_hour),
        cpu=cpu,
        memory_mb=memory,
        gpu=gpu,
        gpu_model=gpu_model,
        tpu_type=tpu_type,
        tpu_software_version=tpu_software_version,
        scheduler_enabled=scheduler,
        preemptible_node=preemptible_node,
    )
    await _update_presets_and_fetch(root, presets)
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
    type=MEGABYTE,
    help="Memory amount",
)
@option(
    "-g",
    "--gpu",
    metavar="NUMBER",
    type=int,
    help="Number of GPUs",
)
@option(
    "--gpu-model",
    metavar="MODEL",
    help="GPU model",
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
)
@option(
    "--preemptible-node/--non-preemptible-node",
    help="Use a lower-cost preemptible instance",
)
async def update_resource_preset(
    root: Root,
    preset_name: str,
    credits_per_hour: Optional[str],
    cpu: Optional[float],
    memory: Optional[int],
    gpu: Optional[int],
    gpu_model: Optional[str],
    tpu_type: Optional[str],
    tpu_software_version: Optional[str],
    scheduler: Optional[bool],
    preemptible_node: Optional[bool],
) -> None:
    """
    Update existing resource preset
    """
    presets = dict(root.client.config.presets)
    try:
        preset = presets[preset_name]
    except KeyError:
        raise ValueError(f"Preset '{preset_name}' does not exists")

    kwargs = {
        "credits_per_hour": _parse_finite_decimal(credits_per_hour)
        if credits_per_hour is not None
        else None,
        "cpu": cpu,
        "memory_mb": memory,
        "gpu": gpu,
        "gpu_model": gpu_model,
        "tpu_type": tpu_type,
        "tpu_software_version": tpu_software_version,
        "scheduler_enabled": scheduler,
        "preemptible_node": preemptible_node,
    }
    kwargs = {key: value for key, value in kwargs.items() if value is not None}

    presets[preset_name] = replace(preset, **kwargs)

    await _update_presets_and_fetch(root, presets)

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
    await _update_presets_and_fetch(root, presets)
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
async def add_org(root: Root, org_name: str) -> None:
    """
    Create a new org.
    """
    await root.client._admin.create_org(org_name)


@command()
@option("--force", default=False, help="Skip prompt", is_flag=True)
@argument("org_name", required=True, type=str)
async def remove_org(root: Root, org_name: str, force: bool) -> None:
    """
    Drop a org

    Completely removes org from the system.
    """

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
async def add_org_user(
    root: Root,
    org_name: str,
    user_name: str,
    role: str,
) -> None:
    """
    Add user access to specified org.

    The command supports one of 3 user roles: admin, manager or user.
    """
    user = await root.client._admin.create_org_user(
        org_name,
        user_name,
        _OrgUserRoleType(role),
    )
    if not root.quiet:
        root.print(
            f"Added [bold]{rich_escape(user.user_name)}[/bold] to org "
            f"[bold]{rich_escape(org_name)}[/bold] as "
            f"[bold]{rich_escape(user.role)}[/bold]",
            markup=True,
        )


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
async def get_org_clusters(root: Root, cluster_name: str) -> None:
    """
    Print the list of all orgs in the cluster
    """
    fmt = OrgClusterFormatter()
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
async def add_org_cluster(
    root: Root,
    cluster_name: str,
    org_name: str,
    credits: str,
    jobs: str,
    default_credits: str,
    default_jobs: str,
) -> None:
    """
    Add org access to specified cluster.

    """
    await root.client._admin.create_org_cluster(
        cluster_name=cluster_name,
        org_name=org_name,
        balance=_Balance(credits=_parse_credits_value(credits)),
        quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
        default_credits=_parse_credits_value(default_credits),
        default_quota=_Quota(_parse_jobs_value(default_jobs)),
    )
    if not root.quiet:
        root.print(
            f"Added org [bold]{rich_escape(org_name)}[/bold] to "
            f"[bold]{rich_escape(cluster_name)}[/bold]",
            markup=True,
        )


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
async def update_org_cluster(
    root: Root,
    cluster_name: str,
    org_name: str,
    credits: str,
    jobs: str,
    default_credits: str,
    default_jobs: str,
) -> None:
    """
    Update org cluster quotas.

    """
    await root.client._admin.update_org_cluster(
        _OrgCluster(
            cluster_name=cluster_name,
            org_name=org_name,
            balance=_Balance(credits=_parse_credits_value(credits)),
            quota=_Quota(total_running_jobs=_parse_jobs_value(jobs)),
            default_credits=_parse_credits_value(default_credits),
            default_quota=_Quota(_parse_jobs_value(default_jobs)),
        )
    )
    if not root.quiet:
        root.print(
            f"Added org [bold]{rich_escape(org_name)}[/bold] to "
            f"[bold]{rich_escape(cluster_name)}[/bold]",
            markup=True,
        )


@command(hidden=True)
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
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    required=True,
    help="Credits amount to set (`unlimited' stands for no limit)",
)
async def set_org_cluster_credits(
    root: Root,
    cluster_name: str,
    org_name: str,
    credits: str,
) -> None:
    """
    Set org cluster credits to given value
    """
    credits_decimal = _parse_credits_value(credits)
    org = await root.client._admin.update_org_cluster_balance(
        cluster_name=cluster_name,
        org_name=org_name,
        credits=credits_decimal,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for org [u]{rich_escape(org_name)}[/u] "
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(fmt(org.balance))


@command()
@argument("cluster_name", required=True, type=str)
@argument("org_name", required=True, type=str)
@option(
    "-c",
    "--credits",
    metavar="AMOUNT",
    type=str,
    help="Credits amount to add",
)
async def add_org_cluster_credits(
    root: Root,
    cluster_name: str,
    org_name: str,
    credits: str,
) -> None:
    """
    Add given values to org cluster balance
    """
    additional_credits = _parse_finite_decimal(credits)
    assert additional_credits
    org = await root.client._admin.update_org_cluster_balance_by_delta(
        cluster_name,
        org_name,
        delta=additional_credits,
    )
    fmt = BalanceFormatter()
    root.print(
        f"New credits for org [u]{rich_escape(org_name)}[/u] "
        + f"on cluster [u]{rich_escape(cluster_name)}[/u]:",
        markup=True,
    )
    root.print(fmt(org.balance))


admin.add_command(get_clusters)
admin.add_command(get_admin_clusters)
admin.add_command(generate_cluster_config)
admin.add_command(add_cluster)
admin.add_command(update_cluster)
admin.add_command(remove_cluster)
admin.add_command(show_cluster_options)

admin.add_command(get_cluster_users)
admin.add_command(add_cluster_user)
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

admin.add_command(get_org_clusters)
admin.add_command(add_org_cluster)
admin.add_command(update_org_cluster)
admin.add_command(remove_org_cluster)

admin.add_command(get_org_cluster_quota)
admin.add_command(set_org_cluster_quota)
admin.add_command(set_org_cluster_credits)
admin.add_command(add_org_cluster_credits)
