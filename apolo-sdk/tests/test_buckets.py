from collections.abc import Callable
from datetime import datetime, timedelta

from aiohttp import web

from apolo_sdk import Bucket, Client, Cluster

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


async def test_list(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now() - timedelta(days=1)

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            [
                {
                    "id": "bucket-1",
                    "owner": "user",
                    "name": None,
                    "provider": "aws",
                    "created_at": created_at.isoformat(),
                    "imported": False,
                    # support None for backward compatibility
                    # all new buckets should have real org name
                    "org_name": "test-org",
                    "project_name": "test-project",
                },
                {
                    "id": "bucket-2",
                    "owner": "user",
                    "name": "test-bucket",
                    "provider": "aws",
                    "created_at": created_at.isoformat(),
                    "imported": True,
                    "org_name": "test-org",
                    "project_name": "test-project",
                },
            ]
        )

    app = web.Application()
    app.router.add_get("/buckets/buckets", handler)

    srv = await aiohttp_server(app)

    ret = []

    async with make_client(srv.make_url("/")) as client:
        async with client.buckets.list() as it:
            async for s in it:
                ret.append(s)

    assert ret == [
        Bucket(
            id="bucket-1",
            owner="user",
            cluster_name=cluster_config.name,
            name=None,
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="test-org",
            project_name="test-project",
        ),
        Bucket(
            id="bucket-2",
            owner="user",
            cluster_name=cluster_config.name,
            name="test-bucket",
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=True,
            org_name="test-org",
            project_name="test-project",
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
            "name": "test-bucket",
            "org_name": "test_org",
            "project_name": "test-project",
        }
        return web.json_response(
            {
                "id": "bucket-1",
                "owner": "user",
                "name": "test-bucket",
                "created_at": created_at.isoformat(),
                "provider": "aws",
                "project_name": "test-project",
                "org_name": "test_org",
            }
        )

    app = web.Application()
    app.router.add_post("/buckets/buckets", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), org_name="test_org") as client:
        bucket = await client.buckets.create(name="test-bucket")
        assert bucket == Bucket(
            id="bucket-1",
            owner="user",
            cluster_name=cluster_config.name,
            name="test-bucket",
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="test_org",
            project_name="test-project",
        )


async def test_add_with_org(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "name": "test-bucket",
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(
            {
                "id": "bucket-1",
                "owner": "user",
                "name": "test-bucket",
                "created_at": created_at.isoformat(),
                "provider": "aws",
                "org_name": "test-org",
                "project_name": "test-project",
            }
        )

    app = web.Application()
    app.router.add_post("/buckets/buckets", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.create(name="test-bucket", org_name="test-org")
        assert bucket == Bucket(
            id="bucket-1",
            owner="user",
            cluster_name=cluster_config.name,
            name="test-bucket",
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="test-org",
            project_name="test-project",
        )


async def test_import(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "name": "test-bucket",
            "provider": "aws",
            "provider_bucket_name": "test-external",
            "credentials": {"key": "value"},
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(
            {
                "id": "bucket-1",
                "owner": "user",
                "name": "test-bucket",
                "created_at": created_at.isoformat(),
                "provider": "aws",
                "imported": True,
                "project_name": "test-project",
                "org_name": "test_org",
            }
        )

    app = web.Application()
    app.router.add_post("/buckets/buckets/import/external", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.import_external(
            provider=Bucket.Provider.AWS,
            provider_bucket_name="test-external",
            credentials={"key": "value"},
            name="test-bucket",
        )
        assert bucket == Bucket(
            id="bucket-1",
            owner="user",
            cluster_name=cluster_config.name,
            name="test-bucket",
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=True,
            org_name="test_org",
            project_name="test-project",
        )


async def test_import_with_org(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "name": "test-bucket",
            "provider": "aws",
            "provider_bucket_name": "test-external",
            "credentials": {"key": "value"},
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(
            {
                "id": "bucket-1",
                "owner": "user",
                "name": "test-bucket",
                "created_at": created_at.isoformat(),
                "provider": "aws",
                "imported": True,
                "org_name": "test-org",
                "project_name": "test-project",
            }
        )

    app = web.Application()
    app.router.add_post("/buckets/buckets/import/external", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.import_external(
            provider=Bucket.Provider.AWS,
            provider_bucket_name="test-external",
            credentials={"key": "value"},
            name="test-bucket",
            org_name="test-org",
            project_name="test-project",
        )
        assert bucket == Bucket(
            id="bucket-1",
            owner="user",
            cluster_name=cluster_config.name,
            name="test-bucket",
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=True,
            org_name="test-org",
            project_name="test-project",
        )


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
                "id": "bucket-1",
                "owner": "user",
                "name": "name",
                "project_name": "test-project",
                "provider": "aws",
                "created_at": created_at.isoformat(),
                "org_name": "test_org",
            }
        )

    app = web.Application()
    app.router.add_get("/buckets/buckets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.get("name")
        assert bucket == Bucket(
            id="bucket-1",
            owner="user",
            cluster_name=cluster_config.name,
            name="name",
            created_at=created_at,
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="test_org",
            project_name="test-project",
        )


async def test_set_public(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    created_at = datetime.now()

    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        data = await request.json()
        assert data == {"public": True}
        return web.json_response(
            {
                "id": "bucket-1",
                "owner": "user",
                "name": "name",
                "project_name": "test-project",
                "provider": "aws",
                "created_at": created_at.isoformat(),
                "public": True,
            }
        )

    app = web.Application()
    app.router.add_patch("/buckets/buckets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.set_public_access("name", True)
        assert bucket.public


async def test_rm(aiohttp_server: _TestServerFactory, make_client: _MakeClient) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        raise web.HTTPNoContent

    app = web.Application()
    app.router.add_delete("/buckets/buckets/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.buckets.rm("name")
