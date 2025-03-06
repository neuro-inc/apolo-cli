from typing import Any, Callable

import pytest
from aiohttp import web

from apolo_sdk import App, Client

from tests import _TestServerFactory


@pytest.fixture
def app_payload() -> dict[str, Any]:
    return {
        "items": [
            {
                "id": "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
                "name": "superorg-test3-stable-diffusion-704285b2",
                "display_name": "Stable Diffusion",
                "template_name": "stable-diffusion",
                "template_version": "master",
                "project_name": "test3",
                "org_name": "superorg",
                "state": "errored",
            },
            {
                "id": "a4723404-f5e2-48b5-b709-629754b5056f",
                "name": "superorg-test3-stable-diffusion-a4723404",
                "display_name": "Stable Diffusion",
                "template_name": "stable-diffusion",
                "template_version": "master",
                "project_name": "test3",
                "org_name": "superorg",
                "state": "errored",
            },
        ],
        "total": 2,
        "page": 1,
        "size": 50,
        "pages": 1,
    }


async def test_apps_list(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
    app_payload: dict[str, Any],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert (
            request.path
            == "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances"
        )
        return web.json_response(app_payload)

    web_app = web.Application()
    web_app.router.add_get(
        "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances", handler
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        apps = []
        async with client.apps.list(
            cluster_name="default", org_name="superorg", project_name="test3"
        ) as it:
            async for app in it:
                apps.append(app)

        assert len(apps) == 2
        assert isinstance(apps[0], App)
        assert apps[0].id == "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"
        assert apps[0].name == "superorg-test3-stable-diffusion-704285b2"
        assert apps[0].display_name == "Stable Diffusion"
        assert apps[0].template_name == "stable-diffusion"
        assert apps[0].template_version == "master"
        assert apps[0].project_name == "test3"
        assert apps[0].org_name == "superorg"
        assert apps[0].state == "errored"
