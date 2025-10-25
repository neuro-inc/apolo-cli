import asyncio
import base64
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Mapping, Optional

import aiohttp
import certifi
from yarl import URL

from ._client import Client
from ._config import _ConfigData, _load, _load_recovery_data, _load_user_config, _save
from ._core import DEFAULT_TIMEOUT
from ._errors import ConfigError
from ._login import (
    AuthNegotiator,
    AuthTokenClient,
    HeadlessNegotiator,
    _AuthToken,
    create_standalone_token,
    logout_from_browser,
)
from ._plugins import PluginManager
from ._rewrite import rewrite_module
from ._server_cfg import Project, _ServerConfig, get_server_config
from ._tracing import _make_trace_config
from ._utils import _ContextManager

if sys.version_info >= (3, 11):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points

DEFAULT_CONFIG_PATH = "~/.apolo"
OLD_DEFAULT_CONFIG_PATH = "~/.neuro"
CONFIG_ENV_NAME = "APOLO_CONFIG"
OLD_CONFIG_ENV_NAME = "NEUROMATION_CONFIG"
PASS_CONFIG_ENV_NAME = "APOLO_PASSED_CONFIG"
OLD_PASS_CONFIG_ENV_NAME = "NEURO_PASSED_CONFIG"
DEFAULT_API_URL = URL("https://staging.neu.ro/api/v1")


def _make_session(
    timeout: aiohttp.ClientTimeout, trace_configs: Optional[List[aiohttp.TraceConfig]]
) -> _ContextManager[aiohttp.ClientSession]:
    return _ContextManager[aiohttp.ClientSession](
        __make_session(timeout, trace_configs)
    )


async def __make_session(
    timeout: aiohttp.ClientTimeout, trace_configs: Optional[List[aiohttp.TraceConfig]]
) -> aiohttp.ClientSession:
    from . import __version__

    ssl_context = ssl.create_default_context(cadata=certifi.contents())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    return aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        trace_configs=trace_configs,
        headers={"User-Agent": f"ApoloCLI/{__version__} ({sys.platform})"},
    )


def _choose_path(explicit: Optional[Path]) -> Path:
    if explicit is not None:
        return explicit.expanduser()

    items = [
        os.environ.get(CONFIG_ENV_NAME, DEFAULT_CONFIG_PATH),
        os.environ.get(OLD_CONFIG_ENV_NAME, OLD_DEFAULT_CONFIG_PATH),
    ]
    paths = [Path(item).expanduser() for item in items]
    for path in paths:
        if (path / "db").exists():
            return path
    else:
        return paths[0]


@rewrite_module
class Factory:
    def __init__(
        self,
        path: Optional[Path] = None,
        trace_configs: Optional[List[aiohttp.TraceConfig]] = None,
        trace_id: Optional[str] = None,
        trace_sampled: Optional[bool] = None,
    ) -> None:
        self._path = _choose_path(path)
        self._trace_configs = [_make_trace_config()]
        if trace_configs:
            self._trace_configs += trace_configs
        self._trace_id = trace_id
        self._trace_sampled = trace_sampled
        self._plugin_manager = PluginManager()
        for entry_point in entry_points(group="apolo_api"):
            entry_point.load()(self._plugin_manager)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_config_present(self) -> bool:
        return (self._path / "db").exists()

    async def get(self, *, timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT) -> Client:
        if (
            not self.is_config_present
            and {PASS_CONFIG_ENV_NAME, OLD_PASS_CONFIG_ENV_NAME} & os.environ.keys()
        ):
            await self.login_with_passed_config(timeout=timeout)
        try:
            return await self._get(timeout=timeout)
        except ConfigError as initial_error:
            try:
                await self._try_recover_config(timeout)
            except asyncio.CancelledError:
                raise
            except Exception:
                raise initial_error
            return await self._get(timeout=timeout)

    async def _get(self, *, timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT) -> Client:
        session = await _make_session(timeout, self._trace_configs)
        try:
            client = Client._create(
                session,
                self._path,
                self._trace_id,
                self._trace_sampled,
                self._plugin_manager,
            )
            await client.config.check_server()
        except (asyncio.CancelledError, Exception):
            await session.close()
            raise
        else:
            return client

    async def _try_recover_config(
        self, timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT
    ) -> None:
        recovery_data = _load_recovery_data(self._path)
        async with _make_session(timeout, self._trace_configs) as session:
            config_unauthorized = await get_server_config(session, recovery_data.url)
            old_token = _AuthToken.create("", 0, recovery_data.refresh_token)
            async with AuthTokenClient(
                session,
                url=config_unauthorized.auth_config.token_url,
                client_id=config_unauthorized.auth_config.client_id,
            ) as token_client:
                fresh_token = await token_client.refresh(old_token)
            config_authorized = await get_server_config(
                session, recovery_data.url, token=fresh_token.token
            )
            config = self._gen_config(config_authorized, fresh_token, recovery_data.url)
        await self.logout()  # Drop old broken config
        self._save(config)

        client = await self.get(timeout=timeout)
        await client.config.switch_cluster(recovery_data.cluster_name)
        await client.config.switch_org(recovery_data.org_name)
        await client.close()

    async def login(
        self,
        show_browser_cb: Callable[[URL], Awaitable[None]],
        *,
        url: URL = DEFAULT_API_URL,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> None:
        config_file = self._path / "db"
        if config_file.exists():
            raise ConfigError(f"Config at {self._path} already exists. Please logout")
        async with _make_session(timeout, self._trace_configs) as session:
            config_unauthorized = await get_server_config(session, url)

            if config_unauthorized.clusters:
                config_authorized = config_unauthorized
                auth_token = create_standalone_token()
            else:
                negotiator = AuthNegotiator(
                    session, config_unauthorized.auth_config, show_browser_cb
                )
                auth_token = await negotiator.get_token()

                config_authorized = await get_server_config(
                    session, url, token=auth_token.token
                )
            config = self._gen_config(config_authorized, auth_token, url)
        self._save(config)

    async def login_headless(
        self,
        get_auth_code_cb: Callable[[URL], Awaitable[str]],
        *,
        url: URL = DEFAULT_API_URL,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> None:
        config_file = self._path / "db"
        if config_file.exists():
            raise ConfigError(f"Config at {self._path} already exists. Please logout")
        async with _make_session(timeout, self._trace_configs) as session:
            config_unauthorized = await get_server_config(session, url)
            negotiator = HeadlessNegotiator(
                session, config_unauthorized.auth_config, get_auth_code_cb
            )
            auth_token = await negotiator.get_token()

            config_authorized = await get_server_config(
                session, url, token=auth_token.token
            )
        config = self._gen_config(config_authorized, auth_token, url)
        self._save(config)

    async def login_with_token(
        self,
        token: str,
        *,
        url: URL = DEFAULT_API_URL,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> None:
        config_file = self._path / "db"
        if config_file.exists():
            raise ConfigError(f"Config at {self._path} already exists. Please logout")
        async with _make_session(timeout, self._trace_configs) as session:
            server_config = await get_server_config(session, url, token=token)
        config = self._gen_config(
            server_config, _AuthToken.create_non_expiring(token), url
        )
        self._save(config)

    async def login_with_passed_config(
        self,
        config_data: Optional[str] = None,
        *,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    ) -> None:
        if config_data is None:
            try:
                config_data = os.environ[PASS_CONFIG_ENV_NAME]
            except KeyError:
                try:
                    config_data = os.environ[OLD_PASS_CONFIG_ENV_NAME]
                except KeyError:
                    raise ConfigError(
                        f"Config env variable {PASS_CONFIG_ENV_NAME} " "is not present"
                    )
        try:
            data = json.loads(base64.b64decode(config_data).decode())
            token = data["token"]
            cluster = data["cluster"]
            url = URL(data["url"])
            org_name = data.get("org_name")
            project_name = data.get("project_name")
        except (ValueError, KeyError):
            raise ConfigError(f"Data in passed config is malformed: {config_data}")
        await self.login_with_token(token, url=url, timeout=timeout)
        client = await self.get(timeout=timeout)

        await client.config.switch_cluster(cluster)
        if org_name is not None:
            await client.config.switch_org(org_name)
        if project_name:
            await client.config.switch_project(project_name)
        await client.close()

    def _gen_config(
        self, server_config: _ServerConfig, token: _AuthToken, url: URL
    ) -> _ConfigData:
        from . import __version__

        if not server_config.clusters:
            raise ConfigError("No clusters configured")
        cluster_name = next(iter(server_config.clusters))
        cluster = server_config.clusters[cluster_name]
        if cluster.orgs:
            org_name = cluster.orgs[0]
        else:
            org_name = "default-org"
        project_name = self._get_first_project(
            server_config.projects, cluster_name, org_name
        )
        config = _ConfigData(
            auth_config=server_config.auth_config,
            auth_token=token,
            url=url,
            admin_url=server_config.admin_url,
            version=__version__,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
            clusters=server_config.clusters,
            projects=server_config.projects,
        )
        return config

    def _get_first_project(
        self,
        projects: Mapping[Project.Key, Project],
        cluster_name: str,
        org_name: Optional[str],
    ) -> Optional[str]:
        cluster_org_projects = []
        for project in projects.values():
            if project.cluster_name == cluster_name and project.org_name == org_name:
                cluster_org_projects.append(project.name)
        return sorted(cluster_org_projects)[0] if cluster_org_projects else None

    async def logout(
        self,
        show_browser_cb: Optional[Callable[[URL], Awaitable[None]]] = None,
    ) -> None:
        if show_browser_cb is not None:
            try:
                old_config = _load(self._path)
            except ConfigError:
                pass  # Do not try to logout from auth0 if config is broken
            else:
                await logout_from_browser(old_config.auth_config, show_browser_cb)

        files = ["db", "db-wal", "db-shm"]
        for name in files:
            f = self._path / name
            if f.exists():
                f.unlink()
        if self._path.is_file():
            # Old-styled single file config from 2019
            self._path.unlink()
        else:
            try:
                self._path.rmdir()
            except OSError:
                # Directory Not Empty or Not A Directory
                pass

    async def load_user_config(self) -> Mapping[str, Any]:
        return _load_user_config(self._plugin_manager, self._path)

    def _save(self, config: _ConfigData) -> None:
        _save(config, self._path, False)
