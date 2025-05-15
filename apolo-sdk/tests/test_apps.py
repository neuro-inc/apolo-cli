from datetime import datetime, timezone
from typing import Any, Callable

import pytest
from aiohttp import web
from aiohttp.web_ws import WebSocketResponse

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


@pytest.fixture
def app_values_payload() -> dict[str, Any]:
    return {
        "items": [
            {
                "app_instance_id": "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
                "type": "password",
                "path": "/credentials/admin",
                "value": "admin123",
            },
            {
                "app_instance_id": "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
                "type": "url",
                "path": "/app/url",
                "value": "https://example.com/app",
            },
            {
                "app_instance_id": "a4723404-f5e2-48b5-b709-629754b5056f",
                "type": "secret",
                "path": "/credentials/token",
                "value": "s3cr3tt0k3n",
            },
        ]
    }


async def test_apps_get_values(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
    app_values_payload: dict[str, Any],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        base_path = "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances"

        # Test URL structure based on parameters
        if request.path == f"{base_path}/values":
            # No app_id provided
            assert not request.path.endswith(
                "/704285b2-aab1-4b0a-b8ff-bfbeb37f89e4/values"
            )
            # Optional value_type parameter
            if request.query.get("type"):
                assert request.query.get("type") == "password"
                filtered_payload = {
                    "items": [
                        item
                        for item in app_values_payload["items"]
                        if item["type"] == "password"
                    ]
                }
                return web.json_response(filtered_payload)
        elif request.path == f"{base_path}/704285b2-aab1-4b0a-b8ff-bfbeb37f89e4/values":
            # Specific app_id provided
            filtered_payload = {
                "items": [
                    item
                    for item in app_values_payload["items"]
                    if item["app_instance_id"] == "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"
                ]
            }
            return web.json_response(filtered_payload)

        return web.json_response(app_values_payload)

    web_app = web.Application()
    base_path = "/apis/apps/v1/cluster/default/org/superorg/project/test3/instances"
    # Add routes for different combinations of parameters
    web_app.router.add_get(f"{base_path}/values", handler)
    web_app.router.add_get(
        f"{base_path}/704285b2-aab1-4b0a-b8ff-bfbeb37f89e4/values", handler
    )

    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        # Test 1: No filters (get all values)
        values = []
        async with client.apps.get_values(
            cluster_name="default", org_name="superorg", project_name="test3"
        ) as it:
            async for value in it:
                values.append(value)

        assert len(values) == 3
        assert values[0].app_instance_id == "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"
        assert values[0].type == "password"
        assert values[0].path == "/credentials/admin"
        assert values[0].value == "admin123"

        assert values[1].app_instance_id == "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"
        assert values[1].type == "url"
        assert values[1].path == "/app/url"
        assert values[1].value == "https://example.com/app"

        assert values[2].app_instance_id == "a4723404-f5e2-48b5-b709-629754b5056f"
        assert values[2].type == "secret"
        assert values[2].path == "/credentials/token"
        assert values[2].value == "s3cr3tt0k3n"

        # Test 2: Filter by app_id
        values = []
        async with client.apps.get_values(
            app_id="704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
            cluster_name="default",
            org_name="superorg",
            project_name="test3",
        ) as it:
            async for value in it:
                values.append(value)

        assert len(values) == 2
        for value in values:
            assert value.app_instance_id == "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"

        # Test 3: Filter by value_type
        values = []
        async with client.apps.get_values(
            value_type="password",
            cluster_name="default",
            org_name="superorg",
            project_name="test3",
        ) as it:
            async for value in it:
                values.append(value)

        assert len(values) == 1
        assert values[0].type == "password"
        assert values[0].path == "/credentials/admin"


async def test_apps_logs(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    app_id = "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4"
    test_log_messages = [
        b"Starting app...\n",
        b"App initialized\n",
        b"App is now running\n",
    ]

    async def ws_handler(request: web.Request) -> WebSocketResponse:
        assert request.path == f"/api/v1/apps/{app_id}/log_ws"

        # Verify query parameters
        qs = request.query
        if "since" in qs:
            assert qs["since"] == "2025-05-07T11:00:00+00:00"
        if "timestamps" in qs:
            assert qs["timestamps"] == "true"

        ws = WebSocketResponse()
        await ws.prepare(request)

        for msg in test_log_messages:
            await ws.send_bytes(msg)

        await ws.close()
        return ws

    web_app = web.Application()
    web_app.router.add_get(f"/api/v1/apps/{app_id}/log_ws", ws_handler)

    srv = await aiohttp_server(web_app)
    url = srv.make_url("/")

    # Create a monitoring URL with http scheme (not https/wss) for the test server
    monitoring_url = url

    async with make_client(url, monitoring_url=monitoring_url) as client:
        # Test 1: Basic logs retrieval
        logs = []
        async with client.apps.logs(app_id) as it:
            async for chunk in it:
                logs.append(chunk)

        assert logs == test_log_messages

        # Test 2: Logs with parameters
        logs = []
        test_datetime = datetime(2025, 5, 7, 11, 0, 0, tzinfo=timezone.utc)
        async with client.apps.logs(
            app_id,
            since=test_datetime,
            timestamps=True,
        ) as it:
            async for chunk in it:
                logs.append(chunk)

        assert logs == test_log_messages
