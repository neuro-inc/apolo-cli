from collections.abc import Callable

from aiohttp import web

from apolo_sdk import (
    Bucket,
    BucketCredentials,
    Client,
    Cluster,
    PersistentBucketCredentials,
)

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


async def test_list(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            [
                {
                    "id": "credentials-1",
                    "owner": "user",
                    "name": None,
                    "read_only": True,
                    "credentials": [
                        {
                            "bucket_id": "test-1",
                            "provider": "aws",
                            "credentials": {
                                "key": "value",
                            },
                        },
                        {
                            "bucket_id": "test-2",
                            "provider": "aws",
                            "credentials": {
                                "key": "value",
                            },
                        },
                    ],
                },
                {
                    "id": "credentials-2",
                    "owner": "user",
                    "name": None,
                    "read_only": False,
                    "credentials": [
                        {
                            "bucket_id": "test-3",
                            "provider": "aws",
                            "credentials": {
                                "key": "value",
                            },
                        },
                        {
                            "bucket_id": "test-4",
                            "provider": "aws",
                            "credentials": {
                                "key": "value",
                            },
                        },
                    ],
                },
            ]
        )

    app = web.Application()
    app.router.add_get("/buckets/persistent_credentials", handler)

    srv = await aiohttp_server(app)

    ret = []

    async with make_client(srv.make_url("/")) as client:
        async with client.buckets.persistent_credentials_list() as it:
            async for s in it:
                ret.append(s)

    assert ret == [
        PersistentBucketCredentials(
            id="credentials-1",
            owner="user",
            cluster_name=cluster_config.name,
            name=None,
            read_only=True,
            credentials=[
                BucketCredentials(
                    bucket_id="test-1",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
                BucketCredentials(
                    bucket_id="test-2",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
            ],
        ),
        PersistentBucketCredentials(
            id="credentials-2",
            owner="user",
            cluster_name=cluster_config.name,
            name=None,
            read_only=False,
            credentials=[
                BucketCredentials(
                    bucket_id="test-3",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
                BucketCredentials(
                    bucket_id="test-4",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
            ],
        ),
    ]


async def test_add(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "name": "test-bucket",
            "bucket_ids": ["test-1", "test-2"],
            "read_only": False,
        }
        return web.json_response(
            {
                "id": "credentials-1",
                "owner": "user",
                "name": None,
                "credentials": [
                    {
                        "bucket_id": "test-1",
                        "provider": "aws",
                        "credentials": {
                            "key": "value",
                        },
                    },
                    {
                        "bucket_id": "test-2",
                        "provider": "aws",
                        "credentials": {
                            "key": "value",
                        },
                    },
                ],
            }
        )

    app = web.Application()
    app.router.add_post("/buckets/persistent_credentials", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.persistent_credentials_create(
            name="test-bucket", bucket_ids=["test-1", "test-2"]
        )
        assert bucket == PersistentBucketCredentials(
            id="credentials-1",
            owner="user",
            cluster_name=cluster_config.name,
            name=None,
            read_only=False,
            credentials=[
                BucketCredentials(
                    bucket_id="test-1",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
                BucketCredentials(
                    bucket_id="test-2",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
            ],
        )


async def test_add_readonly(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "name": "test-bucket",
            "bucket_ids": ["test-1", "test-2"],
            "read_only": True,
        }
        return web.json_response(
            {
                "id": "credentials-1",
                "owner": "user",
                "name": None,
                "read_only": True,
                "credentials": [
                    {
                        "bucket_id": "test-1",
                        "provider": "aws",
                        "credentials": {
                            "key": "value",
                        },
                    },
                    {
                        "bucket_id": "test-2",
                        "provider": "aws",
                        "credentials": {
                            "key": "value",
                        },
                    },
                ],
            }
        )

    app = web.Application()
    app.router.add_post("/buckets/persistent_credentials", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.persistent_credentials_create(
            name="test-bucket",
            bucket_ids=["test-1", "test-2"],
            read_only=True,
        )
        assert bucket == PersistentBucketCredentials(
            id="credentials-1",
            owner="user",
            cluster_name=cluster_config.name,
            name=None,
            read_only=True,
            credentials=[
                BucketCredentials(
                    bucket_id="test-1",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
                BucketCredentials(
                    bucket_id="test-2",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
            ],
        )


async def test_get(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_config: Cluster,
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        return web.json_response(
            {
                "id": "credentials-1",
                "owner": "user",
                "name": None,
                "credentials": [
                    {
                        "bucket_id": "test-1",
                        "provider": "aws",
                        "credentials": {
                            "key": "value",
                        },
                    },
                    {
                        "bucket_id": "test-2",
                        "provider": "aws",
                        "credentials": {
                            "key": "value",
                        },
                    },
                ],
            }
        )

    app = web.Application()
    app.router.add_get("/buckets/persistent_credentials/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        bucket = await client.buckets.persistent_credentials_get("name")
        assert bucket == PersistentBucketCredentials(
            id="credentials-1",
            owner="user",
            cluster_name=cluster_config.name,
            name=None,
            read_only=False,
            credentials=[
                BucketCredentials(
                    bucket_id="test-1",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
                BucketCredentials(
                    bucket_id="test-2",
                    provider=Bucket.Provider.AWS,
                    credentials={
                        "key": "value",
                    },
                ),
            ],
        )


async def test_rm(aiohttp_server: _TestServerFactory, make_client: _MakeClient) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["key"] == "name"
        raise web.HTTPNoContent

    app = web.Application()
    app.router.add_delete("/buckets/persistent_credentials/{key}", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.buckets.persistent_credentials_rm("name")
