import base64
from typing import Callable

from aiohttp import web

from apolo_sdk import Client, Secret

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


async def test_list(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            [
                {
                    "key": "name1",
                    "owner": "test",
                    "project_name": "test-project",
                    # support no-org secrets for backward compatibility,
                    # new secrets should always have the real org name
                },
                {
                    "key": "name2",
                    "owner": "test",
                    "org_name": "test-org",
                    "project_name": "test-project",
                },
            ]
        )

    app = web.Application()
    app.router.add_get("/secrets", handler)

    srv = await aiohttp_server(app)

    ret = []

    async with make_client(srv.make_url("/")) as client:
        async with client.secrets.list() as it:
            async for s in it:
                ret.append(s)

    assert ret == [
        Secret(
            key="name1",
            owner="test",
            cluster_name="default",
            org_name="NO_ORG",
            project_name="test-project",
        ),
        Secret(
            key="name2",
            owner="test",
            cluster_name="default",
            org_name="test-org",
            project_name="test-project",
        ),
    ]


async def test_add(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "key": "name",
            "value": base64.b64encode(b"data").decode("ascii"),
            "project_name": "test-project",
            "org_name": "NO_ORG",
        }
        raise web.HTTPCreated

    app = web.Application()
    app.router.add_post("/secrets", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.secrets.add("name", b"data")


async def test_add_with_org(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "key": "name",
            "value": base64.b64encode(b"data").decode("ascii"),
            "org_name": "test-org",
            "project_name": "test-project",
        }
        raise web.HTTPCreated

    app = web.Application()
    app.router.add_post("/secrets", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.secrets.add("name", b"data", org_name="test-org")


async def test_add_with_project(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "key": "name",
            "value": base64.b64encode(b"data").decode("ascii"),
            "project_name": "project",
            "org_name": "NO_ORG",
        }
        raise web.HTTPCreated

    app = web.Application()
    app.router.add_post("/secrets", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.secrets.add("name", b"data", project_name="project")


async def test_rm(aiohttp_server: _TestServerFactory, make_client: _MakeClient) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        raise web.HTTPNoContent

    app = web.Application()
    app.router.add_delete("/secrets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.secrets.rm("name")


async def test_rm_with_org(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        assert request.query.get("org_name") == "test-org"
        raise web.HTTPNoContent

    app = web.Application()
    app.router.add_delete("/secrets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.secrets.rm("name", org_name="test-org")


async def test_rm_with_project(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        assert request.query.get("project_name") == "project"
        raise web.HTTPNoContent

    app = web.Application()
    app.router.add_delete("/secrets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.secrets.rm("name", project_name="project")


async def test_get(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        assert request.query.get("project_name") == "test-project"
        return web.json_response({"value": base64.b64encode(b"data").decode("ascii")})

    app = web.Application()
    app.router.add_get("/secrets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        result = await client.secrets.get("name")
        assert result == b"data"


async def test_get_with_org(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        assert request.query.get("org_name") == "test-org"
        return web.json_response({"value": base64.b64encode(b"data").decode("ascii")})

    app = web.Application()
    app.router.add_get("/secrets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        result = await client.secrets.get("name", org_name="test-org")
        assert result == b"data"


async def test_get_with_project(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        assert request.query.get("project_name") == "project"
        return web.json_response({"value": base64.b64encode(b"data").decode("ascii")})

    app = web.Application()
    app.router.add_get("/secrets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        result = await client.secrets.get("name", project_name="project")
        assert result == b"data"
