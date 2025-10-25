import logging
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from dateutil.parser import isoparse
from yarl import URL

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager

logger = logging.getLogger(__package__)


@rewrite_module
@dataclass(frozen=True)
class Disk:
    id: str
    storage: int  # In bytes
    owner: str
    status: "Disk.Status"
    cluster_name: str
    project_name: str
    org_name: str
    created_at: datetime
    last_usage: Optional[datetime] = None
    name: Optional[str] = None
    timeout_unused: Optional[timedelta] = None
    used_bytes: Optional[int] = None

    @property
    def uri(self) -> URL:
        base = f"disk://{self.cluster_name}"
        if self.org_name:
            base += f"/{self.org_name}"
        return URL(f"{base}/{self.project_name}/{self.id}")

    class Status(Enum):
        PENDING = "Pending"
        READY = "Ready"
        BROKEN = "Broken"


@rewrite_module
class Disks(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    def _parse_disk_payload(self, payload: Mapping[str, Any]) -> Disk:
        last_usage_raw = payload.get("last_usage")
        if last_usage_raw is not None:
            last_usage: Optional[datetime] = isoparse(last_usage_raw)
        else:
            last_usage = None
        life_span_raw = payload.get("life_span")
        if life_span_raw is not None:
            timeout_unused: Optional[timedelta] = timedelta(seconds=life_span_raw)
        else:
            timeout_unused = None
        org_name = payload.get("org_name")
        if not org_name:
            raise ValueError("org_name is required for disks")
        return Disk(
            id=payload["id"],
            storage=payload["storage"],
            used_bytes=payload.get("used_bytes"),
            owner=payload["owner"],
            project_name=payload["project_name"],
            name=payload.get("name"),
            status=Disk.Status(payload["status"]),
            cluster_name=self._config.cluster_name,
            org_name=org_name,
            created_at=isoparse(payload["created_at"]),
            last_usage=last_usage,
            timeout_unused=timeout_unused,
        )

    def _get_disks_url(self, cluster_name: Optional[str]) -> URL:
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        return self._config.get_cluster(cluster_name).disks_url

    @asyncgeneratorcontextmanager
    async def list(
        self,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[Disk]:
        url = self._get_disks_url(cluster_name)
        params = {}
        params["org_name"] = org_name or self._config.org_name
        if project_name:
            params["project_name"] = project_name

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth, params=params) as resp:
            ret = await resp.json()
            for disk_payload in ret:
                yield self._parse_disk_payload(disk_payload)

    async def create(
        self,
        storage: int,
        timeout_unused: Optional[timedelta] = None,
        name: Optional[str] = None,
        cluster_name: Optional[str] = None,
        project_name: Optional[str] = None,
        org_name: Optional[str] = None,
    ) -> Disk:
        url = self._get_disks_url(cluster_name)
        auth = await self._config._api_auth()
        data = {
            "storage": storage,
            "life_span": timeout_unused.total_seconds() if timeout_unused else None,
            "name": name,
            "project_name": project_name or self._config.project_name_or_raise,
            "org_name": org_name or self._config.org_name,
        }
        async with self._core.request("POST", url, auth=auth, json=data) as resp:
            payload = await resp.json()
            return self._parse_disk_payload(payload)

    async def get(
        self,
        disk_id_or_name: str,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Disk:
        url = self._get_disks_url(cluster_name) / disk_id_or_name
        auth = await self._config._api_auth()
        params = self._get_url_params(org_name, project_name)
        async with self._core.request("GET", url, auth=auth, params=params) as resp:
            payload = await resp.json()
            return self._parse_disk_payload(payload)

    async def rm(
        self,
        disk_id_or_name: str,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> None:
        url = self._get_disks_url(cluster_name) / disk_id_or_name
        auth = await self._config._api_auth()
        params = self._get_url_params(org_name, project_name)
        async with self._core.request("DELETE", url, auth=auth, params=params):
            pass

    def _get_url_params(
        self,
        org_name: Optional[str],
        project_name: Optional[str],
    ) -> dict[str, str]:
        params = {
            "project_name": project_name or self._config.project_name_or_raise,
        }
        org_name_val = org_name or self._config.org_name
        if org_name_val:
            params["org_name"] = org_name_val
        return params
