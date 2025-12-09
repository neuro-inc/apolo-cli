import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from aiodocker.exceptions import DockerError
from aiohttp import web
from dateutil.parser import isoparse
from yarl import URL

from apolo_sdk import (
    Client,
    Container,
    DiskVolume,
    HTTPPort,
    JobPriority,
    JobRestartPolicy,
    JobStatus,
    JobTelemetry,
    RemoteImage,
    ResourceNotFound,
    Resources,
    SecretFile,
    Volume,
)
from apolo_sdk._jobs import INVALID_IMAGE_NAME, _calc_status, _job_description_from_api

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


def test_resources_default() -> None:
    resources = Resources(16 * 2**20, 0.5)
    assert resources.memory == 16 * 2**20
    assert resources.memory_mb == 16
    assert resources.cpu == 0.5
    assert resources.nvidia_gpu is None
    assert resources.amd_gpu is None
    assert resources.intel_gpu is None
    assert resources.nvidia_gpu_model is None
    assert resources.amd_gpu_model is None
    assert resources.intel_gpu_model is None
    assert resources.shm is True
    assert resources.tpu_type is None
    assert resources.tpu_software_version is None


async def test_jobs_monitor(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def log_stream(request: web.Request) -> web.StreamResponse:
        assert "since" not in request.query
        assert request.query.get("timestamps", "false") == "false"
        resp = web.WebSocketResponse()
        await resp.prepare(request)
        for i in range(10):
            await resp.send_bytes(b"chunk " + str(i).encode("ascii") + b"\n")
        return resp

    app = web.Application()
    app.router.add_get("/jobs/job-id/log_ws", log_stream)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.monitor("job-id") as it:
            async for data in it:
                lst.append(data)

    assert b"".join(lst) == b"".join(
        [
            b"chunk 0\n",
            b"chunk 1\n",
            b"chunk 2\n",
            b"chunk 3\n",
            b"chunk 4\n",
            b"chunk 5\n",
            b"chunk 6\n",
            b"chunk 7\n",
            b"chunk 8\n",
            b"chunk 9\n",
        ]
    )


async def test_jobs_monitor_since(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def log_stream(request: web.Request) -> web.StreamResponse:
        assert request.query["since"] == "2021-08-17T00:00:00+00:00"
        assert request.query.get("timestamps", "false") == "false"
        resp = web.WebSocketResponse()
        await resp.prepare(request)
        for i in range(5, 10):
            await resp.send_bytes(b"chunk " + str(i).encode("ascii") + b"\n")
        return resp

    app = web.Application()
    app.router.add_get("/jobs/job-id/log_ws", log_stream)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.monitor(
            "job-id", since=datetime(2021, 8, 17, tzinfo=timezone.utc)
        ) as it:
            async for data in it:
                lst.append(data)

    assert b"".join(lst) == b"".join(
        [
            b"chunk 5\n",
            b"chunk 6\n",
            b"chunk 7\n",
            b"chunk 8\n",
            b"chunk 9\n",
        ]
    )


async def test_jobs_monitor_timestamps(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def log_stream(request: web.Request) -> web.StreamResponse:
        assert "since" not in request.query
        assert request.query["timestamps"] == "true"
        resp = web.WebSocketResponse()
        await resp.prepare(request)
        for i in range(10):
            await resp.send_bytes(
                f"2021-08-13T09:23:{i:02}.123456789Z chunk {i}\n".encode()
            )
        return resp

    app = web.Application()
    app.router.add_get("/jobs/job-id/log_ws", log_stream)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.monitor("job-id", timestamps=True) as it:
            async for data in it:
                lst.append(data)

    assert b"".join(lst) == b"".join(
        [
            b"2021-08-13T09:23:00.123456789Z chunk 0\n",
            b"2021-08-13T09:23:01.123456789Z chunk 1\n",
            b"2021-08-13T09:23:02.123456789Z chunk 2\n",
            b"2021-08-13T09:23:03.123456789Z chunk 3\n",
            b"2021-08-13T09:23:04.123456789Z chunk 4\n",
            b"2021-08-13T09:23:05.123456789Z chunk 5\n",
            b"2021-08-13T09:23:06.123456789Z chunk 6\n",
            b"2021-08-13T09:23:07.123456789Z chunk 7\n",
            b"2021-08-13T09:23:08.123456789Z chunk 8\n",
            b"2021-08-13T09:23:09.123456789Z chunk 9\n",
        ]
    )


async def test_monitor_notexistent_job(
    aiohttp_server: Any, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        raise web.HTTPNotFound()

    app = web.Application()
    app.router.add_get("/jobs/job-id/log", handler)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ResourceNotFound):
            async with client.jobs.monitor("job-id") as it:
                async for data in it:
                    lst.append(data)
    assert lst == []


async def test_job_top(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    def get_data_chunk(index: int) -> dict[str, Any]:
        return {
            "cpu": 0.5,
            "memory_bytes": 50 * 2**20,
            "timestamp": index,
            "gpu_duty_cycle": 50,
            "gpu_memory_bytes": int(55.6 * 2**20),
        }

    def get_job_telemetry(index: int) -> JobTelemetry:
        return JobTelemetry(
            cpu=0.5,
            memory_bytes=50 * 2**20,
            timestamp=index,
            gpu_duty_cycle=50,
            gpu_memory_bytes=int(55.6 * 2**20),
        )

    async def top_stream(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        for i in range(10):
            await ws.send_json(get_data_chunk(i))

        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/jobs/job-id/top", top_stream)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.top("job-id") as it:
            async for data in it:
                lst.append(data)

    assert lst == [get_job_telemetry(i) for i in range(10)]


async def test_top_finished_job(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/jobs/job-id/top", handler)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ValueError, match="not running"):
            async with client.jobs.top("job-id") as it:
                async for data in it:
                    lst.append(data)
    assert lst == []


async def test_top_nonexisting_job(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        raise web.HTTPBadRequest(headers={"X-Error": "job job-id not found"})

    app = web.Application()
    app.router.add_get("/jobs/job-id/top", handler)

    srv = await aiohttp_server(app)

    lst = []
    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ValueError, match="not found"):
            async with client.jobs.top("job-id") as it:
                async for data in it:
                    lst.append(data)
    assert lst == []


async def test_kill_not_found_error(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        raise web.HTTPNotFound()

    app = web.Application()
    app.router.add_delete("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(ResourceNotFound):
            await client.jobs.kill("job-id")


async def test_kill_ok(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        raise web.HTTPNoContent()

    app = web.Application()
    app.router.add_delete("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.jobs.kill("job-id")


async def test_save_image_not_in_platform_registry(make_client: _MakeClient) -> None:
    async with make_client("http://whatever") as client:
        image = RemoteImage.new_external_image(name="ubuntu")
        with pytest.raises(ValueError, match="must be in the platform registry"):
            await client.jobs.save("job-id", image)


async def test_save_ok(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = [
        {
            "status": "CommitStarted",
            "details": {"container": "cont_id", "image": f"ubuntu:latest"},
        },
        {"status": "CommitFinished"},
        {"status": "The push refers to repository [localhost:5000/alpine]"},
        {"status": "Preparing", "progressDetail": {}, "id": "a31dbd3063d7"},
        {
            "status": "Pushing",
            "progressDetail": {"current": 3584},
            "progress": " 3.584kB",
            "id": "0acd017a4b67",
        },
        {"status": "Pushed", "progressDetail": {}, "id": "0acd017a4b67"},
        {"status": "job-id: digest: sha256:DIGEST size: 1359"},
        {
            "progressDetail": {},
            "aux": {"Tag": "job-id", "Digest": "sha256:DIGEST", "Size": 1359},
        },
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        encoding = "utf-8"
        response = web.StreamResponse(status=200)
        response.enable_compression(web.ContentCoding.identity)
        response.content_type = "application/x-ndjson"
        response.charset = encoding
        await response.prepare(request)
        for chunk in JSON:
            chunk_str = json.dumps(chunk) + "\r\n"
            await response.write(chunk_str.encode(encoding))
        return response

    app = web.Application()
    app.router.add_post("/jobs/job-id/save", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        image = RemoteImage.new_platform_image(
            registry="gcr.io",
            cluster_name="test-cluster",
            name="img",
            org_name=None,
            project_name="test-project",
        )
        await client.jobs.save("job-id", image)


async def test_save_commit_started_invalid_status_fails(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    invalid = "invalid status"
    JSON = [
        {"status": invalid, "details": {"container": "cnt", "image": "img"}},
        {"status": "CommitFinished"},
        {"status": "The push refers to repository [localhost:5000/alpine]"},
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        encoding = "utf-8"
        response = web.StreamResponse(status=200)
        response.enable_compression(web.ContentCoding.identity)
        response.content_type = "application/x-ndjson"
        response.charset = encoding
        await response.prepare(request)
        for chunk in JSON:
            chunk_str = json.dumps(chunk) + "\r\n"
            await response.write(chunk_str.encode(encoding))
        return response

    app = web.Application()
    app.router.add_post("/jobs/job-id/save", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        image = RemoteImage.new_platform_image(
            registry="gcr.io",
            cluster_name="test-cluster",
            name="img",
            org_name=None,
            project_name="test-project",
        )
        with pytest.raises(
            DockerError,
            match=f"Invalid commit status: '{invalid}', expecting: 'CommitStarted'",
        ):
            await client.jobs.save("job-id", image)


async def test_save_commit_started_missing_image_details_fails(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = [
        {"status": "CommitStarted", "details": {"container": "cnt"}},
        {"status": "CommitFinished"},
        {"status": "The push refers to repository [localhost:5000/alpine]"},
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        encoding = "utf-8"
        response = web.StreamResponse(status=200)
        response.enable_compression(web.ContentCoding.identity)
        response.content_type = "application/x-ndjson"
        response.charset = encoding
        await response.prepare(request)
        for chunk in JSON:
            chunk_str = json.dumps(chunk) + "\r\n"
            await response.write(chunk_str.encode(encoding))
        return response

    app = web.Application()
    app.router.add_post("/jobs/job-id/save", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        image = RemoteImage.new_platform_image(
            registry="gcr.io",
            cluster_name="test-cluster",
            name="img",
            org_name=None,
            project_name="test-project",
        )
        with pytest.raises(DockerError, match="Missing required details: 'image'"):
            await client.jobs.save("job-id", image)


async def test_save_commit_finished_invalid_status_fails(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    invalid = "invalid status"
    JSON = [
        {"status": "CommitStarted", "details": {"container": "cnt", "image": "img"}},
        {"status": invalid},
        {"status": "The push refers to repository [localhost:5000/alpine]"},
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        encoding = "utf-8"
        response = web.StreamResponse(status=200)
        response.enable_compression(web.ContentCoding.identity)
        response.content_type = "application/x-ndjson"
        response.charset = encoding
        await response.prepare(request)
        for chunk in JSON:
            chunk_str = json.dumps(chunk) + "\r\n"
            await response.write(chunk_str.encode(encoding))
        return response

    app = web.Application()
    app.router.add_post("/jobs/job-id/save", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        image = RemoteImage.new_platform_image(
            registry="gcr.io",
            cluster_name="test-cluster",
            name="img",
            org_name=None,
            project_name="test-project",
        )
        with pytest.raises(
            DockerError,
            match=(f"Invalid commit status: '{invalid}', expecting: 'CommitFinished'"),
        ):
            await client.jobs.save("job-id", image)


async def test_save_commit_started_missing_status_fails(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = [
        {"not-a-status": "value"},
        {"status": "CommitFinished"},
        {"status": "The push refers to repository [localhost:5000/alpine]"},
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        encoding = "utf-8"
        response = web.StreamResponse(status=200)
        response.enable_compression(web.ContentCoding.identity)
        response.content_type = "application/x-ndjson"
        response.charset = encoding
        await response.prepare(request)
        for chunk in JSON:
            chunk_str = json.dumps(chunk) + "\r\n"
            await response.write(chunk_str.encode(encoding))
        return response

    app = web.Application()
    app.router.add_post("/jobs/job-id/save", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        image = RemoteImage.new_platform_image(
            registry="gcr.io",
            cluster_name="test-cluster",
            name="img",
            org_name=None,
            project_name="test-project",
        )
        with pytest.raises(DockerError, match='Missing required field: "status"'):
            await client.jobs.save("job-id", image)


async def test_save_commit_finished_missing_status_fails(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = [
        {"status": "CommitStarted", "details": {"container": "cnt", "image": "img"}},
        {"not-a-status": "value"},
        {"status": "The push refers to repository [localhost:5000/alpine]"},
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        encoding = "utf-8"
        response = web.StreamResponse(status=200)
        response.enable_compression(web.ContentCoding.identity)
        response.content_type = "application/x-ndjson"
        response.charset = encoding
        await response.prepare(request)
        for chunk in JSON:
            chunk_str = json.dumps(chunk) + "\r\n"
            await response.write(chunk_str.encode(encoding))
        return response

    app = web.Application()
    app.router.add_post("/jobs/job-id/save", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        image = RemoteImage.new_platform_image(
            registry="gcr.io",
            cluster_name="test-cluster",
            name="img",
            org_name=None,
            project_name="test-project",
        )
        with pytest.raises(DockerError, match='Missing required field: "status"'):
            await client.jobs.save("job-id", image)


async def test_status_failed(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "status": "failed",
        "id": "job-id",
        "description": "This is job description, not a history description",
        "http_url": "http://my_host:8889",
        "history": {
            "created_at": "2018-08-29T12:23:13.981621+00:00",
            "started_at": "2018-08-29T12:23:15.988054+00:00",
            "finished_at": "2018-08-29T12:59:31.427795+00:00",
            "reason": "ContainerCannotRun",
            "description": "Not enough coffee",
        },
        "scheduler_enabled": True,
        "preemptible_node": True,
        "pass_config": False,
        "owner": "owner",
        "cluster_name": "default",
        "uri": "job://default/owner/job-id",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "submit-image-name",
            "command": "submit-command",
            "http": {"port": 8181},
            "resources": {
                "memory": 4096 * 2**20,
                "cpu": 7.0,
                "shm": True,
                "nvidia_gpu": 1,
            },
            "volumes": [
                {
                    "src_storage_uri": "storage://test-user/path_read_only",
                    "dst_path": "/container/read_only",
                    "read_only": True,
                },
                {
                    "src_storage_uri": "storage://test-user/path_read_write",
                    "dst_path": "/container/path_read_write",
                    "read_only": False,
                },
            ],
        },
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.status("job-id")

        assert ret == _job_description_from_api(JSON, client.parse)
        assert ret.preemptible_node


async def test_status_being_dropped(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "status": "failed",
        "id": "job-id",
        "description": "This is job description, not a history description",
        "http_url": "http://my_host:8889",
        "history": {
            "created_at": "2018-08-29T12:23:13.981621+00:00",
            "started_at": "2018-08-29T12:23:15.988054+00:00",
            "finished_at": "2018-08-29T12:59:31.427795+00:00",
            "reason": "ContainerCannotRun",
            "description": "Not enough coffee",
        },
        "scheduler_enabled": True,
        "preemptible_node": True,
        "pass_config": False,
        "being_dropped": True,
        "logs_removed": True,
        "owner": "owner",
        "cluster_name": "default",
        "uri": "job://default/owner/job-id",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "submit-image-name",
            "command": "submit-command",
            "http": {"port": 8181},
            "resources": {
                "memory": 4096 * 2**20,
                "cpu": 7.0,
                "shm": True,
                "nvidia_gpu": 1,
            },
            "volumes": [
                {
                    "src_storage_uri": "storage://test-user/path_read_only",
                    "dst_path": "/container/read_only",
                    "read_only": True,
                },
                {
                    "src_storage_uri": "storage://test-user/path_read_write",
                    "dst_path": "/container/path_read_write",
                    "read_only": False,
                },
            ],
        },
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.status("job-id")

        assert ret == _job_description_from_api(JSON, client.parse)
        assert ret._internal.being_dropped
        assert ret._internal.logs_removed


async def test_status_with_http(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "status": "running",
        "id": "job-id",
        "description": "This is job description, not a history description",
        "http_url": "http://my_host:8889",
        "history": {
            "created_at": "2018-08-29T12:23:13.981621+00:00",
            "started_at": "2018-08-29T12:23:15.988054+00:00",
            "finished_at": "2018-08-29T12:59:31.427795+00:00",
            "reason": "OK",
            "description": "Everything is fine",
        },
        "scheduler_enabled": True,
        "pass_config": False,
        "owner": "owner",
        "cluster_name": "default",
        "uri": "job://default/owner/job-id",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "submit-image-name",
            "command": "submit-command",
            "http": {"port": 8181},
            "resources": {
                "memory": 4096 * 2**20,
                "cpu": 7.0,
                "shm": True,
                "nvidia_gpu": 1,
            },
            "volumes": [
                {
                    "src_storage_uri": "storage://test-user/path_read_only",
                    "dst_path": "/container/read_only",
                    "read_only": True,
                },
                {
                    "src_storage_uri": "storage://test-user/path_read_write",
                    "dst_path": "/container/path_read_write",
                    "read_only": False,
                },
            ],
        },
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.status("job-id")

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_status_with_tpu(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "status": "running",
        "id": "job-id",
        "description": "This is job description, not a history description",
        "http_url": "http://my_host:8889",
        "history": {
            "created_at": "2018-08-29T12:23:13.981621+00:00",
            "started_at": "2018-08-29T12:23:15.988054+00:00",
            "finished_at": "2018-08-29T12:59:31.427795+00:00",
            "reason": "OK",
            "description": "Everything is fine",
        },
        "scheduler_enabled": True,
        "pass_config": False,
        "owner": "owner",
        "cluster_name": "default",
        "uri": "job://default/owner/job-id",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "submit-image-name",
            "command": "submit-command",
            "http": {"port": 8181},
            "resources": {
                "memory": 4096 * 2**20,
                "cpu": 7.0,
                "shm": True,
                "nvidia_gpu": 1,
                "tpu": {"type": "v3-8", "software_version": "1.14"},
            },
            "volumes": [
                {
                    "src_storage_uri": "storage://test-user/path_read_only",
                    "dst_path": "/container/read_only",
                    "read_only": True,
                },
                {
                    "src_storage_uri": "storage://test-user/path_read_write",
                    "dst_path": "/container/path_read_write",
                    "read_only": False,
                },
            ],
        },
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.status("job-id")

        assert ret == _job_description_from_api(JSON, client.parse)
        assert ret.container.resources.tpu_type == "v3-8"
        assert ret.container.resources.tpu_software_version == "1.14"


async def test_status_wo_project(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = create_job_response("job-id", "running", project_name=None)

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs/job-id", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.status("job-id")
        assert ret == _job_description_from_api(JSON, client.parse)
        assert ret.project_name == "owner"


async def test_job_start(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "image": "submit-image-name",
            "command": "submit-command",
            "http": {"port": 8181, "requires_auth": True},
            "resources": {
                "shm": True,
            },
            "volumes": [
                {
                    "src_storage_uri": "storage://test-user/path_read_only",
                    "dst_path": "/container/read_only",
                    "read_only": True,
                },
                {
                    "src_storage_uri": "storage://test-user/path_read_write",
                    "dst_path": "/container/path_read_write",
                    "read_only": False,
                },
            ],
            "pass_config": False,
            "cluster_name": "default",
            "preset_name": "cpu-small",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        volumes: list[Volume] = [
            Volume(
                URL("storage://test-user/path_read_only"), "/container/read_only", True
            ),
            Volume(
                URL("storage://test-user/path_read_write"),
                "/container/path_read_write",
                False,
            ),
        ]
        ret = await client.jobs.start(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            volumes=volumes,
            http=HTTPPort(8181),
            shm=True,
            preset_name="cpu-small",
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_start_with_privileged_flag(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
        "privileged": True,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "image": "submit-image-name",
            "command": "submit-command",
            "pass_config": False,
            "cluster_name": "default",
            "preset_name": "cpu-small",
            "privileged": True,
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.start(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            preset_name="cpu-small",
            privileged=True,
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_start_with_priority(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
        "privileged": True,
        "priority": "high",
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "image": "submit-image-name",
            "command": "submit-command",
            "pass_config": False,
            "cluster_name": "default",
            "preset_name": "cpu-small",
            "priority": "high",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.start(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            preset_name="cpu-small",
            priority=JobPriority.HIGH,
        )

        assert ret == _job_description_from_api(JSON, client.parse)


@pytest.mark.parametrize(
    "project_name",
    [None, "", "test-project", "other-test-project", "non-existing-project"],
)
async def test_job_start_with_project(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    project_name: str | None,
) -> None:
    JSON = create_job_response("qwerty", "running", project_name=project_name)

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "image": "submit-image-name",
            "pass_config": False,
            "cluster_name": "default",
            "preset_name": "cpu-small",
            # if project_name is not provided, SDK falls back to current project
            "project_name": project_name or "test-project",
            "org_name": "test-org",
        }
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)
    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.start(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            preset_name="cpu-small",
            project_name=project_name,
        )
        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "cluster_name": "default",
        "org_name": "my-test-org",
        "project_name": "test-project",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "amd_gpu": 2,
                "intel_gpu": 3,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                    "amd_gpu": 2,
                    "intel_gpu": 3,
                },
                "volumes": [
                    {
                        "src_storage_uri": "storage://test-user/path_read_only",
                        "dst_path": "/container/read_only",
                        "read_only": True,
                    },
                    {
                        "src_storage_uri": "storage://test-user/path_read_write",
                        "dst_path": "/container/path_read_write",
                        "read_only": False,
                    },
                ],
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(
            memory=16384 * 2**20,
            cpu=7,
            nvidia_gpu=1,
            amd_gpu=2,
            intel_gpu=3,
            shm=True,
        )
        volumes: list[Volume] = [
            Volume(
                URL("storage://test-user/path_read_only"), "/container/read_only", True
            ),
            Volume(
                URL("storage://test-user/path_read_write"),
                "/container/path_read_write",
                False,
            ),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            volumes=volumes,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(container=container, scheduler_enabled=False)

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_with_wait_for_quota(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "cluster_name": "default",
        "project_name": "test-project",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
            },
            "scheduler_enabled": False,
            "wait_for_jobs_quota": True,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
        )
        ret = await client.jobs.run(
            container=container, scheduler_enabled=False, wait_for_jobs_quota=True
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_with_name_and_description(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "name": "test-job-name",
        "description": "job description",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
                "volumes": [
                    {
                        "src_storage_uri": "storage://test-user/path_read_only",
                        "dst_path": "/container/read_only",
                        "read_only": True,
                    },
                    {
                        "src_storage_uri": "storage://test-user/path_read_write",
                        "dst_path": "/container/path_read_write",
                        "read_only": False,
                    },
                ],
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "name": "test-job-name",
            "description": "job description",
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        volumes: list[Volume] = [
            Volume(
                URL("storage://test-user/path_read_only"), "/container/read_only", True
            ),
            Volume(
                URL("storage://test-user/path_read_write"),
                "/container/path_read_write",
                False,
            ),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            volumes=volumes,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(
            container,
            scheduler_enabled=False,
            name="test-job-name",
            description="job description",
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_with_tags(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "tags": ["t1", "t2", "t3"],
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
                "volumes": [
                    {
                        "src_storage_uri": "storage://test-user/path_read_only",
                        "dst_path": "/container/read_only",
                        "read_only": True,
                    },
                    {
                        "src_storage_uri": "storage://test-user/path_read_write",
                        "dst_path": "/container/path_read_write",
                        "read_only": False,
                    },
                ],
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "tags": ["t1", "t2", "t3"],
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        volumes: list[Volume] = [
            Volume(
                URL("storage://test-user/path_read_only"), "/container/read_only", True
            ),
            Volume(
                URL("storage://test-user/path_read_write"),
                "/container/path_read_write",
                False,
            ),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            volumes=volumes,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(
            container,
            scheduler_enabled=False,
            tags=["t1", "t2", "t3"],
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_no_volumes(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "name": "test-job-name",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 7,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "name": "test-job-name",
            "description": "job description",
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(
            container,
            scheduler_enabled=False,
            name="test-job-name",
            description="job description",
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_with_relative_volume_uris(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
                "volumes": [
                    {
                        "src_storage_uri": (
                            "storage://default/test-org/test-project/path"
                        ),
                        "dst_path": "/container/my_path",
                        "read_only": False,
                    },
                    {
                        "src_storage_uri": (
                            "storage://default/test-org/otherproject/path"
                        ),
                        "dst_path": "/container/other_user_path",
                        "read_only": True,
                    },
                    {
                        "src_storage_uri": "storage://othercluster/otherproject/path",
                        "dst_path": "/container/other_cluster_path",
                        "read_only": True,
                    },
                ],
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        volumes: list[Volume] = [
            Volume(URL("storage:path"), "/container/my_path", False),
            Volume(
                URL("storage:/otherproject/path"),
                "/container/other_user_path",
                True,
            ),
            Volume(
                URL("storage://othercluster/otherproject/path"),
                "/container/other_cluster_path",
                True,
            ),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            volumes=volumes,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(container=container, scheduler_enabled=False)

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_with_secret_uris(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
                "env": {"VAR": "VAL"},
                "secret_env": {
                    "SECRET_VAR": ("secret://default/test-org/test-project/secret")
                },
                "volumes": [
                    {
                        "src_storage_uri": (
                            "storage://default/test-org/test-project/path"
                        ),
                        "dst_path": "/container/my_path",
                        "read_only": False,
                    }
                ],
                "secret_volumes": [
                    {
                        "src_secret_uri": (
                            "secret://default/test-org/test-project/secret"
                        ),
                        "dst_path": "/secrets/my_path",
                    }
                ],
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        env = {"VAR": "VAL"}
        secret_env = {"SECRET_VAR": URL("secret:secret")}
        volumes = [Volume(URL("storage:path"), "/container/my_path", False)]
        secret_files = [
            SecretFile(URL("secret:secret"), "/secrets/my_path"),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            env=env,
            secret_env=secret_env,
            volumes=volumes,
            secret_files=secret_files,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(container=container, scheduler_enabled=False)

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_with_disk_volume_uris(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "cluster_name": "default",
        "project_name": "test-project",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
            "disk_volumes": [
                {
                    "src_disk_uri": "disk://default/test-project/disk-1",
                    "dst_path": "/container/my_path",
                    "read_only": False,
                }
            ],
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
                "disk_volumes": [
                    {
                        "src_disk_uri": "disk://default/test-org/test-project/disk-1",
                        "dst_path": "/container/my_path",
                        "read_only": False,
                    }
                ],
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        disk_volumes = [
            DiskVolume(URL("disk:disk-1"), "/container/my_path"),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            disk_volumes=disk_volumes,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(container=container, scheduler_enabled=False)

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_preemptible(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "name": "test-job-name",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "scheduler_enabled": True,
        "pass_config": False,
        "http_url": "http://my_host:8889",
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "http": {"port": 8181, "requires_auth": True},
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7.0,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
                "volumes": [
                    {
                        "src_storage_uri": "storage://test-user/path_read_only",
                        "dst_path": "/container/read_only",
                        "read_only": True,
                    },
                    {
                        "src_storage_uri": "storage://test-user/path_read_write",
                        "dst_path": "/container/path_read_write",
                        "read_only": False,
                    },
                ],
            },
            "scheduler_enabled": True,
            "pass_config": False,
            "name": "test-job-name",
            "description": "job description",
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        volumes: list[Volume] = [
            Volume(
                URL("storage://test-user/path_read_only"), "/container/read_only", True
            ),
            Volume(
                URL("storage://test-user/path_read_write"),
                "/container/path_read_write",
                False,
            ),
        ]
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            volumes=volumes,
            http=HTTPPort(8181),
        )
        ret = await client.jobs.run(
            container,
            scheduler_enabled=True,
            name="test-job-name",
            description="job description",
        )

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_schedule_timeout(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "org_name": "test-org",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
        "schedule_timeout": 5,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7,
                    "shm": True,
                    "nvidia_gpu": 1,
                },
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "schedule_timeout": 5,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(memory=16384 * 2**20, cpu=7, nvidia_gpu=1, shm=True)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
        )
        ret = await client.jobs.run(container=container, schedule_timeout=5)

        assert ret == _job_description_from_api(JSON, client.parse)


async def test_job_run_tpu(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "org_name": "test-org",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
                "shm": False,
                "tpu": {"type": "v3-8", "software_version": "1.14"},
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": False,
        "pass_config": False,
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "resources": {
                    "memory": 16384 * 2**20,
                    "cpu": 7,
                    "shm": True,
                    "nvidia_gpu": 1,
                    "tpu": {"type": "v3-8", "software_version": "1.14"},
                },
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "schedule_timeout": 5,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(
            memory=16384 * 2**20,
            cpu=7,
            nvidia_gpu=1,
            shm=True,
            tpu_type="v3-8",
            tpu_software_version="1.14",
        )
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
        )
        ret = await client.jobs.run(container=container, schedule_timeout=5)

        assert ret == _job_description_from_api(JSON, client.parse)
        assert ret.container.resources.tpu_type == "v3-8"
        assert ret.container.resources.tpu_software_version == "1.14"


async def test_job_run_with_tty(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = create_job_response("job-id-1", "running")
    JSON["container"]["tty"] = True

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "command": "submit-command",
                "resources": {"memory": 16384 * 2**20, "cpu": 0.5, "shm": True},
                "tty": True,
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(16384 * 2**20, 0.5)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
            tty=True,
        )
        ret = await client.jobs.run(container=container)

        assert ret == _job_description_from_api(JSON, client.parse)
        assert ret.container.tty is True


@pytest.mark.parametrize(
    "project_name",
    [None, "", "test-project", "other-test-project", "non-existing-project"],
)
async def test_job_run_with_project(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    project_name: str | None,
) -> None:
    JSON = create_job_response("qwerty", "running", project_name=project_name)

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "resources": {"memory": 16384 * 2**20, "cpu": 0.5, "shm": True},
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": project_name or "test-project",
            "org_name": "test-org",
        }
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)
    srv = await aiohttp_server(app)

    container = Container(
        image=RemoteImage.new_external_image(name="submit-image-name"),
        resources=Resources(16384 * 2**20, 0.5),
    )
    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.run(
            container,
            project_name=project_name,
        )
        assert ret == _job_description_from_api(JSON, client.parse)


def create_job_response(
    id: str,
    status: str,
    owner: str = "owner",
    name: str | None = None,
    org_name: str | None = None,
    image: str = "submit-image-name",
    tags: list[str] | None = None,
    total_price_credits: str = "10.01",
    price_credits_per_hour: str = "20",
    project_name: str | None = "myproject",
) -> dict[str, Any]:
    result = {
        "id": id,
        "status": status,
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "container": {
            "image": image,
            "command": "submit-command",
            "resources": {
                "cpu": 1.0,
                "memory": 16384 * 2**20,
                "nvidia_gpu": 1,
            },
        },
        "scheduler_enabled": True,
        "pass_config": False,
        "owner": owner,
        "cluster_name": "default",
        "uri": f"job://default/{owner}/{id}",
        "total_price_credits": total_price_credits,
        "price_credits_per_hour": price_credits_per_hour,
    }
    if name:
        result["name"] = name
    if tags:
        result["tags"] = tags
    if org_name:
        result["org_name"] = org_name
    if project_name:
        result["project_name"] = project_name
    return result


async def test_list_error_in_stream_response(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    error_result = {"error": "Failed"}

    async def handler(request: web.Request) -> web.StreamResponse:
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(error_result).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(Exception) as err:
            async with client.jobs.list() as it:
                async for _ in it:
                    pass
        assert err.value.args[0] == "Failed"


async def test_list_no_filter(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    jobs = [
        create_job_response("job-id-1", "pending", name="job-name-1"),
        create_job_response("job-id-2", "running", name="job-name-1"),
        create_job_response("job-id-3", "succeeded", name="job-name-1"),
        create_job_response("job-id-4", "failed", name="job-name-1"),
    ]
    JSON = {"jobs": jobs}

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list() as it:
            ret = [job async for job in it]

        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        assert ret == job_descriptions


async def test_list_filter_by_name(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    name_1 = "job-name-1"
    name_2 = "job-name-2"
    jobs = [
        create_job_response("job-id-1", "pending", name=name_1),
        create_job_response("job-id-2", "succeeded", name=name_1),
        create_job_response("job-id-3", "failed", name=name_1),
        create_job_response("job-id-4", "running", name=name_2),
        create_job_response("job-id-5", "succeeded", name=name_2),
        create_job_response("job-id-6", "failed", name=name_2),
        create_job_response("job-id-7", "running"),
        create_job_response("job-id-8", "pending"),
        create_job_response("job-id-9", "succeeded"),
        create_job_response("job-id-10", "failed"),
    ]

    async def handler(request: web.Request) -> web.Response:
        name = request.query.get("name")
        assert name
        filtered_jobs = [job for job in jobs if job.get("name") == name]
        JSON = {"jobs": filtered_jobs}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list(name=name_1) as it:
            ret = [job async for job in it]

        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        assert ret == job_descriptions[:3]


async def test_list_filter_by_statuses(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    name_1 = "job-name-1"
    name_2 = "job-name-2"
    jobs = [
        create_job_response("job-id-1", "pending", name=name_1),
        create_job_response("job-id-2", "succeeded", name=name_1),
        create_job_response("job-id-3", "failed", name=name_1),
        create_job_response("job-id-4", "running", name=name_2),
        create_job_response("job-id-5", "succeeded", name=name_2),
        create_job_response("job-id-6", "failed", name=name_2),
        create_job_response("job-id-7", "running"),
        create_job_response("job-id-8", "pending"),
        create_job_response("job-id-9", "succeeded"),
        create_job_response("job-id-10", "failed"),
        create_job_response("job-id-10", "cancelled"),
    ]

    async def handler(request: web.Request) -> web.Response:
        statuses = request.query.getall("status")
        assert statuses
        filtered_jobs = [job for job in jobs if job["status"] in statuses]
        JSON = {"jobs": filtered_jobs}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    statuses = {JobStatus.FAILED, JobStatus.SUCCEEDED, JobStatus.CANCELLED}
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list(statuses=statuses) as it:
            ret = [job async for job in it]

        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        assert ret == [job for job in job_descriptions if job.status in statuses]


async def test_list_incorrect_image(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    jobs = [
        create_job_response("job-id-1", "running"),
        create_job_response("job-id-2", "pending", image="some.com/path:tag"),
        create_job_response(
            "job-id-3", "failed", image="registry-api.dev.apolo.us/path/:tag"
        ),
        create_job_response("job-id-4", "failed", image=""),
        create_job_response("job-id-5", "failed", image=":"),
    ]

    async def handler(request: web.Request) -> web.Response:
        JSON = {"jobs": jobs}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    statuses = {JobStatus.FAILED, JobStatus.SUCCEEDED}
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list(statuses=statuses) as it:
            ret = [job async for job in it]
    for job in ret:
        if job.status == JobStatus.FAILED:
            assert job.container.image.name == INVALID_IMAGE_NAME
        else:
            assert job.container.image.name != INVALID_IMAGE_NAME


class TestVolumeParsing:
    @pytest.mark.parametrize(
        "volume_param", ["dir", "storage://dir", "storage://dir:/var/www:rw:ro"]
    )
    async def test_incorrect_params_count(
        self, volume_param: str, make_client: _MakeClient
    ) -> None:
        async with make_client("https://example.com") as client:
            with pytest.raises(ValueError, match=r"Invalid volume specification"):
                client.parse.volume(volume_param)

    @pytest.mark.parametrize(
        "volume_param", ["storage://dir:/var/www:write", "storage://dir:/var/www:"]
    )
    async def test_incorrect_mode(
        self, volume_param: str, make_client: _MakeClient
    ) -> None:
        async with make_client("https://example.com") as client:
            with pytest.raises(ValueError, match=r"Wrong ReadWrite/ReadOnly mode spec"):
                client.parse.volume(volume_param)

    @pytest.mark.parametrize(
        "volume_param,volume",
        [
            (
                "storage://default/test-org/test-project/dir:/var/www",
                Volume(
                    storage_uri=URL("storage://default/test-org/test-project/dir"),
                    container_path="/var/www",
                    read_only=False,
                ),
            ),
            (
                "storage://default/test-org/test-project/dir:/var/www:rw",
                Volume(
                    storage_uri=URL("storage://default/test-org/test-project/dir"),
                    container_path="/var/www",
                    read_only=False,
                ),
            ),
            (
                "storage://default/test-org/test-project:/var/www:ro",
                Volume(
                    storage_uri=URL("storage://default/test-org/test-project"),
                    container_path="/var/www",
                    read_only=True,
                ),
            ),
            (
                "storage::/var/www:ro",
                Volume(
                    storage_uri=URL("storage://default/test-org/test-project"),
                    container_path="/var/www",
                    read_only=True,
                ),
            ),
            (
                "storage:dir:/var/www:ro",
                Volume(
                    storage_uri=URL("storage://default/test-org/test-project/dir"),
                    container_path="/var/www",
                    read_only=True,
                ),
            ),
            (
                "storage::/var/www:ro",
                Volume(
                    storage_uri=URL("storage://default/test-org/test-project"),
                    container_path="/var/www",
                    read_only=True,
                ),
            ),
        ],
    )
    async def test_positive(
        self, volume_param: str, volume: Volume, make_client: _MakeClient
    ) -> None:
        async with make_client("https://example.com") as client:
            assert client.parse.volume(volume_param) == volume


async def test_list_filter_by_name_and_statuses(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    name_1 = "job-name-1"
    name_2 = "job-name-2"
    jobs = [
        create_job_response("job-id-1", "pending", name=name_1),
        create_job_response("job-id-2", "succeeded", name=name_1),
        create_job_response("job-id-3", "failed", name=name_1),
        create_job_response("job-id-4", "running", name=name_2),
        create_job_response("job-id-5", "succeeded", name=name_2),
        create_job_response("job-id-6", "failed", name=name_2),
        create_job_response("job-id-7", "running"),
        create_job_response("job-id-8", "pending"),
        create_job_response("job-id-9", "succeeded"),
        create_job_response("job-id-10", "failed"),
    ]

    async def handler(request: web.Request) -> web.Response:
        statuses = request.query.getall("status")
        assert statuses
        name = request.query.get("name")
        assert name
        filtered_jobs = [
            job for job in jobs if job["status"] in statuses and job.get("name") == name
        ]
        JSON = {"jobs": filtered_jobs}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    statuses = {JobStatus.PENDING, JobStatus.SUCCEEDED}
    name = "job-name-1"
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list(statuses=statuses, name=name) as it:
            ret = [job async for job in it]

        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        assert ret == job_descriptions[:2]


async def test_list_filter_by_tags(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    jobs = [
        # under filter:
        create_job_response("job-id-1", "running", tags=["t1", "t2", "t3"]),
        create_job_response("job-id-2", "running", tags=["t1"]),
        create_job_response("job-id-3", "running", tags=["t2"]),
        # out of filter:
        create_job_response("job-id-4", "running", tags=["t4"]),
        create_job_response("job-id-5", "running"),
    ]

    async def handler(request: web.Request) -> web.Response:
        request_tags = set(request.query.getall("tag"))
        filtered_jobs = []
        for job in jobs:
            tags = job.get("tags")
            if tags and set(tags).intersection(request_tags):
                filtered_jobs.append(job)
        JSON = {"jobs": filtered_jobs}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    tags = {"t1", "t2"}
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list(tags=tags) as it:
            ret = [job async for job in it]

        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        assert ret == job_descriptions[:3]


async def test_list_filter_by_name_and_statuses_and_owners(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    name_1 = "job-name-1"
    name_2 = "job-name-2"
    owner_1 = "owner-1"
    owner_2 = "owner-2"
    jobs = [
        create_job_response("job-id-1", "running", name=name_1, owner=owner_1),
        create_job_response("job-id-2", "running", name=name_1, owner=owner_2),
        create_job_response("job-id-3", "running", name=name_2, owner=owner_1),
        create_job_response("job-id-4", "running", name=name_2, owner=owner_2),
        create_job_response("job-id-5", "succeeded", name=name_1, owner=owner_1),
        create_job_response("job-id-6", "succeeded", name=name_1, owner=owner_2),
        create_job_response("job-id-7", "succeeded", name=name_2, owner=owner_1),
        create_job_response("job-id-8", "succeeded", name=name_2, owner=owner_2),
    ]

    async def handler(request: web.Request) -> web.Response:
        statuses = request.query.getall("status")
        name = request.query.get("name")
        owners = request.query.getall("owner")
        filtered_jobs = [
            job
            for job in jobs
            if job["status"] in statuses
            and job.get("name") == name
            and job.get("owner") in owners
        ]
        return web.json_response({"jobs": filtered_jobs})

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    statuses = {JobStatus.RUNNING}
    name = name_1
    owners = {owner_1, owner_2}
    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list(statuses=statuses, name=name, owners=owners) as it:
            ret = [job async for job in it]

        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        assert ret == job_descriptions[:2]


async def test_list_filter_by_date_range(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    jobs = [
        create_job_response("job-id-1", "running"),
        create_job_response("job-id-2", "running"),
        create_job_response("job-id-3", "running"),
    ]
    jobs[0]["history"]["created_at"] = "2018-09-25T12:28:21.298672+00:00"
    jobs[1]["history"]["created_at"] = "2018-09-25T12:28:26.698687+00:00"
    jobs[2]["history"]["created_at"] = "2018-09-25T12:28:31.642202+00:00"

    t1 = isoparse(jobs[0]["history"]["created_at"])
    t2 = isoparse(jobs[1]["history"]["created_at"])
    t3 = isoparse(jobs[2]["history"]["created_at"])
    t2naive = t2.astimezone(None).replace(tzinfo=None)

    async def handler(request: web.Request) -> web.Response:
        since = isoparse(request.query.get("since", "0001-01-01T00:00:00+00:00"))
        until = isoparse(request.query.get("until", "9999-12-31T23:59:59.999999+00:00"))
        filtered_jobs = [
            job
            for job in jobs
            if since <= isoparse(job["history"]["created_at"]) <= until
        ]
        return web.json_response({"jobs": filtered_jobs})

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.list() as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-1", "job-id-2", "job-id-3"}

        async with client.jobs.list(since=t2) as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-2", "job-id-3"}

        async with client.jobs.list(until=t2) as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-1", "job-id-2"}

        async with client.jobs.list(since=t1, until=t2) as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-1", "job-id-2"}

        async with client.jobs.list(since=t1, until=t3) as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-1", "job-id-2", "job-id-3"}

        async with client.jobs.list(since=t2naive) as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-2", "job-id-3"}

        async with client.jobs.list(until=t2naive) as it:
            ret = [job async for job in it]
        assert {job.id for job in ret} == {"job-id-1", "job-id-2"}


async def test_list_filter_by_project(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    proj_1 = "proj-name-1"
    proj_2 = "proj-name-2"
    jobs = [
        create_job_response("job-id-1", "pending", project_name=proj_1),
        create_job_response("job-id-2", "succeeded", project_name=proj_1),
        create_job_response("job-id-3", "failed", project_name=proj_1),
        create_job_response("job-id-4", "running", project_name=proj_2),
        create_job_response("job-id-5", "succeeded", project_name=proj_2),
        create_job_response("job-id-6", "failed", project_name=proj_2),
        create_job_response("job-id-7", "running"),
        create_job_response("job-id-8", "pending"),
        create_job_response("job-id-9", "succeeded"),
        create_job_response("job-id-10", "failed"),
    ]

    async def handler(request: web.Request) -> web.Response:
        projects = request.query.getall("project_name", None)
        if projects:
            filtered_jobs = [job for job in jobs if job["project_name"] in projects]
        else:
            filtered_jobs = jobs
        JSON = {"jobs": filtered_jobs}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/jobs", handler)
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        job_descriptions = [
            _job_description_from_api(job, client.parse) for job in jobs
        ]
        # default -- lists all available jobs
        async with client.jobs.list() as it:
            ret = [job async for job in it]
        assert ret == job_descriptions
        # filter by one project
        async with client.jobs.list(project_names=(proj_1,)) as it:
            ret = [job async for job in it]
        assert ret == job_descriptions[:3]
        # filter by two projects
        async with client.jobs.list(project_names=(proj_1, proj_2)) as it:
            ret = [job async for job in it]
        assert ret == job_descriptions[:6]
        # filter by non-existing project
        async with client.jobs.list(project_names=("non-existing",)) as it:
            ret = [job async for job in it]
        assert ret == []


async def test_job_run_life_span(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "resources": {"memory": 16 * 2**20, "cpu": 0.5, "shm": True},
                "command": "submit-command",
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "max_run_time_minutes": 10,
            "cluster_name": "default",
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(create_job_response("job-id-1", "running"))

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(16 * 2**20, 0.5)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
        )
        await client.jobs.run(container=container, life_span=10 * 60)


async def test_job_run_restart_policy(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "resources": {"memory": 16 * 2**20, "cpu": 0.5, "shm": True},
                "command": "submit-command",
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "restart_policy": "always",
            "cluster_name": "default",
            "org_name": "test-org",
            "project_name": "test-project",
        }
        return web.json_response(create_job_response("job-id-1", "running"))

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(16 * 2**20, 0.5)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            resources=resources,
        )
        await client.jobs.run(
            container=container, restart_policy=JobRestartPolicy.ALWAYS
        )


async def test_job_run_working_dir(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "container": {
                "image": "submit-image-name",
                "resources": {"memory": 16 * 2**20, "cpu": 0.5, "shm": True},
                "command": "submit-command",
                "working_dir": "/working/dir",
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }
        result = create_job_response("job-id-1", "running")
        result["container"]["working_dir"] = "/working/dir"
        return web.json_response(result)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        resources = Resources(16 * 2**20, 0.5)
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            working_dir="/working/dir",
            resources=resources,
        )
        ret = await client.jobs.run(container=container)

        assert ret.container.working_dir == "/working/dir"


async def test_port_forward(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    unused_tcp_port: int,
) -> None:
    async def handler(request: web.Request) -> web.WebSocketResponse:
        resp = web.WebSocketResponse()
        await resp.prepare(request)
        async for msg in resp:
            await resp.send_bytes(b"rep-" + msg.data)
        return resp

    app = web.Application()
    app.router.add_get("/jobs/job-id/port_forward/12345", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.port_forward("job-id", unused_tcp_port, 12345):
            reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
            for i in range(5):
                writer.write(str(i).encode("ascii"))
                ret = await reader.read(1024)
                assert ret == b"rep-" + str(i).encode("ascii")
            writer.close()
            await writer.wait_closed()


async def test_port_forward_logs_error(
    aiohttp_server: _TestServerFactory,
    make_client: _MakeClient,
    unused_tcp_port: int,
    caplog: Any,
) -> None:
    async def handler(request: web.Request) -> web.WebSocketResponse:
        raise web.HTTPBadRequest(
            text="test",
            content_type="application/json",
            headers={"X-Error": "test error info"},
        )

    app = web.Application()
    app.router.add_get("/jobs/job-id/port_forward/12345", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.jobs.port_forward("job-id", unused_tcp_port, 12345):
            reader, writer = await asyncio.open_connection("127.0.0.1", unused_tcp_port)
            writer.write(b"boom")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(0.1)

    assert "test error info" in caplog.text


def test__calc_status_known() -> None:
    assert _calc_status("pending") == JobStatus.PENDING


def test__calc_status_unknown() -> None:
    assert _calc_status("something") == JobStatus.UNKNOWN


async def test_get_capacity(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"cpu-micro": 10})

    app = web.Application()
    app.router.add_get("/jobs/capacity", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        result = await client.jobs.get_capacity()
        assert result == {"cpu-micro": 10}


async def test_bump_life_span(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    called = False

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "additional_max_run_time_minutes": 60,
        }
        nonlocal called
        called = True
        raise web.HTTPNoContent()

    app = web.Application()
    app.router.add_put("/jobs/job-id/max_run_time_minutes", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.jobs.bump_life_span(
            id="job-id",
            additional_life_span=3600,  # 1h
        )
        assert called


async def test_job_price_credits(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    total_price_credits = "105000.00000000000123"
    price_credits_per_hour = "0.000123"

    async def handler(request: web.Request) -> web.Response:
        to_api_request = await request.json()
        # we do not send total_price_credits and price_credits_per_hour
        # they should be controled by the API
        assert to_api_request == {
            "container": {
                "image": "submit-image-name",
                "resources": {"memory": 16 * 2**20, "cpu": 0.5, "shm": True},
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": "test-org",
        }
        api_responce = create_job_response(
            "job-id-1",
            "running",
            total_price_credits=total_price_credits,
            price_credits_per_hour=price_credits_per_hour,
        )
        return web.json_response(api_responce)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            resources=Resources(16 * 2**20, 0.5),
        )
        resp = await client.jobs.run(container=container)
        assert resp.total_price_credits == Decimal(total_price_credits)
        assert resp.price_credits_per_hour == Decimal(price_credits_per_hour)


async def test_job_with_org_name(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    org_name = "my-awesome-organization"

    async def handler(request: web.Request) -> web.Response:
        to_api_request = await request.json()
        assert to_api_request == {
            "container": {
                "image": "submit-image-name",
                "resources": {"memory": 16 * 2**20, "cpu": 0.5, "shm": True},
            },
            "scheduler_enabled": False,
            "pass_config": False,
            "cluster_name": "default",
            "project_name": "test-project",
            "org_name": org_name,
        }
        api_responce = create_job_response(
            "job-id-1",
            "running",
            org_name=org_name,
        )
        return web.json_response(api_responce)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        container = Container(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            resources=Resources(16 * 2**20, 0.5),
        )
        resp = await client.jobs.run(container=container, org_name=org_name)
        assert resp.org_name == org_name


async def test_job_start_with_energy_schedule_name(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "id": "job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "status": "failed",
        "history": {
            "status": "failed",
            "reason": "Error",
            "description": "Mounted on Avail\\n/dev/shm     " "64M\\n\\nExit code: 1",
            "created_at": "2018-09-25T12:28:21.298672+00:00",
            "started_at": "2018-09-25T12:28:59.759433+00:00",
            "finished_at": "2018-09-25T12:28:59.759433+00:00",
        },
        "owner": "owner",
        "project_name": "test-project",
        "cluster_name": "default",
        "uri": "job://default/owner/job-cf519ed3-9ea5-48f6-a8c5-492b810eb56f",
        "total_price_credits": "10.01",
        "price_credits_per_hour": "20",
        "container": {
            "image": "gcr.io/light-reality-205619/ubuntu:latest",
            "command": "date",
            "resources": {
                "cpu": 7,
                "memory": 14 * 2**30,
                "shm": False,
            },
        },
        "http_url": "http://my_host:8889",
        "scheduler_enabled": True,
        "pass_config": False,
        "energy_schedule_name": "some-energy",
    }

    async def handler(request: web.Request) -> web.Response:
        data = await request.json()
        assert data == {
            "image": "submit-image-name",
            "command": "submit-command",
            "cluster_name": "default",
            "preset_name": "cpu-large-p",
            "energy_schedule_name": "some-schedule",
            "pass_config": False,
            "project_name": "test-project",
            "org_name": "test-org",
        }

        return web.json_response(JSON)

    app = web.Application()
    app.router.add_post("/jobs", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        ret = await client.jobs.start(
            image=RemoteImage.new_external_image(name="submit-image-name"),
            command="submit-command",
            preset_name="cpu-large-p",
            energy_schedule_name="some-schedule",
        )

        assert ret == _job_description_from_api(JSON, client.parse)
