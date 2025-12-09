from collections.abc import Callable

import pytest
from aiohttp import web
from yarl import URL

from apolo_sdk import Client, NotSupportedError

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


async def test_not_supported_admin_api(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/api/v1"), admin_url=URL()) as client:
        with pytest.raises(
            NotSupportedError, match="admin API is not supported by server"
        ):
            await client._admin.get_cluster_user("default", "test")
