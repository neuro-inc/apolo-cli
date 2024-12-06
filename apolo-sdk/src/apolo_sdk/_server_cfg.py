from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

import aiohttp
from yarl import URL

from ._errors import AuthError
from ._login import _AuthConfig
from ._rewrite import rewrite_module


@rewrite_module
@dataclass(frozen=True)
class Preset:
    credits_per_hour: Decimal
    cpu: float
    memory: int
    nvidia_gpu: Optional[int] = None
    amd_gpu: Optional[int] = None
    intel_gpu: Optional[int] = None
    nvidia_gpu_model: Optional[str] = None
    amd_gpu_model: Optional[str] = None
    intel_gpu_model: Optional[str] = None
    scheduler_enabled: bool = False
    preemptible_node: bool = False
    tpu_type: Optional[str] = None
    tpu_software_version: Optional[str] = None
    resource_pool_names: tuple[str, ...] = ()
    available_resource_pool_names: tuple[str, ...] = ()

    @property
    def memory_mb(self) -> int:
        return self.memory // 2**20


@dataclass(frozen=True)
class TPUResource:
    ipv4_cidr_block: str
    types: Sequence[str] = ()
    software_versions: Sequence[str] = ()


@rewrite_module
@dataclass(frozen=True)
class ResourcePool:
    min_size: int
    max_size: int
    cpu: float
    memory: int
    disk_size: int
    nvidia_gpu: Optional[int] = None
    amd_gpu: Optional[int] = None
    intel_gpu: Optional[int] = None
    nvidia_gpu_model: Optional[str] = None
    amd_gpu_model: Optional[str] = None
    intel_gpu_model: Optional[str] = None
    tpu: Optional[TPUResource] = None
    is_preemptible: bool = False


@rewrite_module
@dataclass(frozen=True)
class Project:
    @dataclass(frozen=True)
    class Key:
        cluster_name: str
        org_name: str
        project_name: str

    cluster_name: str
    org_name: str
    name: str
    role: str

    @property
    def key(self) -> Key:
        return self.Key(
            cluster_name=self.cluster_name,
            org_name=self.org_name,
            project_name=self.name,
        )


@rewrite_module
@dataclass(frozen=True)
class AppsConfig:
    hostname_templates: Sequence[str] = ()


@rewrite_module
@dataclass(frozen=True)
class Cluster:
    name: str
    orgs: List[str]
    registry_url: URL
    storage_url: URL
    users_url: URL
    monitoring_url: URL
    secrets_url: URL
    disks_url: URL
    buckets_url: URL
    resource_pools: Mapping[str, ResourcePool]
    presets: Mapping[str, Preset]
    apps: AppsConfig


@dataclass(frozen=True)
class _ServerConfig:
    admin_url: Optional[URL]
    auth_config: _AuthConfig
    clusters: Mapping[str, Cluster]
    projects: Mapping[Project.Key, Project]


def _parse_project_config(payload: Dict[str, Any]) -> Project:
    return Project(
        name=payload["name"],
        cluster_name=payload["cluster_name"],
        org_name=payload.get("org_name") or "NO_ORG",
        role=payload["role"],
    )


def _parse_projects(payload: Dict[str, Any]) -> Dict[Project.Key, Project]:
    ret: Dict[Project.Key, Project] = {}
    for item in payload.get("projects", []):
        project = _parse_project_config(item)
        ret[project.key] = project
    return ret


def _parse_cluster_config(payload: Dict[str, Any]) -> Cluster:
    resource_pools = {}
    for data in payload["resource_pool_types"]:
        tpu = None
        if "tpu" in data:
            tpu = TPUResource(
                types=data["tpu"]["types"],
                software_versions=data["tpu"]["software_versions"],
                ipv4_cidr_block=data["tpu"]["ipv4_cidr_block"],
            )
        resource_pools[data["name"]] = ResourcePool(
            min_size=data["min_size"],
            max_size=data["max_size"],
            cpu=data["cpu"],
            memory=data["memory"],
            disk_size=data["disk_size"],
            nvidia_gpu=data.get("nvidia_gpu"),
            amd_gpu=data.get("amd_gpu"),
            intel_gpu=data.get("intel_gpu"),
            nvidia_gpu_model=data.get("nvidia_gpu_model"),
            amd_gpu_model=data.get("amd_gpu_model"),
            intel_gpu_model=data.get("intel_gpu_model"),
            tpu=tpu,
            is_preemptible=data.get("is_preemptible", False),
        )
    presets: Dict[str, Preset] = {}
    for data in payload["resource_presets"]:
        tpu_type = tpu_software_version = None
        if "tpu" in data:
            tpu_payload = data["tpu"]
            tpu_type = tpu_payload["type"]
            tpu_software_version = tpu_payload["software_version"]
        presets[data["name"]] = Preset(
            credits_per_hour=Decimal(data["credits_per_hour"]),
            cpu=data["cpu"],
            memory=data["memory"],
            nvidia_gpu=data.get("nvidia_gpu"),
            amd_gpu=data.get("amd_gpu"),
            intel_gpu=data.get("intel_gpu"),
            nvidia_gpu_model=data.get("nvidia_gpu_model"),
            amd_gpu_model=data.get("amd_gpu_model"),
            intel_gpu_model=data.get("intel_gpu_model"),
            scheduler_enabled=data.get("scheduler_enabled", False),
            preemptible_node=data.get("preemptible_node", False),
            tpu_type=tpu_type,
            tpu_software_version=tpu_software_version,
            resource_pool_names=tuple(data.get("resource_pool_names", ())),
            available_resource_pool_names=tuple(
                data.get("available_resource_pool_names", ())
            ),
        )
    orgs = payload.get("orgs")
    if not orgs:
        orgs = ["NO_ORG"]
    else:
        orgs = [org if org is not None else "NO_ORG" for org in orgs]

    apps_payload = payload.get("apps", {})
    if apps_payload:
        apps_config = AppsConfig(
            hostname_templates=apps_payload.get("apps_hostname_templates", [])
        )
    else:
        apps_config = AppsConfig()

    cluster_config = Cluster(
        name=payload["name"],
        orgs=orgs,
        registry_url=URL(payload["registry_url"]),
        storage_url=URL(payload["storage_url"]),
        users_url=URL(payload["users_url"]),
        monitoring_url=URL(payload["monitoring_url"]),
        secrets_url=URL(payload["secrets_url"]),
        disks_url=URL(payload["disks_url"]),
        buckets_url=URL(payload["buckets_url"]),
        resource_pools=resource_pools,
        presets=presets,
        apps=apps_config,
    )
    return cluster_config


def _parse_clusters(payload: Dict[str, Any]) -> Dict[str, Cluster]:
    ret: Dict[str, Cluster] = {}
    for item in payload.get("clusters", []):
        cluster = _parse_cluster_config(item)
        ret[cluster.name] = cluster
    return ret


async def get_server_config(
    client: aiohttp.ClientSession, url: URL, token: Optional[str] = None
) -> _ServerConfig:
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with client.get(url / "config", headers=headers) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Unable to get server configuration: {resp.status}")
        payload = await resp.json()
        # TODO (ajuszkowski, 5-Feb-2019) validate received data
        success_redirect_url = URL(payload.get("success_redirect_url", "")) or None
        callback_urls = payload.get("callback_urls")
        callback_urls = (
            tuple(URL(u) for u in callback_urls)
            if callback_urls is not None
            else _AuthConfig.callback_urls
        )
        headless_callback_url = URL(payload["headless_callback_url"])
        auth_config = _AuthConfig(
            auth_url=URL(payload["auth_url"]),
            token_url=URL(payload["token_url"]),
            logout_url=URL(payload["logout_url"]),
            client_id=payload["client_id"],
            audience=payload["audience"],
            success_redirect_url=success_redirect_url,
            callback_urls=callback_urls,
            headless_callback_url=headless_callback_url,
        )
        admin_url: Optional[URL] = None
        if "admin_url" in payload:
            admin_url = URL(payload["admin_url"])
        if headers and not payload.get("authorized", False):
            raise AuthError("Cannot authorize user")
        clusters = _parse_clusters(payload)
        projects = _parse_projects(payload)
        return _ServerConfig(
            admin_url=admin_url,
            auth_config=auth_config,
            clusters=clusters,
            projects=projects,
        )
