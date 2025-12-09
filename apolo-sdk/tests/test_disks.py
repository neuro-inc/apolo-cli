from collections.abc import Callable
from datetime import datetime, timedelta

from aiohttp import web

from apolo_sdk import Client, Cluster, Disk

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


async def test_list(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now() - timedelta(days=1)
    last_usage = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            [
                {
                    "id": "disk-1",
                    "storage": 500,
                    "owner": "user",
                    "project_name": "test-project",
                    "status": "Ready",
                    "created_at": created_at.isoformat(),
                    "name": None,
                    "org_name": "test-org",
                },
                {
                    "id": "disk-2",
                    "storage": 600,
                    "owner": "user",
                    "project_name": "other-project",
                    "status": "Pending",
                    "org_name": "test-org",
                    "created_at": created_at.isoformat(),
                    "last_usage": last_usage.isoformat(),
                    "life_span": 3600,
                    "name": "test-disk",
                },
            ]
        )

    app = web.Application()
    app.router.add_get("/disk", handler)

    srv = await aiohttp_server(app)

    ret = []

    async with make_client(srv.make_url("/")) as client:
        async with client.disks.list() as it:
            async for s in it:
                ret.append(s)

    assert ret == [
        Disk(
            id="disk-1",
            storage=500,
            owner="user",
            status=Disk.Status.READY,
            cluster_name=cluster_config.name,
            project_name="test-project",
            org_name="test-org",
            created_at=created_at,
            timeout_unused=None,
            name=None,
        ),
        Disk(
            id="disk-2",
            storage=600,
            owner="user",
            status=Disk.Status.PENDING,
            cluster_name=cluster_config.name,
            project_name="other-project",
            org_name="test-org",
            created_at=created_at,
            last_usage=last_usage,
            timeout_unused=timedelta(hours=1),
            name="test-disk",
        ),
    ]


async def test_add(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "storage": 500,
            "life_span": 3600,
            "name": "test-disk",
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(
            {
                "id": "disk-1",
                "storage": 500,
                "owner": "user",
                "status": "Ready",
                "created_at": created_at.isoformat(),
                "life_span": 3600,
                "name": "test-disk",
                "org_name": "test-org",
                "project_name": "test-project",
            },
        )

    app = web.Application()
    app.router.add_post("/disk", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        disk = await client.disks.create(500, timedelta(hours=1), name="test-disk")
        assert disk == Disk(
            id="disk-1",
            storage=500,
            owner="user",
            status=Disk.Status.READY,
            cluster_name=cluster_config.name,
            project_name=client.config.project_name_or_raise,
            org_name="test-org",
            created_at=created_at,
            timeout_unused=timedelta(hours=1),
            name="test-disk",
        )


async def test_add_with_org_name(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "storage": 500,
            "life_span": 3600,
            "name": "test-disk",
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(
            {
                "id": "disk-1",
                "storage": 500,
                "owner": "user",
                "status": "Ready",
                "created_at": created_at.isoformat(),
                "life_span": 3600,
                "name": "test-disk",
                "org_name": "test-org",
                "project_name": "test-project",
            },
        )

    app = web.Application()
    app.router.add_post("/disk", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        disk = await client.disks.create(
            500, timedelta(hours=1), name="test-disk", org_name="test-org"
        )
        assert disk == Disk(
            id="disk-1",
            storage=500,
            owner="user",
            status=Disk.Status.READY,
            cluster_name=cluster_config.name,
            org_name="test-org",
            project_name="test-project",
            created_at=created_at,
            timeout_unused=timedelta(hours=1),
            name="test-disk",
        )


async def test_add_with_custom_project_name(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()
    resp_pl = {
        "id": "disk-1",
        "storage": 500,
        "owner": "user",
        "status": "Ready",
        "created_at": created_at.isoformat(),
        "life_span": 3600,
        "name": "test-disk",
        "org_name": "test-org",
        "project_name": "other-project",
    }

    async def handle_post(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "storage": 500,
            "life_span": 3600,
            "name": "test-disk",
            "org_name": "test-org",
            "project_name": "other-project",
        }
        return web.json_response(resp_pl)

    async def handle_list(request: web.Request) -> web.Response:
        return web.json_response([resp_pl])

    async def handle_get(request: web.Request) -> web.Response:
        return web.json_response(resp_pl)

    app = web.Application()
    app.router.add_post("/disk", handle_post)
    app.router.add_get("/disk/{key}", handle_get)
    app.router.add_get("/disk", handle_list)

    srv = await aiohttp_server(app)

    expected = Disk(
        id="disk-1",
        storage=500,
        owner="user",
        org_name="test-org",
        status=Disk.Status.READY,
        cluster_name=cluster_config.name,
        project_name="other-project",
        created_at=created_at,
        timeout_unused=timedelta(hours=1),
        name="test-disk",
    )

    async with make_client(srv.make_url("/")) as client:
        disk_created = await client.disks.create(
            500, timedelta(hours=1), "test-disk", project_name="other-project"
        )
        assert disk_created == expected

        disk_get = await client.disks.get("test-disk")
        assert disk_get == expected

        l1 = []
        async with client.disks.list() as it:
            async for s in it:
                l1.append(s)
        assert l1 == [expected]

        l2 = []
        async with client.disks.list(project_name="other-project") as it:
            async for disk in it:
                l2.append(disk)
        assert l2 == [expected]


async def test_get(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        return web.json_response(
            {
                "id": "disk-1",
                "storage": 500,
                "used_bytes": 150,
                "owner": "user",
                "org_name": "test-org",
                "project_name": "some-project",
                "status": "Ready",
                "created_at": created_at.isoformat(),
            },
        )

    app = web.Application()
    app.router.add_get("/disk/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        disk = await client.disks.get("name")
        assert disk == Disk(
            id="disk-1",
            storage=500,
            used_bytes=150,
            owner="user",
            status=Disk.Status.READY,
            cluster_name=cluster_config.name,
            org_name="test-org",
            project_name="some-project",
            created_at=created_at,
        )


async def test_rm(aiohttp_server: _TestServerFactory, make_client: _MakeClient) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        raise web.HTTPNoContent

    app = web.Application()
    app.router.add_delete("/disk/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.disks.rm("name")
