from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from yarl import URL

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager

YEAR = timedelta(days=365)


@rewrite_module
@dataclass(frozen=True)
class KubeServiceAccount:
    user: str
    name: str
    created_at: datetime
    expired_at: datetime


@rewrite_module
class VCluster(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    def _build_base_url(
        self,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> URL:
        cluster_name = cluster_name or self._config.cluster_name
        if org_name is None:
            org_name = self._config.org_name
            if org_name is None:
                raise ValueError("Organization name is required")
        if project_name is None:
            project_name = self._config.project_name
            if project_name is None:
                raise ValueError("Project name is required")

        url = (
            self._config.vcluster_url
            / "kube/cluster"
            / cluster_name
            / "org"
            / org_name
            / "project"
            / project_name
        )
        return url

    async def create_service_account(
        self,
        name: str,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        ttl: timedelta = YEAR,
    ) -> Any:
        url = self._build_base_url(cluster_name, org_name, project_name) / "config"
        auth = await self._config._api_auth()
        async with self._core.request(
            "POST", url, auth=auth, json={"name": name, "ttl": ttl.isoformat()}
        ) as resp:
            resp.raise_for_status()
            ret = await resp.json()
            return ret

    @asyncgeneratorcontextmanager
    async def list_service_accounts(
        self,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[KubeServiceAccount]:
        url = self._build_base_url(cluster_name, org_name, project_name) / "config"
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            ret = await resp.json()
            assert isinstance(ret, list)
            for item in ret:
                yield KubeServiceAccount(**item)

    async def delete_service_account(
        self,
        name: str,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> KubeServiceAccount:
        url = (
            self._build_base_url(cluster_name, org_name, project_name) / "config" / name
        )
        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth) as resp:
            resp.raise_for_status()
            ret = await resp.json()
            return KubeServiceAccount(**ret)
