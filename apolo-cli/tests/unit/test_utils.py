from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn, cast
from unittest import mock

import click
import pytest
import toml
from aiohttp import web
from yarl import URL

from apolo_sdk import Action, Client, JobStatus, PluginManager

from apolo_cli.parse_utils import parse_timedelta
from apolo_cli.root import Root
from apolo_cli.utils import (
    calc_life_span,
    pager_maybe,
    parse_file_resource,
    parse_permission_action,
    parse_resource_for_sharing,
    resolve_job,
    resolve_job_ex,
)

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


def _job_entry(
    job_id: str,
    cluster_name: str = "default",
    owner: str = "user",
    project_name: str = "project",
    org_name: str = "org",
) -> dict[str, Any]:
    uri = f"job://{cluster_name}/{org_name}/{project_name}/{job_id}"
    return {
        "id": job_id,
        "owner": owner,
        "cluster_name": cluster_name,
        "org_name": org_name,
        "project_name": project_name,
        "uri": uri,
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
            "resources": {"cpu": 0.1, "memory": 2**30, "shm": True},
        },
        "ssh_auth_server": "ssh://nobody@ssh-auth-api.dev.apolo.us:22",
        "scheduler_enabled": True,
        "pass_config": False,
        "name": "my-job-name",
        "internal_hostname": f"{job_id}.{cluster_name}",
        "internal_hostname_named": f"my-job-name--{project_name}.{cluster_name}",
        "total_price_credits": "150",
        "price_credits_per_hour": "15",
    }


def _check_params(request: web.Request, **expected: str | list[str] | set[str]) -> None:
    # Since `resolve_job` excepts any Exception, `assert` will be caught there
    for key, value in expected.items():
        got: list[str] | set[str] = request.query.getall(key)
        if isinstance(value, set):
            got = set(got)
        elif not isinstance(value, list):
            value = [value]
        if got != value:
            print(f"received: {key}={got!r} (expected {value!r})")
            pytest.fail(f"received: {key}={got!r} (expected {value!r})")


async def test_resolve_job_id__from_string__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON: dict[str, Any] = {"jobs": []}
    job_id = "job-81839be3-3ecf-4ec5-80d9-19b1588869db"

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_id,
            project_name="test-project",
            cluster_name="default",
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(job_id, client=client, status={JobStatus.RUNNING})
        assert resolved == job_id
        resolved_ex = await resolve_job_ex(
            job_id, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_id, "default")


@pytest.mark.parametrize("cluster_name", ["default", "other"])
async def test_resolve_job_id__from_uri_with_same_project__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient, cluster_name: str
) -> None:
    job_project = "test-project"
    job_name = "my-job-name"
    uri = f"job://{cluster_name}/{job_project}/{job_name}"
    JSON: dict[str, Any] = {"jobs": []}

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name=job_project,
            cluster_name=cluster_name,
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_name
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_name, cluster_name)

    await srv.close()


async def test_resolve_job_id__from_uri_with_other_project__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_project = "other-test-project"
    job_name = "my-job-name"
    uri = f"job://default/{job_project}/{job_name}"
    JSON: dict[str, Any] = {"jobs": []}

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name=job_project,
            cluster_name="default",
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ValueError):
            await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        with pytest.raises(ValueError):
            await resolve_job_ex(uri, client=client, status={JobStatus.RUNNING})

    await srv.close()


async def test_resolve_job_id__from_uri_without_project__no_jobs_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "my-job-name"
    uri = f"job:{job_name}"
    JSON: dict[str, Any] = {"jobs": []}

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name="test-project",
            cluster_name="default",
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_name
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_name, "default")

    await srv.close()


async def test_resolve_job_id__from_string__single_job_found(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "test-job-name-555"
    job_id = "job-id-1"
    JSON = {"jobs": [_job_entry(job_id, project_name="test-project", org_name="org")]}

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            org_name="org",
            project_name="test-project",
            cluster_name="default",
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(
            job_name, client=client, status={JobStatus.RUNNING}
        )
        assert resolved == job_id
        resolved_ex = await resolve_job_ex(
            job_name, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_id, "default")

    await srv.close()


@pytest.mark.parametrize("cluster_name", ["default", "other"])
@pytest.mark.parametrize("org_name", ["org", "test-org"])
async def test_resolve_job_id__from_uri_with_same_project__single_job_found(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_name: str,
    org_name: str,
) -> None:
    job_project = "test-project"
    job_name = "my-job-name"
    uri = f"job://{cluster_name}/{job_project}/{job_name}"
    job_id = "job-id-1"
    JSON = {
        "jobs": [
            _job_entry(
                job_id,
                cluster_name=cluster_name,
                project_name=job_project,
                org_name=org_name,
            )
        ]
    }

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name=job_project,
            cluster_name=cluster_name,
            reverse="1",
            org_name=org_name,
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), org_name=org_name) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_id
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_id, cluster_name)

    await srv.close()


@pytest.mark.parametrize("cluster_name", ["default", "other"])
@pytest.mark.parametrize("org_name", [None, "test-org", "job-org"])
async def test_resolve_job_id__from_uri_with_org__single_job_found(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_name: str,
    org_name: str | None,
) -> None:
    job_org = "job-org"
    job_project = "test-project"
    job_name = "my-job-name"
    uri = f"job://{cluster_name}/{job_org}/{job_project}/{job_name}"
    job_id = "job-id-1"
    JSON = {
        "jobs": [
            _job_entry(
                job_id,
                cluster_name=cluster_name,
                org_name=job_org,
                project_name=job_project,
            )
        ]
    }

    async def handler(request: web.Request) -> web.Response:
        expected_projects = (
            [f"{job_org}/{job_project}", job_project]
            if org_name != job_org
            else [job_project]
        )
        _check_params(
            request,
            name=job_name,
            project_name=expected_projects,
            cluster_name=cluster_name,
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), org_name=org_name) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_id
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_id, cluster_name)

    await srv.close()


@pytest.mark.parametrize("cluster_name", ["default", "other"])
@pytest.mark.parametrize("org_name", ["org", "test-org"])
async def test_resolve_job_id__from_uri__multiple_jobs_found(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_name: str,
    org_name: str,
) -> None:
    job_org = "job-org"
    job_project = "test-project"
    job_name = "my-job-name"
    uri = f"job://{cluster_name}/{job_project}/{job_name}"
    job_ids = [f"job-id-{i}" for i in range(4)]
    JSON = {
        "jobs": [
            _job_entry(
                job_ids[0],
                cluster_name=cluster_name,
                project_name=job_project,
                org_name="other-org",
            ),
            _job_entry(
                job_ids[1],
                cluster_name=cluster_name,
                project_name=job_project,
                org_name=job_org,
            ),
            _job_entry(
                job_ids[2],
                cluster_name=cluster_name,
                project_name=job_project,
                org_name=org_name,
            ),
            _job_entry(
                job_ids[3],
                cluster_name=cluster_name,
                org_name="other-org",
                project_name=job_project,
            ),
        ]
    }

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name=job_project,
            cluster_name=cluster_name,
            reverse="1",
            org_name=org_name,
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), org_name=org_name) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_ids[2]
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_ids[2], cluster_name)

    await srv.close()


@pytest.mark.parametrize("cluster_name", ["default", "other"])
@pytest.mark.parametrize("org_name", ["org", "test-org"])
async def test_resolve_job_id__from_uri_with_org__multiple_jobs_found(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    cluster_name: str,
    org_name: str,
) -> None:
    job_org = "job-org"
    job_project = "test-project"
    job_name = "my-job-name"
    uri = f"job://{cluster_name}/{job_org}/{job_project}/{job_name}"
    job_ids = [f"job-id-{i}" for i in range(4)]
    JSON = {
        "jobs": [
            _job_entry(
                job_ids[0],
                cluster_name=cluster_name,
                project_name=job_project,
                org_name="other-org",
            ),
            _job_entry(job_ids[1], cluster_name=cluster_name, project_name=job_project),
            _job_entry(
                job_ids[2],
                cluster_name=cluster_name,
                project_name=job_project,
                org_name=job_org,
            ),
            _job_entry(
                job_ids[3],
                cluster_name=cluster_name,
                project_name=job_project,
                org_name="other-org",
            ),
        ]
    }

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name=[f"{job_org}/{job_project}", job_project],
            cluster_name=cluster_name,
            reverse="1",
            org_name=org_name,
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), org_name=org_name) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_ids[2]
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_ids[2], cluster_name)

    await srv.close()


@pytest.mark.parametrize("org_name", ["org", "test-org"])
async def test_resolve_job_id__from_uri_without_project__single_job_found(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    org_name: str,
) -> None:
    job_name = "my-job-name"
    uri = f"job:{job_name}"
    job_id = "job-id-1"
    JSON = {
        "jobs": [_job_entry(job_id, project_name="test-project", org_name=org_name)]
    }

    async def handler(request: web.Request) -> web.Response:
        _check_params(
            request,
            name=job_name,
            project_name="test-project",
            cluster_name="default",
            reverse="1",
        )
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), org_name=org_name) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_id
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_id, "default")

    await srv.close()


async def test_resolve_job_id__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_id = "job-81839be3-3ecf-4ec5-80d9-19b1588869db"
    job_name = job_id

    async def handler(request: web.Request) -> NoReturn:
        _check_params(
            request,
            name=job_name,
            project_name="test-project",
            cluster_name="default",
            reverse="1",
        )
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(
            job_name, client=client, status={JobStatus.RUNNING}
        )
        assert resolved == job_id
        resolved_ex = await resolve_job_ex(
            job_name, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_id, "default")

    await srv.close()


@pytest.mark.parametrize("cluster_name", ["default", "other"])
async def test_resolve_job_id__from_uri_with_same_project__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient, cluster_name: str
) -> None:
    job_project = "test-project"
    job_name = "my-job-name"
    uri = f"job://{cluster_name}/{job_project}/{job_name}"

    async def handler(request: web.Request) -> NoReturn:
        _check_params(
            request,
            name=job_name,
            project_name=job_project,
            cluster_name=cluster_name,
            reverse="1",
        )
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_name
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_name, cluster_name)

    await srv.close()


async def test_resolve_job_id__from_uri_with_other_project__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_project = "other-test-project"
    job_name = "my-job-name"
    uri = f"job://default/{job_project}/{job_name}"

    async def handler(request: web.Request) -> NoReturn:
        _check_params(
            request,
            name=job_name,
            project_name=job_project,
            cluster_name="default",
            reverse="1",
        )
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ValueError):
            await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        with pytest.raises(ValueError):
            await resolve_job_ex(uri, client=client, status={JobStatus.RUNNING})

    await srv.close()


async def test_resolve_job_id__from_uri_without_project__server_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    job_name = "my-job-name"
    uri = f"job:{job_name}"

    async def handler(request: web.Request) -> NoReturn:
        _check_params(
            request,
            name=job_name,
            project_name="test-project",
            cluster_name="default",
            reverse="1",
        )
        raise web.HTTPError()

    app = web.Application()
    app.router.add_get("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resolved = await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        assert resolved == job_name
        resolved_ex = await resolve_job_ex(
            uri, client=client, status={JobStatus.RUNNING}
        )
        assert resolved_ex == (job_name, "default")

    await srv.close()


@pytest.mark.parametrize(
    "uri",
    [
        # "job:",
        "job:/",
        # "job://",
        "job:///",
        "job://default",
        "job://default/",
        # "job://default/user",
        # "job://default/user/",
        # "job://default/user/name/",
        "job://default/org/user/name/",
        # "job:/user",
        # "job:/user/",
        "job:/user/name/",
        "job:name/",
    ],
)
async def test_resolve_job_id__from_uri__invalid(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient, uri: str
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ValueError, match="Invalid job URI: job:"):
            await resolve_job(uri, client=client, status={JobStatus.RUNNING})
        with pytest.raises(ValueError, match="Invalid job URI: job:"):
            await resolve_job_ex(uri, client=client, status={JobStatus.RUNNING})


def test_parse_file_resource_no_scheme(root: Root) -> None:
    parsed = parse_file_resource("scheme-less/resource", root)
    assert parsed == URL((Path.cwd() / "scheme-less/resource").as_uri())
    parsed = parse_file_resource("C:scheme-less/resource", root)
    assert parsed == URL((Path("C:scheme-less").resolve() / "resource").as_uri())


def test_parse_file_resource_unsupported_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Invalid scheme"):
        parse_file_resource("http://neu.ro", root)
    with pytest.raises(ValueError, match=r"Invalid scheme"):
        parse_file_resource("image:ubuntu", root)


def test_parse_file_resource_project_less(root: Root) -> None:
    user_less_permission = parse_file_resource("storage:resource", root)
    assert user_less_permission == URL(
        f"storage://{root.client.cluster_name}"
        f"/org/{root.client.config.project_name}/resource"
    )


def test_parse_file_resource_with_project(root: Root) -> None:
    full_permission = parse_file_resource(
        f"storage://{root.client.cluster_name}"
        f"/{root.client.config.project_name}/resource",
        root,
    )
    assert full_permission == URL(
        f"storage://{root.client.cluster_name}"
        f"/{root.client.config.project_name}/resource"
    )
    full_permission = parse_file_resource(f"storage://default/alice/resource", root)
    assert full_permission == URL(f"storage://default/alice/resource")


def test_parse_file_resource_with_tilde(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        parse_file_resource(f"storage://~/resource", root)


def test_parse_resource_for_sharing_image_no_tag(root: Root) -> None:
    uri = "image:ubuntu"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(
        f"image://{root.client.cluster_name}"
        f"/org/{root.client.config.project_name}/ubuntu"
    )


def test_parse_resource_for_sharing_image_non_ascii(root: Root) -> None:
    uri = "image:образ"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(
        f"image://{root.client.cluster_name}"
        f"/org/{root.client.config.project_name}/образ"
    )
    assert parsed.path == f"/org/{root.client.config.project_name}/образ"


def test_parse_resource_for_sharing_image_percent_encoded(root: Root) -> None:
    uri = "image:%252d%3f%23"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(
        f"image://{root.client.cluster_name}"
        f"/org/{root.client.config.project_name}/%252d%3f%23"
    )
    assert parsed.path == f"/org/{root.client.config.project_name}/%2d?#"


def test_parse_resource_for_sharing_image_with_tag_fail(root: Root) -> None:
    uri = "image:ubuntu:latest"
    with pytest.raises(ValueError, match="tag is not allowed"):
        parse_resource_for_sharing(uri, root)


def test_parse_resource_for_sharing_all_project_images(root: Root) -> None:
    uri = "image:/otherproject"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(f"image://{root.client.cluster_name}/org/otherproject")


def _test_parse_resource_for_sharing_all_cluster_images(root: Root) -> None:
    uri = "image://"
    parsed = parse_resource_for_sharing(uri, root)
    assert parsed == URL(f"image://{root.client.cluster_name}/otheruser")


def test_parse_resource_for_sharing_no_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"URI Scheme not specified"):
        parse_resource_for_sharing("scheme-less/resource", root)


def test_parse_resource_for_sharing_unsupported_scheme(root: Root) -> None:
    with pytest.raises(ValueError, match=r"Invalid scheme"):
        parse_resource_for_sharing("http://neu.ro", root)
    with pytest.raises(ValueError, match=r"Invalid scheme"):
        parse_resource_for_sharing("file:///etc/password", root)
    with pytest.raises(ValueError, match=r"Invalid scheme"):
        parse_resource_for_sharing(r"c:scheme-less/resource", root)


def test_parse_resource_for_sharing_user_less(root: Root) -> None:
    user_less_permission = parse_resource_for_sharing("storage:resource", root)
    assert user_less_permission == URL(
        f"storage://{root.client.cluster_name}"
        f"/org/{root.client.config.project_name}/resource"
    )


def test_parse_resource_for_sharing_with_project(root: Root) -> None:
    full_permission = parse_resource_for_sharing(
        f"storage://{root.client.cluster_name}"
        f"/{root.client.config.project_name}/resource",
        root,
    )
    assert full_permission == URL(
        f"storage://{root.client.cluster_name}"
        f"/{root.client.config.project_name}/resource"
    )
    full_permission = parse_resource_for_sharing(
        f"storage://default/alice/resource", root
    )
    assert full_permission == URL(f"storage://default/alice/resource")


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


async def test_calc_life_span_none_default(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "life-span")

    async with make_client(
        "https://example.com", plugin_manager=plugin_manager
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"life-span": "1d2h3m4s"}}))
        expected = timedelta(days=1, hours=2, minutes=3, seconds=4)
        assert (
            await calc_life_span(client, None, "1d", "job") == expected.total_seconds()
        )


async def test_calc_life_span_default_life_span_all_keys(
    caplog: Any, monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "life-span")

    async with make_client(
        "https://example.com", plugin_manager=plugin_manager
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text(toml.dumps({"job": {"life-span": "1d2h3m4s"}}))

        expected = timedelta(days=1, hours=2, minutes=3, seconds=4)
        assert (
            await calc_life_span(client, None, "1d", "job") == expected.total_seconds()
        )


async def test_calc_default_life_span_invalid(
    caplog: Any,
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "life-span")

    async with make_client(
        "https://example.com", plugin_manager=plugin_manager
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text(toml.dumps({"job": {"life-span": "invalid"}}))
        with pytest.raises(
            click.UsageError,
            match="Could not parse time delta",
        ):
            await calc_life_span(client, None, "1d", "job")


async def test_calc_default_life_span_default_value(
    caplog: Any,
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
) -> None:
    async with make_client("https://example.com") as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text(toml.dumps(cast(dict[str, Any], {})))
        default = parse_timedelta("1d")
        assert (
            await calc_life_span(client, None, "1d", "job") == default.total_seconds()
        )
