from collections.abc import Awaitable, Callable

from aiohttp.test_utils import (
    RawTestServer,
)
from aiohttp.test_utils import TestClient as _TestClient
from aiohttp.test_utils import TestServer as _TestServer
from aiohttp.web import Application, Request, StreamResponse

_TestServerFactory = Callable[[Application], Awaitable[_TestServer]]
_RawTestServerFactory = Callable[
    [Callable[[Request], Awaitable[StreamResponse]]], Awaitable[RawTestServer]
]
_TestClientFactory = Callable[[Application], Awaitable[_TestClient]]  # type: ignore
