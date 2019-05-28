from pathlib import Path
from typing import Any, Callable, Dict, Tuple

import click
import pytest
from aiohttp import web
from yarl import URL

from neuromation.api import Action, Client
from neuromation.cli.root import Root
from neuromation.cli.utils import (
    LocalRemotePortParamType,
    parse_file_resource,
    parse_permission_action,
    parse_resource_for_sharing,
    resolve_job,
)
from tests import _TestServerFactory


_MakeClient = Callable[..., Client]


async def test_resolve_job_id__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON: Dict[str, Any] = {"jobs": []}
    job_id = "job-81839be3-3ecf-4ec5-80d9-19b1588869db"
    job_name_to_resolve = job_id

    async def handler(request: web.Request) -> web.Response:
        assert request.query.get("name") == job_name_to_resolve
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(client, job_name_to_resolve)
        assert resolved == job_id


async def test_resolve_job_id__single_job_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name_to_resolve = "test-job-name-555"
    JSON = {
        "jobs": [
            {
                "id": "job-efb7d723-722c-4d5c-a5db-de258db4b09e",
                "owner": "test1",
                "status": "running",
                "history": {
                    "status": "running",
                    "reason": None,
                    "description": None,
                    "created_at": "2019-03-18T12:41:10.573468+00:00",
                    "started_at": "2019-03-18T12:41:16.804040+00:00",
                },
                "container": {
                    "image": "ubuntu:latest",
                    "env": {},
                    "volumes": [],
                    "command": "sleep 1h",
                    "resources": {"cpu": 0.1, "memory_mb": 1024, "shm": True},
                },
                "ssh_auth_server": "ssh://nobody@ssh-auth-dev.neu.ro:22",
                "is_preemptible": True,
                "name": job_name_to_resolve,
                "internal_hostname": "job-efb7d723-722c-4d5c-a5db-de258db4b09e.default",
            }
        ]
    }
    job_id = JSON["jobs"][0]["id"]

    async def handler(request: web.Request) -> web.Response:
        assert request.query.get("name") == job_name_to_resolve
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(client, job_name_to_resolve)
        assert resolved == job_id


async def test_resolve_job_id__multiple_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name_to_resolve = "job-name-123-000"
    JSON = {
        "jobs": [
            {
                "id": "job-d912aa8c-d01b-44bd-b77c-5a19fc151f89",
                "owner": "test1",
                "status": "succeeded",
                "history": {
                    "status": "succeeded",
                    "reason": None,
                    "description": None,
                    "created_at": "2019-03-17T16:24:54.746175+00:00",
                    "started_at": "2019-03-17T16:25:00.868880+00:00",
                    "finished_at": "2019-03-17T16:28:01.298487+00:00",
                },
                "container": {
                    "image": "ubuntu:latest",
                    "env": {},
                    "volumes": [],
                    "command": "sleep 3m",
                    "resources": {"cpu": 0.1, "memory_mb": 1024, "shm": True},
                },
                "ssh_auth_server": "ssh://nobody@ssh-auth-dev.neu.ro:22",
                "is_preemptible": True,
                "name": job_name_to_resolve,
                "internal_hostname": "job-d912aa8c-d01b-44bd-b77c-5a19fc151f89.default",
            },
            {
                "id": "job-e5071b6b-2e97-4cce-b12d-86e31751dc8a",
                "owner": "test1",
                "status": "succeeded",
                "history": {
                    "status": "succeeded",
                    "reason": None,
                    "description": None,
                    "created_at": "2019-03-18T11:31:03.669549+00:00",
                    "started_at": "2019-03-18T11:31:10.428975+00:00",
                    "finished_at": "2019-03-18T11:31:54.896666+00:00",
                },
                "container": {
                    "image": "ubuntu:latest",
                    "env": {},
                    "volumes": [],
                    "command": "sleep 5m",
                    "resources": {"cpu": 0.1, "memory_mb": 1024, "shm": True},
                },
                "ssh_auth_server": "ssh://nobody@ssh-auth-dev.neu.ro:22",
                "is_preemptible": True,
                "name": job_name_to_resolve,
                "internal_hostname": "job-e5071b6b-2e97-4cce-b12d-86e31751dc8a.default",
            },
        ]
    }
    job_id = JSON["jobs"][-1]["id"]

    async def handler(request: web.Request) -> web.Response:
        assert request.query.get("name") == job_name_to_resolve
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(client, job_name_to_resolve)
        assert resolved == job_id


async def test_resolve_job_id__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_id = "job-81839be3-3ecf-4ec5-80d9-19b1588869db"
    job_name_to_resolve = job_id

    async def handler(request: web.Request) -> web.Response:
        assert request.query.get("name") == job_name_to_resolve
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(client, job_name_to_resolve)
        assert resolved == job_id


def test_parse_file_resource_no_scheme(root: Root) -> None:
    parsed = parse_file_resource("scheme-less/resource", root)
    assert parsed == URL((Path.cwd() / "scheme-less/resource").as_uri())
    parsed = parse_file_resource("c:scheme-less/resource", root)
    assert parsed == URL(Path("c:scheme-less/resource").resolve().as_uri())


def test_parse_file_resource_unsupported_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_file_resource("http://neuromation.io", root)
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_file_resource("image:ubuntu", root)


def test_parse_file_resource_user_less(root: Root) -> None:
    user_less_permission = parse_file_resource("storage:resource", root)
    assert user_less_permission == URL(f"storage://{root.username}/resource")


def test_parse_file_resource_with_user(root: Root) -> None:
    full_permission = parse_file_resource(f"storage://{root.username}/resource", root)
    assert full_permission == URL(f"storage://{root.username}/resource")
    full_permission = parse_file_resource(f"storage://alice/resource", root)
    assert full_permission == URL(f"storage://alice/resource")


def test_parse_file_resource_with_tilde(root: Root) -> None:
    parsed = parse_file_resource(f"storage://~/resource", root)
    assert parsed == URL(f"storage://{root.username}/resource")


def test_parse_resource_for_sharing_image_1_no_tag(root: Root) -> None:
    uri = "image://~/ubuntu"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(f"image://{root.username}/ubuntu")


def test_parse_resource_for_sharing_image_2_no_tag(root: Root) -> None:
    uri = "image:ubuntu"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(f"image://{root.username}/ubuntu")


def test_parse_resource_for_sharing_image_with_tag_fail(root: Root) -> None:
    uri = "image://~/ubuntu:latest"
    with pytest.raises(ValueError, match="tag is not allowed"):
        parse_resource_for_sharing(uri, root)


def test_parse_resource_for_sharing_no_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"URI Scheme not specified"):
        parse_resource_for_sharing("scheme-less/resource", root)


def test_parse_resource_for_sharing_unsupported_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_resource_for_sharing("http://neuromation.io", root)
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_resource_for_sharing("file:///etc/password", root)
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_resource_for_sharing(r"c:scheme-less/resource", root)


def test_parse_resource_for_sharing_user_less(root: Root) -> None:
    user_less_permission = parse_resource_for_sharing("storage:resource", root)
    assert user_less_permission == URL(f"storage://{root.username}/resource")


def test_parse_resource_for_sharing_with_user(root: Root) -> None:
    full_permission = parse_resource_for_sharing(
        f"storage://{root.username}/resource", root
    )
    assert full_permission == URL(f"storage://{root.username}/resource")
    full_permission = parse_resource_for_sharing(f"storage://alice/resource", root)
    assert full_permission == URL(f"storage://alice/resource")


def test_parse_resource_for_sharing_with_tilde(root: Root) -> None:
    parsed = parse_resource_for_sharing(f"storage://~/resource", root)
    assert parsed == URL(f"storage://{root.username}/resource")


def test_parse_resource_for_sharing_with_tilde_relative(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        parse_resource_for_sharing(f"storage:~/resource", root)


def test_parse_permission_action_read_lowercase() -> None:
    action = "read"
    assert parse_permission_action(action) == Action.READ


def test_parse_permission_action_read() -> None:
    action = "READ"
    assert parse_permission_action(action) == Action.READ


def test_parse_permission_action_write_lowercase() -> None:
    action = "write"
    assert parse_permission_action(action) == Action.WRITE


def test_parse_permission_action_write() -> None:
    action = "WRITE"
    assert parse_permission_action(action) == Action.WRITE


def test_parse_permission_action_manage_lowercase() -> None:
    action = "manage"
    assert parse_permission_action(action) == Action.MANAGE


def test_parse_permission_action_manage() -> None:
    action = "MANAGE"
    assert parse_permission_action(action) == Action.MANAGE


def test_parse_permission_action_wrong_string() -> None:
    action = "tosh"
    err = "invalid permission action 'tosh', allowed values: read, write, manage"
    with pytest.raises(ValueError, match=err):
        parse_permission_action(action)


def test_parse_permission_action_wrong_empty() -> None:
    action = ""
    err = "invalid permission action '', allowed values: read, write, manage"
    with pytest.raises(ValueError, match=err):
        parse_permission_action(action)


@pytest.mark.parametrize(
    "arg,val",
    [("1:1", (1, 1)), ("1:10", (1, 10)), ("434:1", (434, 1)), ("0897:123", (897, 123))],
)
def test_local_remote_port_param_type_valid(arg: str, val: Tuple[int, int]) -> None:
    param = LocalRemotePortParamType()
    assert param.convert(arg, None, None) == val


@pytest.mark.parametrize(
    "arg",
    [
        "1:",
        "-123:10",
        "34:-65500",
        "hello:45",
        "5555:world",
        "65536:1",
        "0:0",
        "none",
        "",
    ],
)
def test_local_remote_port_param_type_invalid(arg: str) -> None:
    param = LocalRemotePortParamType()
    with pytest.raises(click.BadParameter, match=".* is not a valid port combination"):
        param.convert(arg, None, None)
