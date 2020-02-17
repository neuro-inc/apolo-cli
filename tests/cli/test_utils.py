from pathlib import Path
from typing import Any, Callable, Dict, NoReturn, Tuple
from unittest import mock

import click
import pytest
from aiohttp import web
from yarl import URL

from neuromation.api import Action, Client
from neuromation.cli.root import Root
from neuromation.cli.utils import (
    LocalRemotePortParamType,
    pager_maybe,
    parse_file_resource,
    parse_permission_action,
    parse_resource_for_sharing,
    resolve_job,
)
from tests import _TestServerFactory


_MakeClient = Callable[..., Client]


def _job_entry(job_id: str) -> Dict[str, Any]:
    return {
        "id": job_id,
        "owner": "job-owner",
        "cluster_name": "default",
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
        "name": "job-name",
        "internal_hostname": "job-id.default",
    }


async def test_resolve_job_id__from_string__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON: Dict[str, Any] = {"jobs": []}
    job_id = "job-81839be3-3ecf-4ec5-80d9-19b1588869db"

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_id:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(job_id, client=client)
        assert resolved == job_id


async def test_resolve_job_id__from_uri_with_owner__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_owner = "job-owner"
    job_name = "job-name"
    uri = f"job://{job_owner}/{job_name}"
    JSON: Dict[str, Any] = {"jobs": []}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != job_owner:
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_name


async def test_resolve_job_id__from_uri_without_owner__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "job-name"
    uri = f"job:{job_name}"
    JSON: Dict[str, Any] = {"jobs": []}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_name


async def test_resolve_job_id__from_string__single_job_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "test-job-name-555"
    job_id = "job-id-1"
    JSON = {"jobs": [_job_entry(job_id)]}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(job_name, client=client)
        assert resolved == job_id


async def test_resolve_job_id__from_uri_with_owner__single_job_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_owner = "job-owner"
    job_name = "job-name"
    uri = f"job://{job_owner}/{job_name}"
    job_id = "job-id-1"
    JSON = {"jobs": [_job_entry(job_id)]}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != job_owner:
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_id


async def test_resolve_job_id__from_uri_without_owner__single_job_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "job-name"
    uri = f"job:{job_name}"
    job_id = "job-id-1"
    JSON = {"jobs": [_job_entry(job_id)]}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_id


async def test_resolve_job_id__from_string__multiple_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "job-name-123-000"
    job_id_1 = "job-id-1"
    job_id_2 = "job-id-2"
    JSON = {"jobs": [_job_entry(job_id_1), _job_entry(job_id_2)]}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(job_name, client=client)
        assert resolved == job_id_2


async def test_resolve_job_id__from_uri_with_owner__multiple_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_owner = "job-owner"
    job_name = "job-name"
    uri = f"job://{job_owner}/{job_name}"
    job_id_1 = "job-id-1"
    job_id_2 = "job-id-2"
    JSON = {"jobs": [_job_entry(job_id_1), _job_entry(job_id_2)]}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != job_owner:
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_id_2


async def test_resolve_job_id__from_uri_without_owner__multiple_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "job-name"
    uri = f"job:{job_name}"
    job_id_1 = "job-id-1"
    job_id_2 = "job-id-2"
    JSON = {"jobs": [_job_entry(job_id_1), _job_entry(job_id_2)]}

    async def handler(request: web.Request) -> web.Response:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_id_2


async def test_resolve_job_id__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_id = "job-81839be3-3ecf-4ec5-80d9-19b1588869db"
    job_name = job_id

    async def handler(request: web.Request) -> NoReturn:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(job_name, client=client)
        assert resolved == job_id


async def test_resolve_job_id__from_uri_with_owner__with_owner__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_owner = "job-owner"
    job_name = "job-name"
    uri = f"job://{job_owner}/{job_name}"

    async def handler(request: web.Request) -> NoReturn:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != job_owner:
            pytest.fail(f"received: {owner}")
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_name


async def test_resolve_job_id__from_uri_without_owner__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "job-name"
    uri = f"job:{job_name}"

    async def handler(request: web.Request) -> NoReturn:
        # Since `resolve_job` excepts any Exception, `assert` will be caught there
        name = request.query.get("name")
        if name != job_name:
            pytest.fail(f"received: {name}")
        owner = request.query.get("owner")
        if owner != "user":
            pytest.fail(f"received: {owner}")
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client)
        assert resolved == job_name


async def test_resolve_job_id__from_uri__missing_job_id(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:

    uri = "job://job-name"

    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(
            ValueError,
            match="Invalid job URI: owner='job-name', missing job-id or job-name",
        ):
            await resolve_job(uri, client=client)


def test_parse_file_resource_no_scheme(root: Root) -> None:
    parsed = parse_file_resource("scheme-less/resource", root)
    assert parsed == URL((Path.cwd() / "scheme-less/resource").as_uri())
    parsed = parse_file_resource("c:scheme-less/resource", root)
    assert parsed == URL((Path("c:scheme-less").resolve() / "resource").as_uri())


def test_parse_file_resource_unsupported_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_file_resource("http://neuromation.io", root)
    with pytest.raises(ValueError, match=r"Unsupported URI scheme"):
        parse_file_resource("image:ubuntu", root)


def test_parse_file_resource_user_less(root: Root) -> None:
    user_less_permission = parse_file_resource("storage:resource", root)
    assert user_less_permission == URL(f"storage://{root.client.username}/resource")


def test_parse_file_resource_with_user(root: Root) -> None:
    full_permission = parse_file_resource(
        f"storage://{root.client.username}/resource", root
    )
    assert full_permission == URL(f"storage://{root.client.username}/resource")
    full_permission = parse_file_resource(f"storage://alice/resource", root)
    assert full_permission == URL(f"storage://alice/resource")


def test_parse_file_resource_with_tilde(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        parse_file_resource(f"storage://~/resource", root)


def test_parse_resource_for_sharing_image_no_tag(root: Root) -> None:
    uri = "image:ubuntu"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(f"image://{root.client.username}/ubuntu")


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
    assert user_less_permission == URL(f"storage://{root.client.username}/resource")


def test_parse_resource_for_sharing_with_user(root: Root) -> None:
    full_permission = parse_resource_for_sharing(
        f"storage://{root.client.username}/resource", root
    )
    assert full_permission == URL(f"storage://{root.client.username}/resource")
    full_permission = parse_resource_for_sharing(f"storage://alice/resource", root)
    assert full_permission == URL(f"storage://alice/resource")


def test_parse_resource_for_sharing_with_tilde(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        parse_resource_for_sharing(f"storage://~/resource", root)


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


def test_pager_maybe_no_tty() -> None:
    with mock.patch.multiple(
        "click", echo=mock.DEFAULT, echo_via_pager=mock.DEFAULT
    ) as mocked:
        mock_echo = mocked["echo"]
        mock_echo_via_pager = mocked["echo_via_pager"]

        terminal_size = (100, 10)
        tty = False
        large_input = [f"line {x}" for x in range(20)]

        pager_maybe(large_input, tty, terminal_size)
        assert mock_echo.call_args_list == [mock.call(x) for x in large_input]
        mock_echo_via_pager.assert_not_called()


def test_pager_maybe_terminal_larger() -> None:
    with mock.patch.multiple(
        "click", echo=mock.DEFAULT, echo_via_pager=mock.DEFAULT
    ) as mocked:
        mock_echo = mocked["echo"]
        mock_echo_via_pager = mocked["echo_via_pager"]

        terminal_size = (100, 10)
        tty = True
        small_input = ["line 1", "line 2"]

        pager_maybe(small_input, tty, terminal_size)
        assert mock_echo.call_args_list == [mock.call(x) for x in small_input]
        mock_echo_via_pager.assert_not_called()


def test_pager_maybe_terminal_smaller() -> None:
    with mock.patch.multiple(
        "click", echo=mock.DEFAULT, echo_via_pager=mock.DEFAULT
    ) as mocked:
        mock_echo = mocked["echo"]
        mock_echo_via_pager = mocked["echo_via_pager"]

        terminal_size = (100, 10)
        tty = True
        large_input = [f"line {x}" for x in range(20)]

        pager_maybe(large_input, tty, terminal_size)
        mock_echo.assert_not_called()
        mock_echo_via_pager.assert_called_once()
        lines_it = mock_echo_via_pager.call_args[0][0]
        assert "".join(lines_it) == "\n".join(large_input)

        # Do the same, but call with a generator function for input instead
        mock_echo_via_pager.reset_mock()
        iter_input = iter(large_input)
        next(iter_input)  # Skip first line

        pager_maybe(iter_input, tty, terminal_size)
        mock_echo.assert_not_called()
        mock_echo_via_pager.assert_called_once()
        lines_it = mock_echo_via_pager.call_args[0][0]
        assert "".join(lines_it) == "\n".join(large_input[1:])
