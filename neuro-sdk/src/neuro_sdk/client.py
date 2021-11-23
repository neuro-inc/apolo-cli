from pathlib import Path
from types import TracebackType
from typing import Mapping, Optional, Type

import aiohttp

from neuro_sdk.service_accounts import ServiceAccounts

from ._version_utils import VersionChecker
from .admin import _Admin
from .buckets import Buckets
from .config import Config
from .core import _Core
from .disks import Disks
from .images import Images
from .jobs import Jobs
from .parser import Parser
from .plugins import PluginManager
from .secrets import Secrets
from .server_cfg import Preset
from .storage import Storage
from .users import Users
from .utils import NoPublicConstructor


class Client(metaclass=NoPublicConstructor):
    def __init__(
        self,
        session: aiohttp.ClientSession,
        path: Path,
        trace_id: Optional[str],
        trace_sampled: Optional[bool],
        plugin_manager: PluginManager,
    ) -> None:
        self._closed = False
        self._session = session
        self._plugin_manager = plugin_manager
        self._core = _Core(session, trace_id, trace_sampled)
        self._config = Config._create(self._core, path, plugin_manager)

        # Order does matter, need to check the main config before loading
        # the storage cookie session
        self._config._load()
        with self._config._open_db() as db:
            self._core._post_init(
                db,
            )
        self._parser = Parser._create(self._config)
        self._admin = _Admin._create(self._core, self._config)
        self._jobs = Jobs._create(self._core, self._config, self._parser)
        self._storage = Storage._create(self._core, self._config)
        self._users = Users._create(self._core, self._config)
        self._secrets = Secrets._create(self._core, self._config)
        self._disks = Disks._create(self._core, self._config)
        self._service_accounts = ServiceAccounts._create(self._core, self._config)
        self._buckets = Buckets._create(self._core, self._config, self._parser)
        self._images: Optional[Images] = None
        self._version_checker: VersionChecker = VersionChecker._create(
            self._core, self._config, plugin_manager
        )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with self._config._open_db() as db:
            self._core._save_cookies(db)
        await self._core.close()
        if self._images is not None:
            await self._images._close()
        await self._session.close()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> None:
        await self.close()

    @property
    def username(self) -> str:
        return self._config.username

    @property
    def cluster_name(self) -> str:
        return self._config.cluster_name

    @property
    def presets(self) -> Mapping[str, Preset]:
        # TODO: add deprecation warning eventually.
        # The preferred API is client.config now.
        return self._config.presets

    @property
    def config(self) -> Config:
        return self._config

    @property
    def jobs(self) -> Jobs:
        return self._jobs

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def users(self) -> Users:
        return self._users

    @property
    def images(self) -> Images:
        if self._images is None:
            self._images = Images._create(self._core, self._config, self._parser)
        return self._images

    @property
    def secrets(self) -> Secrets:
        return self._secrets

    @property
    def disks(self) -> Disks:
        return self._disks

    @property
    def service_accounts(self) -> ServiceAccounts:
        return self._service_accounts

    @property
    def buckets(self) -> Buckets:
        return self._buckets

    @property
    def parse(self) -> Parser:
        return self._parser

    @property
    def version_checker(self) -> VersionChecker:
        return self._version_checker
