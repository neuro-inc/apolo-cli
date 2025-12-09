# Clusters API is experimental,
# remove underscore prefix after stabilizing and making public
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from neuro_config_client import AMDGPU as _AMDGPU
from neuro_config_client import AMDGPUPreset as _AMDGPUPreset
from neuro_config_client import Cluster as _ConfigCluster
from neuro_config_client import (
    ConfigClientBase,
)
from neuro_config_client import EnergyConfig as _EnergyConfig
from neuro_config_client import EnergySchedule as _EnergySchedule
from neuro_config_client import EnergySchedulePeriod as _EnergySchedulePeriod
from neuro_config_client import IntelGPU as _IntelGPU
from neuro_config_client import IntelGPUPreset as _IntelGPUPreset
from neuro_config_client import NvidiaGPU as _NvidiaGPU
from neuro_config_client import NvidiaGPUPreset as _NvidiaGPUPreset
from neuro_config_client import ResourcePoolType as _ResourcePoolType
from neuro_config_client import ResourcePreset as _ResourcePreset
from neuro_config_client import TPUPreset as _TPUPreset
from neuro_config_client import TPUResource as _TPUResource

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor

# Explicit __all__ to re-export neuro_config_client entities

__all__ = [
    "_AMDGPU",
    "_AMDGPUPreset",
    "_Clusters",
    "_ConfigCluster",
    "_EnergyConfig",
    "_EnergySchedule",
    "_EnergySchedulePeriod",
    "_IntelGPU",
    "_IntelGPUPreset",
    "_NvidiaGPU",
    "_NvidiaGPUPreset",
    "_ResourcePoolType",
    "_ResourcePreset",
    "_TPUPreset",
    "_TPUResource",
]


class _ConfigClient(ConfigClientBase):
    def __init__(self, core: _Core, config: Config) -> None:
        super().__init__()

        self._core = core
        self._config = config

    @asynccontextmanager
    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        url = self._config.api_url / path
        auth = await self._config._api_auth()
        async with self._core.request(
            method=method,
            url=url,
            params=params,
            json=json,
            auth=auth,
            headers=headers,
        ) as resp:
            yield resp


@rewrite_module
class _Clusters(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._client = _ConfigClient(core, config)

    async def list(self) -> list[_ConfigCluster]:
        clusters = await self._client.list_clusters()
        return list(clusters)

    async def add_resource_preset(
        self, cluster_name: str, preset: _ResourcePreset
    ) -> None:
        await self._client.add_resource_preset(cluster_name, preset)

    async def update_resource_preset(
        self, cluster_name: str, preset: _ResourcePreset
    ) -> None:
        await self._client.put_resource_preset(cluster_name, preset)

    async def remove_resource_preset(self, cluster_name: str, preset_name: str) -> None:
        await self._client.delete_resource_preset(cluster_name, preset_name)

    async def get_cluster(self, cluster_name: str) -> _ConfigCluster:
        return await self._client.get_cluster(cluster_name)
