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
        resource_pools[data["name"]] = ResourcePool(
            min_size=data["min_size"],
            max_size=data["max_size"],
            cpu=data["cpu"],
            memory=data["memory"],
            disk_size=data["disk_size"],
            nvidia_gpu=_parse_nvidia_gpu(data),
            amd_gpu=_parse_amd_gpu(data),
            intel_gpu=_parse_intel_gpu(data),
            tpu=_parse_tpu(payload.get("tpu")),
            is_preemptible=data.get("is_preemptible", False),
        )
    presets: Dict[str, Preset] = {}
    for data in payload["resource_presets"]:
        presets[data["name"]] = Preset(
            credits_per_hour=Decimal(data["credits_per_hour"]),
            cpu=data["cpu"],
            memory=data["memory"],
            nvidia_gpu=_parse_nvidia_gpu_preset(data),
            amd_gpu=_parse_amd_gpu_preset(data),
            intel_gpu=_parse_intel_gpu_preset(data),
            tpu=_parse_tpu_preset(data.get("tpu")),
            scheduler_enabled=data.get("scheduler_enabled", False),
            preemptible_node=data.get("preemptible_node", False),
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


def _parse_nvidia_gpu(payload: Dict[str, Any]) -> Optional[NvidiaGPU]:
    nvidia_gpu = payload.get("nvidia_gpu")
    if not nvidia_gpu:
        return None
    if isinstance(nvidia_gpu, int):
        return NvidiaGPU(
            count=nvidia_gpu,
            model=payload["nvidia_gpu_model"],
        )
    payload = nvidia_gpu
    return NvidiaGPU(
        count=payload["count"],
        model=payload["model"],
        memory=payload.get("memory"),
    )


def _parse_amd_gpu(payload: Dict[str, Any]) -> Optional[AMDGPU]:
    amd_gpu = payload.get("amd_gpu")
    if not amd_gpu:
        return None
    if isinstance(amd_gpu, int):
        return AMDGPU(
            count=amd_gpu,
            model=payload["amd_gpu_model"],
        )
    payload = amd_gpu
    return AMDGPU(
        count=payload["count"],
        model=payload["model"],
        memory=payload.get("memory"),
    )


def _parse_intel_gpu(payload: Dict[str, Any]) -> Optional[IntelGPU]:
    intel_gpu = payload.get("intel_gpu")
    if not intel_gpu:
        return None
    if isinstance(intel_gpu, int):
        return IntelGPU(
            count=intel_gpu,
            model=payload["intel_gpu_model"],
        )
    payload = intel_gpu
    return IntelGPU(
        count=payload["count"],
        model=payload["model"],
        memory=payload.get("memory"),
    )


def _parse_tpu(payload: Optional[Dict[str, Any]]) -> Optional[TPUResource]:
    if not payload:
        return None
    return TPUResource(
        types=payload["types"],
        software_versions=payload["software_versions"],
        ipv4_cidr_block=payload["ipv4_cidr_block"],
    )


def _parse_nvidia_gpu_preset(payload: Dict[str, Any]) -> Optional[NvidiaGPUPreset]:
    nvidia_gpu = payload.get("nvidia_gpu")
    if not nvidia_gpu:
        return None
    if isinstance(nvidia_gpu, int):
        return NvidiaGPUPreset(
            count=nvidia_gpu,
            model=payload.get("nvidia_gpu_model"),
        )
    payload = nvidia_gpu
    return NvidiaGPUPreset(
        count=payload["count"],
        model=payload.get("model"),
        memory=payload.get("memory"),
    )


def _parse_amd_gpu_preset(payload: Dict[str, Any]) -> Optional[AMDGPUPreset]:
    amd_gpu = payload.get("amd_gpu")
    if not amd_gpu:
        return None
    if isinstance(amd_gpu, int):
        return AMDGPUPreset(
            count=amd_gpu,
            model=payload.get("amd_gpu_model"),
        )
    payload = amd_gpu
    return AMDGPUPreset(
        count=payload["count"],
        model=payload.get("model"),
        memory=payload.get("memory"),
    )


def _parse_intel_gpu_preset(payload: Dict[str, Any]) -> Optional[IntelGPUPreset]:
    intel_gpu = payload.get("intel_gpu")
    if not intel_gpu:
        return None
    if isinstance(intel_gpu, int):
        return IntelGPUPreset(
            count=intel_gpu,
            model=payload.get("intel_gpu_model"),
        )
    payload = intel_gpu
    return IntelGPUPreset(
        count=payload["count"],
        model=payload.get("model"),
        memory=payload.get("memory"),
    )


def _parse_tpu_preset(payload: Optional[Dict[str, Any]]) -> Optional[TPUPreset]:
    if not payload:
        return None
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
