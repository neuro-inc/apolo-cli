from typing import Callable

from aiohttp import web

from apolo_sdk import Client

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


async def test_add_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    create_cluster_json = None

    async def handle_create_cluster(request: web.Request) -> web.StreamResponse:
        nonlocal create_cluster_json
        create_cluster_json = await request.json()
        return web.json_response(create_cluster_json, status=201)

    app = web.Application()
    app.router.add_post("/apis/admin/v1/clusters", handle_create_cluster)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/api/v1")) as client:
        await client._admin.create_cluster("default")

    assert create_cluster_json == {
        "name": "default",
        "default_quota": {},
        "default_role": "user",
        "maintenance": False,
    }
