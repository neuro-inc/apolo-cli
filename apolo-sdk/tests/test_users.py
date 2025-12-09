from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from aiohttp import web
from yarl import URL

from apolo_sdk import Action, Client, Permission, Quota, ResourceNotFound

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


@pytest.fixture()
async def mocked_share_client(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> AsyncIterator[Client]:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data[0]["action"] in [item.value for item in Action]
        data[0]["action"] = Action.MANAGE.value
        return web.json_response(data, status=web.HTTPCreated.status_code)

    app = web.Application()
    app.router.add_post("/users/bill/permissions", handler)
    srv = await aiohttp_server(app)
    client = make_client(srv.make_url("/"))
    yield client
    await client.close()


@pytest.fixture()
async def mocked_revoke_client(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> AsyncIterator[Client]:
    async def handler(request: web.Request) -> web.Response:
        assert "uri" in request.query
        raise web.HTTPNoContent()

    app = web.Application()
    app.router.add_delete("/users/bill/permissions", handler)
    srv = await aiohttp_server(app)
    client = make_client(srv.make_url("/"))
    yield client
    await client.close()


@pytest.fixture()
async def mocked_add_role_client(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> AsyncIterator[Client]:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data["name"].startswith("mycompany/")
        raise web.HTTPCreated()

    app = web.Application()
    app.router.add_post("/users", handler)
    srv = await aiohttp_server(app)
    client = make_client(srv.make_url("/"))
    yield client
    await client.close()


@pytest.fixture()
async def mocked_remove_role_client(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> AsyncIterator[Client]:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["name"].startswith("mycompany:")
        raise web.HTTPNoContent()

    app = web.Application()
    app.router.add_delete("/users/{name}", handler)
    srv = await aiohttp_server(app)
    client = make_client(srv.make_url("/"))
    yield client
    await client.close()


@pytest.fixture()
async def mocked_get_quota_client(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> AsyncIterator[Client]:
    date = datetime.now(timezone.utc)

    async def handle_get_cluster_user(request: web.Request) -> web.StreamResponse:
        data = {
            "user_name": "denis",
            "role": "admin",
            "user_info": {
                "first_name": "denis",
                "last_name": "admin",
                "email": "denis@domain.name",
                "created_at": date.isoformat(),
            },
            "balance": {
                "credits": "500",
                "spent_credits": "10",
            },
            "quota": {"total_running_jobs": 10},
        }
        return web.json_response(data)

    app = web.Application()
    app.router.add_get(
        "/apis/admin/v1/clusters/{cluster_name}/orgs/test-org/users/{username}",
        handle_get_cluster_user,
    )

    srv = await aiohttp_server(app)

    client = make_client(srv.make_url("/api/v1"))
    yield client
    await client.close()


@pytest.fixture()
async def mocked_get_subroles_client(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> AsyncIterator[Client]:
    async def handle_get_subroles(request: web.Request) -> web.StreamResponse:
        username = request.match_info["username"]
        data = {
            "subroles": [f"{username}/sub1", f"{username}/sub2", f"{username}/sub3"]
        }
        return web.json_response(data)

    app = web.Application()
    app.router.add_get(
        "/api/v1/users/{username}/subroles",
        handle_get_subroles,
    )

    srv = await aiohttp_server(app)

    client = make_client(srv.make_url("/api/v1"))
    yield client
    await client.close()


class TestUsers:
    async def test_get_quota(self, mocked_get_quota_client: Client) -> None:
        res = await mocked_get_quota_client.users.get_quota()
        assert res == Quota(credits=Decimal("500"), total_running_jobs=10)

    async def test_get_quota_adminless(self, make_client: _MakeClient) -> None:
        async with make_client("https://dev.example.com", admin_url="") as client:
            quota = await client.users.get_quota()
            assert quota.credits is None
            assert quota.total_running_jobs is None

    async def test_share_unknown_user(self, mocked_share_client: Client) -> None:
        with pytest.raises(ResourceNotFound):
            await mocked_share_client.users.share(
                user="not-exists",
                permission=Permission(URL("storage://bob/resource"), Action.READ),
            )

    async def test_share_invalid_name(self, mocked_share_client: Client) -> None:
        with pytest.raises(ValueError):
            await mocked_share_client.users.share(
                user="mycompany/team:role",
                permission=Permission(URL("storage://bob/resource"), Action.READ),
            )

    async def test_correct_share(self, mocked_share_client: Client) -> None:
        ret = await mocked_share_client.users.share(
            user="bill",
            permission=Permission(URL("storage://bob/resource"), Action.READ),
        )
        assert ret == Permission(URL("storage://bob/resource"), Action.MANAGE)

    async def test_revoke_unknown_user(self, mocked_revoke_client: Client) -> None:
        with pytest.raises(ResourceNotFound):
            await mocked_revoke_client.users.revoke(
                user="not-exists", uri=URL("storage://bob/resource")
            )

    async def test_revoke_invalid_name(self, mocked_revoke_client: Client) -> None:
        with pytest.raises(ValueError):
            await mocked_revoke_client.users.revoke(
                user="mycompany/team:role", uri=URL("storage://bob/resource")
            )

    async def test_correct_revoke(self, mocked_revoke_client: Client) -> None:
        await mocked_revoke_client.users.revoke(
            user="bill", uri=URL("storage://bob/resource")
        )

    async def test_add_role(self, mocked_add_role_client: Client) -> None:
        await mocked_add_role_client.users.add("mycompany/team/role")

    async def test_remove_role(self, mocked_remove_role_client: Client) -> None:
        await mocked_remove_role_client.users.remove("mycompany/team/role")

    async def test_get_subroles(self, mocked_get_subroles_client: Client) -> None:
        res = await mocked_get_subroles_client.users.get_subroles("test")
        assert set(res) == {"test/sub1", "test/sub2", "test/sub3"}

    async def test_remove_role_invalid_name(
        self, mocked_remove_role_client: Client
    ) -> None:
        with pytest.raises(ValueError):
            await mocked_remove_role_client.users.remove("mycompany/team:role")
