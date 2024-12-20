# Clusters API is experimental,
# remove underscore prefix after stabilizing and making public
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional

import aiohttp
from neuro_config_client import AWSCloudProvider as _AWSCloudProvider
from neuro_config_client import AWSStorage as _AWSStorage
from neuro_config_client import AzureCloudProvider as _AzureCloudProvider
from neuro_config_client import AzureReplicationType as _AzureReplicationType
from neuro_config_client import AzureStorage as _AzureStorage
from neuro_config_client import AzureStorageTier as _AzureStorageTier
from neuro_config_client import CloudProvider as _CloudProvider
from neuro_config_client import CloudProviderOptions as _CloudProviderOptions
from neuro_config_client import CloudProviderType as _CloudProviderType
from neuro_config_client import Cluster as _ConfigCluster
from neuro_config_client import ClusterStatus as _ClusterStatus
from neuro_config_client import ConfigClientBase
from neuro_config_client import EFSPerformanceMode as _EFSPerformanceMode
from neuro_config_client import EFSThroughputMode as _EFSThroughputMode
from neuro_config_client import EnergyConfig as _EnergyConfig
from neuro_config_client import EnergySchedule as _EnergySchedule
from neuro_config_client import EnergySchedulePeriod as _EnergySchedulePeriod
from neuro_config_client import GoogleCloudProvider as _GoogleCloudProvider
from neuro_config_client import GoogleFilestoreTier as _GoogleFilestoreTier
from neuro_config_client import GoogleStorage as _GoogleStorage
from neuro_config_client import NodePool as _NodePool
from neuro_config_client import NodePoolOptions as _NodePoolOptions
from neuro_config_client import OnPremCloudProvider as _OnPremCloudProvider
from neuro_config_client import PatchNodePoolSizeRequest as _PatchNodePoolSizeRequest
from neuro_config_client import ResourcePreset as _ResourcePreset
from neuro_config_client import Storage as _Storage
from neuro_config_client import StorageInstance as _StorageInstance
from neuro_config_client import TPUPreset as _TPUPreset
from neuro_config_client import VCDCloudProvider as _VCDCloudProvider
from neuro_config_client import VCDCloudProviderOptions as _VCDCloudProviderOptions
from neuro_config_client import VCDStorage as _VCDStorage

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor

# Explicit __all__ to re-export neuro_config_client entities

__all__ = [
    "_AWSCloudProvider",
    "_AWSStorage",
    "_AzureCloudProvider",
    "_AzureReplicationType",
    "_AzureStorage",
    "_AzureStorageTier",
    "_CloudProvider",
    "_CloudProviderOptions",
    "_CloudProviderType",
    "_ClusterStatus",
    "_Clusters",
    "_ConfigCluster",
    "_EFSPerformanceMode",
    "_EFSThroughputMode",
    "_EnergyConfig",
    "_EnergySchedule",
    "_EnergySchedulePeriod",
    "_GoogleCloudProvider",
    "_GoogleFilestoreTier",
    "_GoogleStorage",
    "_NodePool",
    "_NodePoolOptions",
    "_OnPremCloudProvider",
    "_ResourcePreset",
    "_Storage",
    "_StorageInstance",
    "_TPUPreset",
    "_VCDCloudProvider",
    "_VCDCloudProviderOptions",
    "_VCDStorage",
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
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
        headers: Optional[Mapping[str, str]] = None,
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

    async def setup_cluster_cloud_provider(
        self, name: str, config: Dict[str, Any]
    ) -> None:
        auth = await self._config._api_auth()
        url = self._config.api_url / "clusters" / name / "cloud_provider"
        url = url.with_query(start_deployment="true")
        async with self._core.request("PUT", url, auth=auth, json=config):
            pass


@rewrite_module
class _Clusters(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._client = _ConfigClient(core, config)

    async def list(self) -> List[_ConfigCluster]:
        clusters = await self._client.list_clusters()
        return list(clusters)

    async def list_cloud_provider_options(self) -> List[_CloudProviderOptions]:
        return await self._client.list_cloud_provider_options()

    async def get_cloud_provider_options(
        self, type: _CloudProviderType
    ) -> _CloudProviderOptions:
        return await self._client.get_cloud_provider_options(type)

    async def setup_cluster_cloud_provider(
        self, name: str, config: Dict[str, Any]
    ) -> None:
        await self._client.setup_cluster_cloud_provider(name, config)

    async def update_node_pool(
        self, cluster_name: str, node_pool_name: str, request: _PatchNodePoolSizeRequest
    ) -> None:
        await self._client.patch_node_pool(cluster_name, node_pool_name, request)

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
