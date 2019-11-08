import time
from http.cookies import Morsel  # noqa
from http.cookies import SimpleCookie
from types import MappingProxyType, TracebackType
from typing import Mapping, Optional, Type

import aiohttp

from neuromation.api.quota import _Quota

from .config import _Config
from .core import _Core
from .images import Images
from .jobs import Jobs
from .login import Preset
from .parser import Parser
from .storage import Storage
from .users import Users
from .utils import NoPublicConstructor


SESSION_COOKIE_MAXAGE = 5 * 60  # 5 min


class Client(metaclass=NoPublicConstructor):
    def __init__(
        self, session: aiohttp.ClientSession, config: _Config, trace_id: Optional[str]
    ) -> None:
        self._closed = False
        config.check_initialized()
        self._config = config
        self._trace_id = trace_id
        self._session = session
        if time.time() - config.cookie_session.timestamp > SESSION_COOKIE_MAXAGE:
            # expired
            cookie: Optional["Morsel[str]"] = None
        else:
            tmp = SimpleCookie()  # type: ignore
            tmp["NEURO_SESSION"] = config.cookie_session.cookie
            cookie = tmp["NEURO_SESSION"]
            assert config.url.raw_host is not None
            cookie["domain"] = config.url.raw_host
            cookie["path"] = "/"
        self._core = _Core(
            session, self._config.url, self._config.auth_token.token, cookie, trace_id
        )
        self._jobs = Jobs._create(self._core, self._config)
        self._storage = Storage._create(self._core, self._config)
        self._users = Users._create(self._core)
        self._parser = Parser._create(self._config, self.username)
        self._quota = _Quota._create(self._core, self._config)
        self._images: Optional[Images] = None

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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
        return self._config.auth_token.username

    @property
    def presets(self) -> Mapping[str, Preset]:
        return MappingProxyType(self._config.cluster_config.resource_presets)

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
            self._images = Images._create(self._core, self._config)
        return self._images

    @property
    def parse(self) -> Parser:
        return self._parser

    def _get_session_cookie(self) -> Optional["Morsel[str]"]:
        for cookie in self._core._session.cookie_jar:
            if cookie.key == "NEURO_SESSION":
                return cookie
        return None
