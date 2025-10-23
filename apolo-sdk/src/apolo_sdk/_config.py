import base64
import contextlib
import json
import logging
import numbers
import os
import re
import sqlite3
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Optional, Union

import toml
from yarl import URL

from ._core import _Core
from ._errors import ConfigError
from ._login import AuthTokenClient, _AuthConfig, _AuthToken
from ._plugins import ConfigScope, PluginManager, _ParamType
from ._rewrite import rewrite_module
from ._server_cfg import (
    AMDGPU,
    AMDGPUPreset,
    AppsConfig,
    Cluster,
    IntelGPU,
    IntelGPUPreset,
    NvidiaGPU,
    NvidiaGPUPreset,
    Preset,
    Project,
    ResourcePool,
    TPUPreset,
    TPUResource,
    _ServerConfig,
    get_server_config,
)
from ._utils import RELOGIN_TEXT, NoPublicConstructor, find_project_root, flat

WIN32 = sys.platform == "win32"
CMD_RE = re.compile("[A-Za-z][A-Za-z0-9-]*")

MALFORMED_CONFIG_MSG = "Malformed config. " + RELOGIN_TEXT


SCHEMA = {
    "main": flat(
        """
        CREATE TABLE main (auth_config TEXT,
                           token TEXT,
                           expiration_time REAL,
                           refresh_token TEXT,
                           url TEXT,
                           admin_url TEXT,
                           version TEXT,
                           project_name TEXT,
                           cluster_name TEXT,
                           org_name TEXT,
                           clusters TEXT,
                           projects TEXT,
                           timestamp REAL)"""
    )
}


logger = logging.getLogger(__package__)


@dataclass(frozen=True)
class _ConfigData:
    auth_config: _AuthConfig
    auth_token: _AuthToken
    url: URL
    admin_url: Optional[URL]
    version: str
    project_name: Optional[str]
    cluster_name: str
    org_name: str
    clusters: Mapping[str, Cluster]
    projects: Mapping[Project.Key, Project]


@dataclass(frozen=True)
class _ConfigRecoveryData:
    url: URL
    cluster_name: str
    org_name: str
    refresh_token: str


@rewrite_module
class Config(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, path: Path, plugin_manager: PluginManager) -> None:
        self._core = core
        self._path = path
        self._plugin_manager = plugin_manager
        self.__config_data: Optional[_ConfigData] = None

    def _load(self) -> _ConfigData:
        ret = self.__config_data = _load(self._path)
        return ret

    @property
    def _config_data(self) -> _ConfigData:
        ret = self.__config_data
        if ret is None:
            return self._load()
        else:
            return ret

    @property
    def path(self) -> Path:
        return self._path

    @property
    def username(self) -> str:
        return self._config_data.auth_token.username

    @property
    def resource_pools(self) -> Mapping[str, ResourcePool]:
        return MappingProxyType(self._cluster.resource_pools)

    @property
    def presets(self) -> Mapping[str, Preset]:
        return MappingProxyType(self._cluster.presets)

    @property
    def clusters(self) -> Mapping[str, Cluster]:
        return MappingProxyType(self._config_data.clusters)

    @property
    def projects(self) -> Mapping[Project.Key, Project]:
        return MappingProxyType(self._config_data.projects)

    @property
    def available_orgs(self) -> Sequence[str]:
        ret = set()
        for cluster in self.clusters.values():
            ret |= set(cluster.orgs)
        return tuple(sorted(ret))

    @property
    def cluster_name(self) -> str:
        if not self._config_data.clusters:
            raise RuntimeError("There are no clusters available. " + RELOGIN_TEXT)
        name = self._get_user_cluster_name()
        if name is None:
            name = self._config_data.cluster_name
        assert name
        return name

    def _get_user_cluster_name(self) -> Optional[str]:
        config = self._get_user_config()
        section = config.get("job")
        if section is not None:
            return section.get("cluster-name")
        return None

    @property
    def cluster_orgs(self) -> list[str]:
        return self.clusters[self.cluster_name].orgs

    @property
    def org_name(self) -> str:
        name = self._get_user_org_name()
        if name is None:
            name = self._config_data.org_name
        if not name:
            raise RuntimeError("org_name is required but not configured")
        return name

    def _get_user_org_name(self) -> Optional[str]:
        config = self._get_user_config()
        section = config.get("job")
        if section is not None:
            return section.get("org-name")
        return None

    @property
    def project_name(self) -> Optional[str]:
        name = self._get_user_project_name()
        if name is None:
            name = self._config_data.project_name
        return name

    @property
    def project_name_or_raise(self) -> str:
        name = self.project_name
        if not name:
            raise RuntimeError(
                "The current project is not selected. "
                "Please create one with 'apolo admin add-project', or "
                "switch to the existing one with 'apolo config switch-project'."
            )
        return name

    def _get_user_project_name(self) -> Optional[str]:
        config = self._get_user_config()
        section = config.get("job")
        if section is not None:
            return section.get("project-name")
        return None

    @property
    def cluster_org_projects(self) -> list[Project]:
        return self._get_cluster_org_projects(self.cluster_name, self.org_name)

    def _get_cluster_org_projects(
        self, cluster_name: str, org_name: Optional[str]
    ) -> list[Project]:
        projects = []
        for project in self.projects.values():
            if project.cluster_name == cluster_name and project.org_name == org_name:
                projects.append(project)
        return projects

    @property
    def _cluster(self) -> Cluster:
        return self.get_cluster(self.cluster_name)

    def get_cluster(self, cluster_name: str) -> Cluster:
        try:
            return self._config_data.clusters[cluster_name]
        except KeyError:
            if self._get_user_cluster_name() is None:
                tip = RELOGIN_TEXT
            else:
                tip = "Please edit local user config file or " + RELOGIN_TEXT
            raise RuntimeError(
                f"Cluster {cluster_name} doesn't exist in "
                f"a list of available clusters "
                f"{list(self._config_data.clusters)}. {tip}"
            ) from None

    async def _fetch_config(self) -> _ServerConfig:
        token = await self.token()
        return await get_server_config(self._core._session, self.api_url, token)

    async def check_server(self) -> None:
        from . import __version__

        if self._config_data.version != __version__:
            config_authorized = await self._fetch_config()
            if (
                config_authorized.clusters != self.clusters
                or config_authorized.auth_config != self._config_data.auth_config
            ):
                raise ConfigError("Apolo Platform CLI was updated. " + RELOGIN_TEXT)
            self.__config_data = replace(self._config_data, version=__version__)
            _save(self._config_data, self._path)

    async def fetch(self) -> None:
        server_config = await self._fetch_config()
        if self.cluster_name not in server_config.clusters:
            # Raise exception here?
            # if yes there is not way to switch cluster without relogin
            raise RuntimeError(
                f"Cluster {self.cluster_name} doesn't exist in "
                f"a list of available clusters "
                f"{list(server_config.clusters)}. " + RELOGIN_TEXT
            )
        self.__config_data = replace(
            self._config_data,
            clusters=server_config.clusters,
            projects=server_config.projects,
        )
        _save(self._config_data, self._path)

    async def switch_project(self, name: str) -> None:
        if self._get_user_project_name() is not None:
            raise RuntimeError(
                "Cannot switch the project. Please edit the '.apolo.toml' file."
            )
        cluster_name = self.cluster_name
        org_name = self.org_name
        project_key = Project.Key(
            cluster_name=cluster_name, org_name=org_name, project_name=name
        )
        if project_key not in self.projects:
            projects = [p.name for p in self.cluster_org_projects]
            raise RuntimeError(
                f"Project {name} doesn't exist in a list of available "
                f"tenant projects {projects}. "
            )
        self.__config_data = replace(self._config_data, project_name=name)
        _save(self._config_data, self._path)

    async def switch_cluster(self, name: str) -> None:
        if self._get_user_cluster_name() is not None:
            raise RuntimeError(
                "Cannot switch the project cluster. "
                "Please edit the '.apolo.toml' file."
            )
        if name not in self.clusters:
            raise RuntimeError(
                f"Cluster {name} doesn't exist in "
                f"a list of available clusters {list(self.clusters)}. "
            )
        cluster_orgs = self.clusters[name].orgs
        org_name = self.org_name
        if org_name not in cluster_orgs:
            # Cannot keep using same org
            # Select the first available in selected cluster
            org_name = sorted(cluster_orgs)[0]
        self.__config_data = replace(
            self._config_data,
            cluster_name=name,
            org_name=org_name,
            project_name=self._get_current_project_for_cluster_org(
                cluster_name=name, org_name=org_name
            ),
        )
        _save(self._config_data, self._path)

    async def switch_org(self, name: str) -> None:
        if self._get_user_org_name() is not None:
            raise RuntimeError(
                "Cannot switch the project org. Please edit the '.apolo.toml' file."
            )
        if name not in self._cluster.orgs:
            # select first available cluster for new org_name
            for cluster in self.clusters.values():
                if cluster.orgs and name in cluster.orgs:
                    await self.switch_cluster(cluster.name)
                    break
            else:
                raise RuntimeError(f"Cannot find available cluster for org {name}. ")
        self.__config_data = replace(
            self._config_data,
            org_name=name,
            project_name=self._get_current_project_for_cluster_org(
                cluster_name=self.cluster_name, org_name=name
            ),
        )
        _save(self._config_data, self._path)

    def _get_current_project_for_cluster_org(
        self, cluster_name: str, org_name: str
    ) -> Optional[str]:
        project_name = self.project_name
        if project_name:
            project_key = Project.Key(
                cluster_name=cluster_name, org_name=org_name, project_name=project_name
            )
        else:
            project_key = None
        if not project_key or project_key not in self.projects:
            # Use first in alphabetical order if any
            cluster_org_projects = self._get_cluster_org_projects(
                cluster_name, org_name
            )
            if cluster_org_projects:
                cluster_org_projects = sorted(
                    cluster_org_projects, key=lambda it: it.name
                )
                project_name = cluster_org_projects[0].name
            else:
                project_name = None
        return project_name

    @property
    def api_url(self) -> URL:
        return self._config_data.url

    @property
    def admin_url(self) -> Optional[URL]:
        return self._config_data.admin_url

    @property
    def service_accounts_url(self) -> URL:
        # TODO: use URL returned from server when available
        return self._config_data.url / "service_accounts"

    @property
    def monitoring_url(self) -> URL:
        return self._cluster.monitoring_url

    @property
    def storage_url(self) -> URL:
        return self._cluster.storage_url

    @property
    def registry_url(self) -> URL:
        return self._cluster.registry_url

    @property
    def secrets_url(self) -> URL:
        return self._cluster.secrets_url

    @property
    def disk_api_url(self) -> URL:
        return self._cluster.disks_url

    @property
    def bucket_api_url(self) -> URL:
        return self._cluster.buckets_url

    async def token(self) -> str:
        token = self._config_data.auth_token
        if not token.is_expired():
            return token.token
        async with AuthTokenClient(
            self._core._session,
            url=self._config_data.auth_config.token_url,
            client_id=self._config_data.auth_config.client_id,
        ) as token_client:
            new_token = await token_client.refresh(token)
            self.__config_data = replace(self._config_data, auth_token=new_token)
            with self._open_db() as db:
                _save_auth_token(db, new_token)
            return new_token.token

    async def _api_auth(self) -> str:
        token = await self.token()
        return f"Bearer {token}"

    async def _docker_auth(self) -> dict[str, str]:
        token = await self.token()
        return {"username": "token", "password": token}

    async def _registry_auth(self) -> str:
        token = await self.token()
        return "Basic " + base64.b64encode(
            f"{self.username}:{token}".encode("ascii")
        ).decode("ascii")

    async def get_user_config(self) -> Mapping[str, Any]:
        return _load_user_config(self._plugin_manager, self._path)

    def _get_user_config(self) -> Mapping[str, Any]:
        return _load_user_config(self._plugin_manager, self._path)

    @contextlib.contextmanager
    def _open_db(self, suppress_errors: bool = True) -> Iterator[sqlite3.Connection]:
        with _open_db_rw(self._path, suppress_errors) as db:
            yield db


def _load_user_config(plugin_manager: PluginManager, path: Path) -> Mapping[str, Any]:
    # TODO: search in several locations (HOME+curdir),
    # merge found configs
    filename = path / "user.toml"
    if not filename.exists():
        # Empty global configuration
        config: Mapping[str, Any] = {}
    elif not filename.is_file():
        raise ConfigError(f"User config {filename} should be a regular file")
    else:
        config = _load_file(
            plugin_manager, filename, allow_cluster_name=False, allow_org_name=False
        )
    try:
        project_root = find_project_root()
    except ConfigError:
        return config
    else:
        filename = project_root / ".apolo.toml"
        if not filename.exists():
            filename2 = project_root / ".neuro.toml"
            if filename2.exists():
                filename = filename2
        local_config = _load_file(
            plugin_manager, filename, allow_cluster_name=True, allow_org_name=True
        )
        return _merge_user_configs(config, local_config)


@contextlib.contextmanager
def _open_db_rw(
    path: Path, suppress_errors: bool = True
) -> Iterator[sqlite3.Connection]:
    path.mkdir(0o700, parents=True, exist_ok=True)  # atomically set proper bits
    path.chmod(0o700)  # fix security if config folder already exists

    config_file = path / "db"
    conn = sqlite3.connect(str(config_file))
    try:
        # forbid access to other users
        os.chmod(config_file, 0o600)

        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
    except sqlite3.DatabaseError as exc:
        conn.close()
        if not suppress_errors:
            raise
        msg = "Cannot send the usage statistics: %s"
        if str(exc) != "database is locked":
            logger.warning(msg, repr(exc))
        else:
            logger.debug(msg, repr(exc))
    finally:
        conn.close()


@contextlib.contextmanager
def _open_db_ro(
    path: Path, *, skip_schema_check: bool = False
) -> Iterator[sqlite3.Connection]:
    config_file = path / "db"
    if not path.exists():
        raise ConfigError(f"Config at {path} does not exists. Please login.")
    if not path.is_dir():
        raise ConfigError(f"Config at {path} is not a directory. " + RELOGIN_TEXT)
    if not config_file.is_file():
        raise ConfigError(
            f"Config {config_file} is not a regular file. " + RELOGIN_TEXT
        )

    if not WIN32:
        stat_dir = path.stat()
        if stat_dir.st_mode & 0o777 != 0o700:
            raise ConfigError(
                f"Config {path} has compromised permission bits, "
                f"run 'chmod 700 {path}' first"
            )
        stat_file = config_file.stat()
        if stat_file.st_mode & 0o777 != 0o600:
            raise ConfigError(
                f"Config at {config_file} has compromised permission bits, "
                f"run 'chmod 600 {config_file}' first"
            )

    conn = sqlite3.connect(str(config_file))
    try:
        # forbid access for other users
        os.chmod(config_file, 0o600)

        if not skip_schema_check:
            _check_db(conn)
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


def _load(path: Path) -> _ConfigData:
    try:
        with _open_db_ro(path) as db:
            cur = db.cursor()
            # only one row is always present normally
            cur.execute(
                """
                SELECT auth_config, token, expiration_time, refresh_token,
                       url, admin_url, version, project_name, cluster_name,
                       org_name, clusters, projects
                FROM main ORDER BY timestamp DESC LIMIT 1"""
            )
            payload = cur.fetchone()

        api_url = URL(payload["url"])
        if not payload["admin_url"]:
            admin_url = None
        else:
            admin_url = URL(payload["admin_url"])
        auth_config = _deserialize_auth_config(payload)
        clusters = _deserialize_clusters(payload)
        projects = _deserialize_projects(payload)
        version = payload["version"]
        project_name = payload["project_name"]
        cluster_name = payload["cluster_name"]
        org_name = payload["org_name"]

        auth_token = _AuthToken(
            payload["token"], payload["expiration_time"], payload["refresh_token"]
        )

        return _ConfigData(
            auth_config=auth_config,
            auth_token=auth_token,
            url=api_url,
            admin_url=admin_url,
            version=version,
            project_name=project_name,
            cluster_name=cluster_name,
            org_name=org_name,
            clusters=clusters,
            projects=projects,
        )
    except (AttributeError, KeyError, TypeError, ValueError, sqlite3.DatabaseError):
        raise ConfigError(MALFORMED_CONFIG_MSG)


def _load_recovery_data(path: Path) -> _ConfigRecoveryData:
    try:
        with _open_db_ro(path, skip_schema_check=True) as db:
            cur = db.cursor()
            # only one row is always present normally
            try:
                cur.execute(
                    """
                    SELECT refresh_token, url, cluster_name, org_name
                    FROM main ORDER BY timestamp DESC LIMIT 1"""
                )
                payload = cur.fetchone()
            except sqlite3.OperationalError:
                # Maybe this config was created before org_name was added?
                cur.execute(
                    """
                    SELECT refresh_token, url, cluster_name
                    FROM main ORDER BY timestamp DESC LIMIT 1"""
                )
                payload = cur.fetchone()

        org_name = payload.get("org_name") or "default-org"
        return _ConfigRecoveryData(
            url=URL(payload["url"]),
            cluster_name=payload["cluster_name"],
            refresh_token=payload["refresh_token"],
            org_name=org_name,
        )
    except (AttributeError, KeyError, TypeError, ValueError, sqlite3.DatabaseError):
        raise ConfigError(MALFORMED_CONFIG_MSG)


def _deserialize_auth_config(payload: dict[str, Any]) -> _AuthConfig:
    auth_config = json.loads(payload["auth_config"])
    success_redirect_url = auth_config.get("success_redirect_url")
    if success_redirect_url:
        success_redirect_url = URL(success_redirect_url)
    return _AuthConfig(
        auth_url=URL(auth_config["auth_url"]),
        token_url=URL(auth_config["token_url"]),
        logout_url=URL(auth_config["logout_url"]),
        client_id=auth_config["client_id"],
        audience=auth_config["audience"],
        headless_callback_url=URL(auth_config["headless_callback_url"]),
        success_redirect_url=success_redirect_url,
        callback_urls=tuple(URL(u) for u in auth_config.get("callback_urls", [])),
    )


def _deserialize_projects(payload: dict[str, Any]) -> dict[Project.Key, Project]:
    projects = json.loads(payload["projects"])
    ret: dict[Project.Key, Project] = {}
    for project_config in projects:
        project = Project(
            name=project_config["name"],
            cluster_name=project_config["cluster_name"],
            org_name=project_config["org_name"],
            role=project_config["role"],
        )
        ret[project.key] = project
    return ret


def _deserialize_clusters(payload: dict[str, Any]) -> dict[str, Cluster]:
    clusters = json.loads(payload["clusters"])
    ret: dict[str, Cluster] = {}
    for cluster_config in clusters:
        cluster = Cluster(
            name=cluster_config["name"],
            orgs=cluster_config.get("orgs", ["test-org"]),
            registry_url=URL(cluster_config["registry_url"]),
            storage_url=URL(cluster_config["storage_url"]),
            users_url=URL(cluster_config["users_url"]),
            monitoring_url=URL(cluster_config["monitoring_url"]),
            secrets_url=URL(cluster_config["secrets_url"]),
            disks_url=URL(cluster_config["disks_url"]),
            buckets_url=URL(cluster_config["buckets_url"]),
            resource_pools=dict(
                _deserialize_resource_pool(data)
                for data in cluster_config.get("resource_pools", [])
            ),
            presets=dict(
                _deserialize_resource_preset(data)
                for data in cluster_config.get("presets", [])
            ),
            apps=AppsConfig(**cluster_config.get("apps", {})),
        )
        ret[cluster.name] = cluster
    return ret


def _deserialize_resource_pool(payload: dict[str, Any]) -> tuple[str, ResourcePool]:
    resource_pool = ResourcePool(
        min_size=payload["min_size"],
        max_size=payload["max_size"],
        cpu=payload["cpu"],
        memory=payload["memory"],
        disk_size=payload["disk_size"],
        nvidia_gpu=_deserialize_nvidia_gpu(payload),
        amd_gpu=_deserialize_amd_gpu(payload),
        intel_gpu=_deserialize_intel_gpu(payload),
        tpu=_deserialize_tpu(payload.get("tpu")),
        is_preemptible=payload.get("is_preemptible", False),
    )
    return (payload["name"], resource_pool)


def _deserialize_nvidia_gpu(payload: dict[str, Any]) -> Optional[NvidiaGPU]:
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


def _deserialize_amd_gpu(payload: dict[str, Any]) -> Optional[AMDGPU]:
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


def _deserialize_intel_gpu(payload: dict[str, Any]) -> Optional[IntelGPU]:
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


def _deserialize_tpu(payload: Optional[dict[str, Any]]) -> Optional[TPUResource]:
    if not payload:
        return None
    return TPUResource(
        types=payload["types"],
        software_versions=payload["software_versions"],
        ipv4_cidr_block=payload["ipv4_cidr_block"],
    )


def _deserialize_resource_preset(payload: dict[str, Any]) -> tuple[str, Preset]:
    return (
        payload["name"],
        Preset(
            credits_per_hour=Decimal(payload["credits_per_hour"]),
            cpu=payload["cpu"],
            memory=payload["memory"],
            nvidia_gpu=_deserialize_nvidia_gpu_preset(payload),
            amd_gpu=_deserialize_amd_gpu_preset(payload),
            intel_gpu=_deserialize_intel_gpu_preset(payload),
            tpu=_deserialize_tpu_preset(payload.get("tpu")),
            scheduler_enabled=payload.get("scheduler_enabled", False),
            preemptible_node=payload.get("preemptible_node", False),
            resource_pool_names=tuple(payload.get("resource_pool_names", ())),
            available_resource_pool_names=tuple(
                payload.get("available_resource_pool_names", ())
            ),
        ),
    )


def _deserialize_nvidia_gpu_preset(
    payload: dict[str, Any],
) -> Optional[NvidiaGPUPreset]:
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


def _deserialize_amd_gpu_preset(payload: dict[str, Any]) -> Optional[AMDGPUPreset]:
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


def _deserialize_intel_gpu_preset(payload: dict[str, Any]) -> Optional[IntelGPUPreset]:
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


def _deserialize_tpu_preset(payload: Optional[dict[str, Any]]) -> Optional[TPUPreset]:
    if not payload:
        return None
    return TPUPreset(
        type=payload["type"],
        software_version=payload["software_version"],
    )


def _deserialize_auth_token(payload: dict[str, Any]) -> _AuthToken:
    auth_payload = payload["auth_token"]
    return _AuthToken(
        token=auth_payload["token"],
        expiration_time=auth_payload["expiration_time"],
        refresh_token=auth_payload["refresh_token"],
    )


def _save_auth_token(db: sqlite3.Connection, token: _AuthToken) -> None:
    db.execute(
        "UPDATE main SET token=?, expiration_time=?, refresh_token=?",
        (token.token, token.expiration_time, token.refresh_token),
    )
    with contextlib.suppress(sqlite3.OperationalError):
        db.commit()


def _save(config: _ConfigData, path: Path, suppress_errors: bool = True) -> None:
    # The wierd method signature is required for communicating with existing
    # Factory._save()
    try:
        url = str(config.url)
        if not config.admin_url:
            admin_url = None
        else:
            admin_url = str(config.admin_url)
        auth_config = _serialize_auth_config(config.auth_config)
        clusters = _serialize_clusters(config.clusters)
        projects = _serialize_projects(config.projects)
        version = config.version
        project_name = config.project_name
        cluster_name = config.cluster_name
        org_name = config.org_name
        token = config.auth_token
    except (AttributeError, KeyError, TypeError, ValueError):
        raise ConfigError(MALFORMED_CONFIG_MSG)

    with _open_db_rw(path, suppress_errors) as db:
        _init_db_maybe(db)

        cur = db.cursor()
        cur.execute("DELETE FROM main")
        cur.execute(
            """
            INSERT INTO main
            (auth_config, token, expiration_time, refresh_token, url, admin_url,
             version, project_name, cluster_name, org_name, clusters, projects,
             timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                auth_config,
                token.token,
                token.expiration_time,
                token.refresh_token,
                url,
                admin_url,
                version,
                project_name,
                cluster_name,
                org_name,
                clusters,
                projects,
                time.time(),
            ),
        )
        db.commit()


def _serialize_auth_config(auth_config: _AuthConfig) -> str:
    success_redirect_url = None
    if auth_config.success_redirect_url:
        success_redirect_url = str(auth_config.success_redirect_url)
    return json.dumps(
        {
            "auth_url": str(auth_config.auth_url),
            "token_url": str(auth_config.token_url),
            "logout_url": str(auth_config.logout_url),
            "client_id": auth_config.client_id,
            "audience": auth_config.audience,
            "headless_callback_url": str(auth_config.headless_callback_url),
            "success_redirect_url": success_redirect_url,
            "callback_urls": [str(u) for u in auth_config.callback_urls],
        }
    )


def _serialize_projects(projects: Mapping[Project.Key, Project]) -> str:
    ret: list[dict[str, Any]] = []
    for project in projects.values():
        project_config = {
            "name": project.name,
            "cluster_name": project.cluster_name,
            "org_name": project.org_name,
            "role": project.role,
        }
        ret.append(project_config)
    return json.dumps(ret)


def _serialize_clusters(clusters: Mapping[str, Cluster]) -> str:
    ret: list[dict[str, Any]] = []
    for cluster in clusters.values():
        cluster_config = {
            "name": cluster.name,
            "orgs": cluster.orgs,
            "registry_url": str(cluster.registry_url),
            "storage_url": str(cluster.storage_url),
            "users_url": str(cluster.users_url),
            "monitoring_url": str(cluster.monitoring_url),
            "secrets_url": str(cluster.secrets_url),
            "disks_url": str(cluster.disks_url),
            "buckets_url": str(cluster.buckets_url),
            "resource_pools": [
                _serialize_resource_pool(name, resource_pool)
                for name, resource_pool in cluster.resource_pools.items()
            ],
            "presets": [
                _serialize_resource_preset(name, preset)
                for name, preset in cluster.presets.items()
            ],
            "apps": asdict(cluster.apps),
        }
        ret.append(cluster_config)
    return json.dumps(ret)


def _serialize_resource_pool(name: str, resource_pool: ResourcePool) -> dict[str, Any]:
    result = {
        "name": name,
        "min_size": resource_pool.min_size,
        "max_size": resource_pool.max_size,
        "cpu": resource_pool.cpu,
        "memory": resource_pool.memory,
        "disk_size": resource_pool.disk_size,
        "is_preemptible": resource_pool.is_preemptible,
    }
    if resource_pool.nvidia_gpu:
        result["nvidia_gpu"] = {
            "count": resource_pool.nvidia_gpu.count,
            "model": resource_pool.nvidia_gpu.model,
            "memory": resource_pool.nvidia_gpu.memory,
        }
    if resource_pool.amd_gpu:
        result["amd_gpu"] = {
            "count": resource_pool.amd_gpu.count,
            "model": resource_pool.amd_gpu.model,
            "memory": resource_pool.amd_gpu.memory,
        }
    if resource_pool.intel_gpu:
        result["intel_gpu"] = {
            "count": resource_pool.intel_gpu.count,
            "model": resource_pool.intel_gpu.model,
            "memory": resource_pool.intel_gpu.memory,
        }
    if resource_pool.tpu:
        result["tpu"] = {
            "types": resource_pool.tpu.types,
            "software_versions": resource_pool.tpu.software_versions,
            "ipv4_cidr_block": resource_pool.tpu.ipv4_cidr_block,
        }
    return result


def _serialize_resource_preset(name: str, preset: Preset) -> dict[str, Any]:
    result = {
        "name": name,
        "credits_per_hour": str(preset.credits_per_hour),
        "cpu": preset.cpu,
        "memory": preset.memory,
        "scheduler_enabled": preset.scheduler_enabled,
        "preemptible_node": preset.preemptible_node,
        "resource_pool_names": preset.resource_pool_names,
        "available_resource_pool_names": preset.available_resource_pool_names,
    }
    if preset.nvidia_gpu:
        result["nvidia_gpu"] = {
            "count": preset.nvidia_gpu.count,
            "model": preset.nvidia_gpu.model,
            "memory": preset.nvidia_gpu.memory,
        }
    if preset.amd_gpu:
        result["amd_gpu"] = {
            "count": preset.amd_gpu.count,
            "model": preset.amd_gpu.model,
            "memory": preset.amd_gpu.memory,
        }
    if preset.intel_gpu:
        result["intel_gpu"] = {
            "count": preset.intel_gpu.count,
            "model": preset.intel_gpu.model,
            "memory": preset.intel_gpu.memory,
        }
    if preset.tpu:
        result["tpu"] = {
            "type": preset.tpu.type,
            "software_version": preset.tpu.software_version,
        }
    return result


def _merge_user_configs(
    older: Mapping[str, Any], newer: Mapping[str, Any]
) -> Mapping[str, Any]:
    ret: dict[str, Any] = {}
    for key, val in older.items():
        if key not in newer:
            # keep older key/values
            ret[key] = val
        else:
            # key is present in both newer and older
            new_val = newer[key]
            if isinstance(new_val, Mapping) and isinstance(val, Mapping):
                # merge nested dictionaries
                ret[key] = _merge_user_configs(val, new_val)
            else:
                # for non-dicts newer overrides older
                ret[key] = new_val
    for key in newer.keys() - older.keys():
        # Add keys/values from newer that absent in older
        ret[key] = newer[key]
    return ret


def _check_sections(
    config: Mapping[str, Any],
    valid_names: set[str],
    filename: Union[str, "os.PathLike[str]"],
) -> None:
    extra_sections = config.keys() - valid_names
    if extra_sections:
        raise ConfigError(
            f"{filename}: unsupported config sections: {extra_sections!r}"
        )
    for name in valid_names:
        section = config.get(name, {})
        if not isinstance(section, dict):
            raise ConfigError(
                f"{filename}: {name!r} should be a section, got {section!r}"
            )


def _check_item(
    val: Any,
    validator: Any,
    full_name: str,
    filename: Union[str, "os.PathLike[str]"],
) -> None:
    if isinstance(validator, tuple):
        container_type, item_type = validator
        if not isinstance(val, container_type):
            raise ConfigError(
                f"{filename}: invalid type for {full_name}, "
                f"{container_type.__name__} is expected"
            )
        for num, i in enumerate(val):
            _check_item(i, item_type, f"{full_name}[{num}]", filename)
    else:
        assert isinstance(validator, type) and issubclass(
            validator, (bool, numbers.Real, numbers.Integral, str)
        )
        # validator for integer types should be numbers.Real or numbers.Integral,
        # not int or float
        if not isinstance(val, validator):
            raise ConfigError(
                f"{filename}: invalid type for {full_name}, "
                f"{validator.__name__} is expected"
            )


def _check_section(
    config: Mapping[str, Any],
    section: str,
    params: Mapping[str, _ParamType],
    filename: Union[str, "os.PathLike[str]"],
) -> None:
    sec = config.get(section)
    if sec is None:
        return
    diff = sec.keys() - params.keys()
    if diff:
        diff_str = ", ".join(f"{section}.{name}" for name in sorted(diff))
        raise ConfigError(f"{filename}: unknown parameters {diff_str}")
    for name, validator in params.items():
        val = sec.get(name)
        if val is None:
            continue
        _check_item(val, validator, f"{section}.{name}", filename)


def _validate_user_config(
    plugin_manager: PluginManager,
    config: Mapping[str, Any],
    filename: Union[str, "os.PathLike[str]"],
    allow_cluster_name: bool = False,
    allow_org_name: bool = False,
) -> None:
    # This was a hard decision.
    # Config structure should be validated to generate meaningful error messages.
    #
    # API should do it but API don't use user config itself, the config is entirely
    # for CLI needs.
    #
    # Since currently CLI is the only API client that reads user config data, API
    # validates it.
    if not allow_cluster_name:
        if "cluster-name" in config.get("job", {}):
            raise ConfigError(
                f"{filename}: cluster name is not allowed in global user "
                f"config file, use 'apolo config switch-cluster' for "
                f"changing the default cluster name"
            )
    if not allow_org_name:
        if "org-name" in config.get("job", {}):
            raise ConfigError(
                f"{filename}: org name is not allowed in global user "
                f"config file, use 'apolo config switch-org' for "
                f"changing the default org name"
            )

    config_spec = plugin_manager.config._get_spec(
        ConfigScope.GLOBAL if not allow_cluster_name else ConfigScope.ALL
    )

    # Alias section uses different validation
    _check_sections(config, set(config_spec.keys()) | {"alias"}, filename)
    for section_name, section_validator in config_spec.items():
        _check_section(config, section_name, section_validator, filename)
    aliases = config.get("alias", {})
    for key, value in aliases.items():
        # check keys and values
        if not CMD_RE.fullmatch(key):
            raise ConfigError(f"{filename}: invalid alias name {key}")
        if not isinstance(value, dict):
            raise ConfigError(
                f"{filename}: invalid alias command type {type(value)}, "
                "run 'apolo help aliases' for getting info about specifying "
                "aliases in config files"
            )
        _validate_alias(key, value, filename)


def _validate_alias(
    key: str, value: dict[str, str], filename: Union[str, "os.PathLike[str]"]
) -> None:
    # TODO: add validation for both internal and external aliases
    pass


def _load_file(
    plugin_manager: PluginManager,
    filename: Path,
    *,
    allow_cluster_name: bool,
    allow_org_name: bool,
) -> Mapping[str, Any]:
    try:
        config = toml.load(filename)
    except ValueError as exc:
        raise ConfigError(f"{filename}: {exc}")
    _validate_user_config(
        plugin_manager,
        config,
        filename,
        allow_cluster_name=allow_cluster_name,
        allow_org_name=allow_org_name,
    )
    return config


def _load_schema(db: sqlite3.Connection) -> dict[str, str]:
    cur = db.cursor()
    schema = {}
    cur.execute("SELECT type, name, sql from sqlite_master")
    for type, name, sql in cur:
        if type not in ("table", "index"):
            continue
        if name.startswith("sqlite"):
            # internal object
            continue
        schema[name] = sql
    return schema


def _check_db(db: sqlite3.Connection) -> None:
    schema = _load_schema(db)
    for name, sql in SCHEMA.items():
        if name not in schema:
            raise ConfigError(MALFORMED_CONFIG_MSG)
        if sql != schema[name]:
            raise ConfigError(MALFORMED_CONFIG_MSG)


def _init_db_maybe(db: sqlite3.Connection) -> None:
    # create schema for empty database if needed
    schema = _load_schema(db)
    cur = db.cursor()
    for name, sql in SCHEMA.items():
        if name not in schema:
            cur.execute(sql)
