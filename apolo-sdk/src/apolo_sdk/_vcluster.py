from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

import yaml
from dateutil.parser import isoparse
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

    @classmethod
    def _parse(cls, item: dict[str, str]) -> "KubeServiceAccount":
        return cls(
            name=item["name"],
            user=item["user"],
            created_at=isoparse(item["created_at"]),
            expired_at=isoparse(item["expired_at"]),
        )


@rewrite_module
class VCluster(metaclass=NoPublicConstructor):
    DEFAULT_TTL: ClassVar[timedelta] = YEAR

    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    def _build_base_url(
        self,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> URL:
        pk = self._config.get_project_key(cluster_name, org_name, project_name)
        assert self._config.vcluster_url is not None, "Old server version"
        url = (
            self._config.vcluster_url
            / "kube/cluster"
            / pk.cluster_name
            / "org"
            / pk.org_name
            / "project"
            / pk.project_name
        )
        return url

    def _write_config(
        self,
        *,
        name: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        config: str,
    ) -> None:
        pk = self._config.get_project_key(cluster_name, org_name, project_name)
        folder = self._config.path / pk.cluster_name / pk.org_name / pk.project_name
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        fname = folder / f"{self._config.username}-{name}.yaml"
        fname.touch(mode=0o600)
        fname.write_text(config)

    async def create_service_account(
        self,
        name: str,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        ttl: timedelta = YEAR,
    ) -> str:
        url = self._build_base_url(cluster_name, org_name, project_name) / "config"
        auth = await self._config._api_auth()
        async with self._core.request(
            "POST", url, auth=auth, json={"name": name, "ttl": ttl.total_seconds()}
        ) as resp:
            resp.raise_for_status()
            ret = await resp.text()
            self._write_config(
                name=name,
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
                config=ret,
            )
            return ret

    async def regenerate_service_account(
        self,
        name: str,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        ttl: timedelta = YEAR,
    ) -> str:
        url = (
            self._build_base_url(cluster_name, org_name, project_name) / "config" / name
        )
        auth = await self._config._api_auth()
        async with self._core.request(
            "PUT", url, auth=auth, json={"ttl": ttl.total_seconds()}
        ) as resp:
            resp.raise_for_status()
            ret = await resp.text()
            self._write_config(
                name=name,
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
                config=ret,
            )
            return ret

    async def activate_service_account(
        self,
        name: str,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> None:
        pk = self._config.get_project_key(cluster_name, org_name, project_name)
        folder = self._config.path / pk.cluster_name / pk.org_name / pk.project_name
        fname = folder / f"{self._config.username}-{name}.yaml"
        kube_config_folder = Path.home() / ".kube"
        kube_config_fname = kube_config_folder / "config"
        with fname.open() as fp:
            config = yaml.safe_load(fp)
        if kube_config_fname.exists():
            with kube_config_fname.open() as fp:
                kube_config = yaml.safe_load(fp)
        else:
            kube_config_folder.mkdir(parents=True, exist_ok=True)
            kube_config = {}
        _merge_configs(kube_config, config)
        with kube_config_fname.open("w") as fp:
            yaml.safe_dump(kube_config, fp)

    @asyncgeneratorcontextmanager
    async def list_service_accounts(
        self,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        all_users: bool = False,
    ) -> AsyncIterator[KubeServiceAccount]:
        url = self._build_base_url(cluster_name, org_name, project_name) / "config"
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            ret = await resp.json()
            assert isinstance(ret, list)
            for item in ret:
                sa = KubeServiceAccount._parse(item)
                if all_users or sa.user == self._config.username:
                    yield sa

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
            return KubeServiceAccount._parse(ret)


def _merge_group(
    kube_config: dict[str, Any], sa_config: dict[str, Any], name: str
) -> None:
    sa_group = sa_config[name]
    if name not in kube_config:
        kube_config[name] = sa_group
        return
    kube_group = kube_config[name]
    assert isinstance(kube_config, dict)
    tmp = {cl["name"]: cl for cl in sa_group}
    for pos in range(len(kube_group)):
        item = kube_group[pos]
        name = item["name"]
        if name in tmp:
            kube_group[pos] = tmp.pop(name)
    for item in tmp.values():
        kube_group.append(item)


def _merge_configs(kube_config: dict[str, Any], sa_config: dict[str, Any]) -> None:
    _merge_group(kube_config, sa_config, "clusters")
    _merge_group(kube_config, sa_config, "contexts")
    _merge_group(kube_config, sa_config, "users")
    kube_config["current-context"] = sa_config["current-context"]
    kube_config.setdefault("apiVersion", sa_config["apiVersion"])
    kube_config.setdefault("kind", sa_config["kind"])
