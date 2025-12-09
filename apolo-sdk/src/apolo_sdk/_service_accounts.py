import logging
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dateutil.parser import isoparse

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager

logger = logging.getLogger(__package__)


@rewrite_module
@dataclass(frozen=True)
class ServiceAccount:
    id: str
    name: str | None
    owner: str
    default_cluster: str
    role: str
    created_at: datetime
    default_project: str
    default_org: str | None = None


@rewrite_module
class ServiceAccounts(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    def _parse_account_payload(self, payload: Mapping[str, Any]) -> ServiceAccount:
        return ServiceAccount(
            id=payload["id"],
            owner=payload["owner"],
            name=payload["name"],
            default_cluster=payload["default_cluster"],
            role=payload["role"],
            created_at=isoparse(payload["created_at"]),
            default_project=payload["default_project"],
            default_org=payload.get("default_org"),
        )

    @asyncgeneratorcontextmanager
    async def list(self) -> AsyncIterator[ServiceAccount]:
        url = self._config.service_accounts_url
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            ret = await resp.json()
            for item in ret:
                yield self._parse_account_payload(item)

    async def create(
        self,
        name: str | None = None,
        default_cluster: str | None = None,
        default_org: str | None = None,
        default_project: str | None = None,
    ) -> tuple[ServiceAccount, str]:
        url = self._config.service_accounts_url
        auth = await self._config._api_auth()
        data = {
            "name": name,
            "default_cluster": default_cluster or self._config.cluster_name,
            "default_project": default_project or self._config.project_name_or_raise,
        }
        default_org = default_org or self._config.org_name
        if default_org:
            data["default_org"] = default_org
        async with self._core.request("POST", url, auth=auth, json=data) as resp:
            payload = await resp.json()
            return self._parse_account_payload(payload), payload["token"]

    async def get(self, id_or_name: str) -> ServiceAccount:
        url = self._config.service_accounts_url / id_or_name
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            payload = await resp.json()
            return self._parse_account_payload(payload)

    async def rm(self, id_or_name: str) -> None:
        url = self._config.service_accounts_url / id_or_name
        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth):
            pass
