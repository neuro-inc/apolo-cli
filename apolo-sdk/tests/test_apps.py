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


async def test_apps_install(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    app_data = {
        "template_name": "stable-diffusion",
        "template_version": "master",
        "input": {},
    }

    async def handler(request: web.Request) -> web.Response:
        assert request.method == "POST"
        url = "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances"
        assert request.path == url
        assert await request.json() == app_data
        return web.Response(status=201)

    web_app = web.Application()
    web_app.router.add_post(
        "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances", handler
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        await client.apps.install(
            app_data=app_data,
            cluster_name="default",
            org_name="superorg",
            project_name="test3",
        )


async def test_apps_uninstall(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    app_id = "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"

    async def handler(request: web.Request) -> web.Response:
        assert request.method == "DELETE"
        url = (
            "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances/"
            + app_id
        )
        assert request.path == url
        return web.Response(status=204)

    web_app = web.Application()
    web_app.router.add_delete(
        f"/apis/apps/v1/cluster/default/org/superorg/project/test3/instances/{app_id}",
        handler,
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        await client.apps.uninstall(
            app_id=app_id,
            cluster_name="default",
            org_name="superorg",
            project_name="test3",
        )


@pytest.fixture
def app_templates_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": "stable-diffusion",
            "version": "master",
            "title": "Stable Diffusion",
            "short_description": "AI image generation model",
            "tags": ["ai", "image-generation"],
        },
        {
            "name": "jupyter-notebook",
            "version": "1.0.0",
            "title": "Jupyter Notebook",
            "short_description": "Interactive computing environment",
            "tags": ["development", "data-science"],
        },
    ]


async def test_apps_list_templates(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
    app_templates_payload: list[dict[str, Any]],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert (
            request.path
            == "/apis/apps/v1/cluster/default/org/superorg/project/test3/templates"
        )
        return web.json_response(app_templates_payload)

    web_app = web.Application()
    web_app.router.add_get(
        "/apis/apps/v1/cluster/default/org/superorg/project/test3/templates", handler
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        templates = []
        async with client.apps.list_templates(
            cluster_name="default", org_name="superorg", project_name="test3"
        ) as it:
            async for template in it:
                templates.append(template)

        assert len(templates) == 2
        assert templates[0].name == "stable-diffusion"
        assert templates[0].version == "master"
        assert templates[0].title == "Stable Diffusion"
        assert templates[0].short_description == "AI image generation model"
        assert templates[0].tags == ["ai", "image-generation"]

        assert templates[1].name == "jupyter-notebook"
        assert templates[1].version == "1.0.0"
        assert templates[1].title == "Jupyter Notebook"
        assert templates[1].short_description == "Interactive computing environment"
        assert templates[1].tags == ["development", "data-science"]


@pytest.fixture
def app_template_versions_payload() -> list[dict[str, Any]]:
    return [
        {
            "version": "master",
            "title": "Stable Diffusion",
            "short_description": "AI image generation model",
            "tags": ["ai", "image-generation"],
        },
        {
            "version": "1.0.0",
            "title": "Stable Diffusion v1",
            "short_description": "Stable Diffusion v1.0 release",
            "tags": ["ai", "image-generation", "stable"],
        },
        {
            "version": "2.0.0",
            "title": "Stable Diffusion v2",
            "short_description": "Stable Diffusion v2.0 with improved generation",
            "tags": ["ai", "image-generation", "stable"],
        },
    ]


async def test_apps_list_template_versions(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
    app_template_versions_payload: list[dict[str, Any]],
) -> None:
    template_name = "stable-diffusion"

    async def handler(request: web.Request) -> web.Response:
        base_path = "/apis/apps/v1/cluster/default/org/superorg/project/test3"
        template_path = f"{base_path}/templates/{template_name}"
        assert request.path == template_path
        return web.json_response(app_template_versions_payload)

    web_app = web.Application()
    base_path = "/apis/apps/v1/cluster/default/org/superorg/project/test3"
    app_path = f"{base_path}/templates/{template_name}"
    web_app.router.add_get(
        app_path,
        handler,
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        versions = []
        async with client.apps.list_template_versions(
            name=template_name,
            cluster_name="default",
            org_name="superorg",
            project_name="test3",
        ) as it:
            async for version in it:
                versions.append(version)

        assert len(versions) == 3

        # Check that all versions have the same template name
        for version in versions:
            assert version.name == template_name

        # Check first version
        assert versions[0].version == "master"
        assert versions[0].title == "Stable Diffusion"
        assert versions[0].short_description == "AI image generation model"
        assert versions[0].tags == ["ai", "image-generation"]

        # Check second version
        assert versions[1].version == "1.0.0"
        assert versions[1].title == "Stable Diffusion v1"
        assert versions[1].short_description == "Stable Diffusion v1.0 release"
        assert versions[1].tags == ["ai", "image-generation", "stable"]

        # Check third version
        assert versions[2].version == "2.0.0"
        assert versions[2].title == "Stable Diffusion v2"
        assert (
            versions[2].short_description
            == "Stable Diffusion v2.0 with improved generation"
        )
        assert versions[2].tags == ["ai", "image-generation", "stable"]
