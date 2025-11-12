from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

import aiohttp
from yarl import URL

from ._errors import AuthError
from ._login import _AuthConfig
from ._rewrite import rewrite_module


@dataclass(frozen=True)
class _GPUPreset:
    count: int
    model: Optional[str] = None
    memory: Optional[int] = None


@rewrite_module
@dataclass(frozen=True)
class NvidiaGPUPreset(_GPUPreset):
    pass


@rewrite_module
@dataclass(frozen=True)
class AMDGPUPreset(_GPUPreset):
    pass


@rewrite_module
@dataclass(frozen=True)
class IntelGPUPreset(_GPUPreset):
    pass


@rewrite_module
@dataclass(frozen=True)
class TPUPreset:
    type: str
    software_version: str


@rewrite_module
@dataclass(frozen=True)
class Preset:
    credits_per_hour: Decimal
    cpu: float
    memory: int
    nvidia_gpu: Optional[NvidiaGPUPreset] = None
    nvidia_migs: Optional[Mapping[str, NvidiaGPUPreset]] = None
    amd_gpu: Optional[AMDGPUPreset] = None
    intel_gpu: Optional[IntelGPUPreset] = None
    tpu: Optional[TPUPreset] = None
    scheduler_enabled: bool = False
    preemptible_node: bool = False
    resource_pool_names: tuple[str, ...] = ()
    available_resource_pool_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class _GPU:
    count: int
    model: str
    memory: Optional[int] = None


@rewrite_module
@dataclass(frozen=True)
class NvidiaGPU(_GPU):
    pass


@rewrite_module
@dataclass(frozen=True)
class AMDGPU(_GPU):
    pass


@rewrite_module
@dataclass(frozen=True)
class IntelGPU(_GPU):
    pass


@rewrite_module
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
    nvidia_gpu: Optional[NvidiaGPU] = None
    nvidia_migs: Optional[Mapping[str, NvidiaGPU]] = None
    amd_gpu: Optional[AMDGPU] = None
    intel_gpu: Optional[IntelGPU] = None
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


def _parse_project_config(payload: Dict[str, Any]) -> Optional[Project]:
    org_name = payload.get("org_name")
    if not org_name:
        # ignore old-fashioned projects without org_name,
        # since they still might be in db
        return None
    return Project(
        name=payload["name"],
        cluster_name=payload["cluster_name"],
        org_name=org_name,
        role=payload["role"],
    )


def _parse_projects(payload: Dict[str, Any]) -> Dict[Project.Key, Project]:
    ret: Dict[Project.Key, Project] = {}
    for item in payload.get("projects", []):
        project = _parse_project_config(item)
        if project:
            ret[project.key] = project
    return ret


def _parse_cluster_config(payload: Dict[str, Any]) -> Cluster:
    resource_pools = {}
    for data in payload["resource_pool_types"]:
        resource_pools[data["name"]] = ResourcePool(
            min_size=data["min_size"],
            max_size=data["max_size"],
            cpu=data["cpu"],
            memory=data["memory"],
            disk_size=data["disk_size"],
            nvidia_gpu=(
                _parse_nvidia_gpu(nvidia_gpu_data)
                if (nvidia_gpu_data := data.get("nvidia_gpu"))
                else None
            ),
            nvidia_migs=(
                {
                    key: _parse_nvidia_gpu(value)
                    for key, value in nvidia_migs_data.items()
                }
                if (nvidia_migs_data := data.get("nvidia_migs"))
                else None
            ),
            amd_gpu=(
                _parse_amd_gpu(amd_gpu_data)
                if (amd_gpu_data := data.get("amd_gpu"))
                else None
            ),
            intel_gpu=(
                _parse_intel_gpu(intel_gpu_data)
                if (intel_gpu_data := data.get("intel_gpu"))
                else None
            ),
            tpu=(_parse_tpu(tpu_data) if (tpu_data := payload.get("tpu")) else None),
            is_preemptible=data.get("is_preemptible", False),
        )
    presets: Dict[str, Preset] = {}
    for data in payload["resource_presets"]:
        presets[data["name"]] = Preset(
            credits_per_hour=Decimal(data["credits_per_hour"]),
            cpu=data["cpu"],
            memory=data["memory"],
            nvidia_gpu=(
                _parse_nvidia_gpu_preset(nvidia_gpu_data)
                if (nvidia_gpu_data := data.get("nvidia_gpu"))
                else None
            ),
            nvidia_migs=(
                {
                    key: _parse_nvidia_gpu_preset(value)
                    for key, value in nvidia_migs_data.items()
                }
                if (nvidia_migs_data := data.get("nvidia_migs"))
                else None
            ),
            amd_gpu=(
                _parse_amd_gpu_preset(amd_gpu_data)
                if (amd_gpu_data := data.get("amd_gpu"))
                else None
            ),
            intel_gpu=(
                _parse_intel_gpu_preset(intel_gpu_data)
                if (intel_gpu_data := data.get("intel_gpu"))
                else None
            ),
            tpu=(
                _parse_tpu_preset(tpu_data) if (tpu_data := data.get("tpu")) else None
            ),
            scheduler_enabled=data.get("scheduler_enabled", False),
            preemptible_node=data.get("preemptible_node", False),
            resource_pool_names=tuple(data.get("resource_pool_names", ())),
            available_resource_pool_names=tuple(
                data.get("available_resource_pool_names", ())
            ),
        )
    orgs = payload.get("orgs") or []

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


def _parse_nvidia_gpu(payload: Dict[str, Any]) -> NvidiaGPU:
    return NvidiaGPU(
        count=payload["count"],
        model=payload["model"],
        memory=payload.get("memory"),
    )


def _parse_amd_gpu(payload: Dict[str, Any]) -> AMDGPU:
    return AMDGPU(
        count=payload["count"],
        model=payload["model"],
        memory=payload.get("memory"),
    )


def _parse_intel_gpu(payload: Dict[str, Any]) -> IntelGPU:
    return IntelGPU(
        count=payload["count"],
        model=payload["model"],
        memory=payload.get("memory"),
    )


def _parse_tpu(payload: Dict[str, Any]) -> TPUResource:
    return TPUResource(
        types=payload["types"],
        software_versions=payload["software_versions"],
        ipv4_cidr_block=payload["ipv4_cidr_block"],
    )


def _parse_nvidia_gpu_preset(payload: Dict[str, Any]) -> NvidiaGPUPreset:
    return NvidiaGPUPreset(
        count=payload["count"],
        model=payload.get("model"),
        memory=payload.get("memory"),
    )


def _parse_amd_gpu_preset(payload: Dict[str, Any]) -> AMDGPUPreset:
    return AMDGPUPreset(
        count=payload["count"],
        model=payload.get("model"),
        memory=payload.get("memory"),
    )


def _parse_intel_gpu_preset(payload: Dict[str, Any]) -> IntelGPUPreset:
    return IntelGPUPreset(
        count=payload["count"],
        model=payload.get("model"),
        memory=payload.get("memory"),
    )


def _parse_tpu_preset(payload: Dict[str, Any]) -> TPUPreset:
    return TPUPreset(
        type=payload["type"],
        software_version=payload["software_version"],
    )


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
