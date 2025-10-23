import asyncio
import errno
import json
import os
from filecmp import dircmp
from pathlib import Path
from shutil import copytree
from typing import Any, AsyncIterator, Callable, List, Tuple
from unittest import mock

import pytest
from aiohttp import web
from yarl import URL

from apolo_sdk import (
    Action,
    Client,
    DiskUsageInfo,
    FileStatus,
    FileStatusType,
    IllegalArgumentError,
    StorageProgressComplete,
    StorageProgressDelete,
    StorageProgressStart,
    StorageProgressStep,
)
from apolo_sdk._storage import _parse_content_range

from tests import _RawTestServerFactory, _TestServerFactory

_MakeClient = Callable[..., Client]


FOLDER = Path(__file__).parent
DATA_FOLDER = FOLDER / "data"


def calc_diff(dcmp: "dircmp[str]", *, pre: str = "") -> List[Tuple[str, str]]:
    ret = []
    for name in dcmp.diff_files:
        ret.append((pre + name, pre + name))
    for name in dcmp.left_only:
        ret.append((pre + name, ""))
    for name in dcmp.right_only:
        ret.append(("", pre + name))
    for name, sub_dcmp in dcmp.subdirs.items():
        ret.extend(calc_diff(sub_dcmp, pre=name + "/"))
    return ret


@pytest.fixture
def small_block_size(monkeypatch: Any) -> None:
    import apolo_sdk._storage

    monkeypatch.setattr(apolo_sdk._storage, "READ_SIZE", 300)


@pytest.fixture
def storage_path(tmp_path: Path) -> Path:
    ret = tmp_path / "storage"
    ret.mkdir()
    return ret


@pytest.fixture
async def storage_server(
    aiohttp_raw_server: _RawTestServerFactory, storage_path: Path
) -> Any:
    PREFIX = "/storage/test-org/test-project"
    PREFIX_LEN = len(PREFIX)

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        op = request.query["op"]
        path = request.path
        assert path.startswith(PREFIX)
        path = path[PREFIX_LEN:]
        if path.startswith("/"):
            path = path[1:]
        local_path = storage_path / path
        if op == "CREATE":
            content = await request.read()
            local_path.write_bytes(content)
            return web.Response(status=201)

        elif op == "WRITE":
            rng = _parse_content_range(request.headers.get("Content-Range"))
            content = await request.read()
            assert rng.stop - rng.start == len(content)
            with open(local_path, "r+b") as f:
                f.seek(rng.start)
                f.write(content)
            return web.Response(status=200)

        elif op == "OPEN":
            rng = request.http_range
            content = local_path.read_bytes()
            response = web.StreamResponse()
            start, stop, _ = rng.indices(len(content))
            if not (rng.start is rng.stop is None):
                if start >= stop:
                    raise RuntimeError
                response.set_status(web.HTTPPartialContent.status_code)
                response.headers["Content-Range"] = (
                    f"bytes {start}-{stop - 1}/{len(content)}"
                )
                response.content_length = stop - start
            await response.prepare(request)
            chunk_size = 200
            if stop - start > chunk_size:
                await response.write(content[start : start + chunk_size])
                raise RuntimeError
            else:
                await response.write(content[start:stop])
                await response.write_eof()
                return response

        elif op == "GETFILESTATUS":
            if not local_path.exists():
                raise web.HTTPNotFound()
            stat = local_path.lstat()
            status = {
                "path": local_path.name,
                "length": stat.st_size,
                "modificationTime": stat.st_mtime,
                "permission": "write",
            }
            if local_path.is_symlink():
                status["type"] = "SYMLINK"
                status["target"] = os.readlink(local_path)
            elif local_path.is_file():
                status["type"] = "FILE"
            elif local_path.is_dir():
                status["type"] = "DIRECTORY"
            else:
                status["type"] = "UNKNOWN"
            return web.json_response({"FileStatus": status})

        elif op == "MKDIRS":
            try:
                local_path.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                raise web.HTTPBadRequest(
                    text=json.dumps({"error": "File exists", "errno": "EEXIST"}),
                    content_type="application/json",
                )
            return web.Response(status=201)

        elif op == "LISTSTATUS":
            if not local_path.exists():
                raise web.HTTPNotFound()
            ret = []
            for child in local_path.iterdir():
                stat = child.lstat()
                status = {
                    "path": child.name,
                    "length": stat.st_size,
                    "modificationTime": stat.st_mtime,
                    "permission": "write",
                }
                if child.is_symlink():
                    status["type"] = "SYMLINK"
                    status["target"] = os.readlink(local_path)
                elif child.is_file():
                    status["type"] = "FILE"
                elif child.is_dir():
                    status["type"] = "DIRECTORY"
                else:
                    status["type"] = "UNKNOWN"
                ret.append(status)
            return await make_listiter_response(request, ret)

        else:
            raise web.HTTPInternalServerError(text=f"Unsupported operation {op}")

    return await aiohttp_raw_server(handler)


async def test_storage_ls_legacy(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    JSON = {
        "FileStatuses": {
            "FileStatus": [
                {
                    "path": "foo",
                    "length": 1024,
                    "type": "FILE",
                    "modificationTime": 0,
                    "permission": "read",
                },
                {
                    "path": "bar",
                    "length": 4 * 1024,
                    "type": "DIRECTORY",
                    "modificationTime": 0,
                    "permission": "read",
                },
                {
                    "path": "baz",
                    "length": 1,
                    "type": "SYMLINK",
                    "modificationTime": 0,
                    "permission": "read",
                    "target": "foo",
                },
                {
                    "path": "spam",
                    "length": 1,
                    "type": "SPAM",
                    "modificationTime": 0,
                    "permission": "read",
                },
            ]
        }
    }

    async def handler(request: web.Request) -> web.Response:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "LISTSTATUS"}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    expected = [
        FileStatus(
            path="foo",
            size=1024,
            type=FileStatusType.FILE,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder/foo"),
        ),
        FileStatus(
            path="bar",
            size=4 * 1024,
            type=FileStatusType.DIRECTORY,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder/bar"),
        ),
        FileStatus(
            path="baz",
            size=1,
            type=FileStatusType.SYMLINK,
            modification_time=0,
            permission=Action.READ,
            target="foo",
            uri=URL("storage://default/test-org/test-project/folder/baz"),
        ),
        FileStatus(
            path="spam",
            size=1,
            type=FileStatusType.UNKNOWN,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder/spam"),
        ),
    ]

    async with make_client(srv.make_url("/")) as client:
        async with client.storage.list(URL("storage:folder")) as it:
            ret = [file async for file in it]
            assert ret == expected


async def make_listiter_response(
    request: web.Request, file_statuses: List[Any]
) -> web.StreamResponse:
    assert request.query == {"op": "LISTSTATUS"}
    assert request.headers["Accept"] == "application/x-ndjson"
    resp = web.StreamResponse()
    resp.headers["Content-Type"] = "application/x-ndjson"
    await resp.prepare(request)
    for item in file_statuses:
        await resp.write(json.dumps({"FileStatus": item}).encode() + b"\n")
    return resp


async def test_storage_ls(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    file_statuses = [
        {
            "path": "foo",
            "length": 1024,
            "type": "FILE",
            "modificationTime": 0,
            "permission": "read",
        },
        {
            "path": "bar",
            "length": 4 * 1024,
            "type": "DIRECTORY",
            "modificationTime": 0,
            "permission": "read",
        },
        {
            "path": "baz",
            "length": 1,
            "type": "SYMLINK",
            "modificationTime": 0,
            "permission": "read",
            "target": "foo",
        },
        {
            "path": "spam",
            "length": 1,
            "type": "SPAM",
            "modificationTime": 0,
            "permission": "read",
        },
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "LISTSTATUS"}
        return await make_listiter_response(request, file_statuses)

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.storage.list(URL("storage:folder")) as it:
            ret = [file async for file in it]

    assert ret == [
        FileStatus(
            path="foo",
            size=1024,
            type=FileStatusType.FILE,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder/foo"),
        ),
        FileStatus(
            path="bar",
            size=4 * 1024,
            type=FileStatusType.DIRECTORY,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder/bar"),
        ),
        FileStatus(
            path="baz",
            size=1,
            type=FileStatusType.SYMLINK,
            modification_time=0,
            permission=Action.READ,
            target="foo",
            uri=URL("storage://default/test-org/test-project/folder/baz"),
        ),
        FileStatus(
            path="spam",
            size=1,
            type=FileStatusType.UNKNOWN,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder/spam"),
        ),
    ]


async def test_storage_ls_without_project(make_client: _MakeClient) -> None:
    async with make_client("https://example.com", projects={}) as client:
        with pytest.raises(RuntimeError, match="The current project is not selected"):
            async with client.storage.list(URL("storage:folder")) as it:
                [file async for file in it]


async def test_storage_disk_usage(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project"
        assert request.query == {"op": "GETDISKUSAGE"}
        return web.json_response({"total": 100, "used": 20, "free": 80})

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        res = await client.storage.disk_usage()

    assert res == DiskUsageInfo(
        total=100, used=20, free=80, cluster_name="default", org_name="test-org"
    )


async def test_storage_disk_usage_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage2/test-org/test-project"
        assert request.query == {"op": "GETDISKUSAGE"}
        return web.json_response({"total": 100, "used": 20, "free": 80})

    app = web.Application()
    app.router.add_get("/storage2/test-org/test-project", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        res = await client.storage.disk_usage(cluster_name="another")

    assert res == DiskUsageInfo(
        total=100, used=20, free=80, cluster_name="another", org_name="test-org"
    )


async def test_storage_disk_usage_another_org(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage/org/test-project"
        assert request.query == {"op": "GETDISKUSAGE"}
        return web.json_response({"total": 100, "used": 20, "free": 80})

    app = web.Application()
    app.router.add_get("/storage/org/test-project", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        res = await client.storage.disk_usage(org_name="org")

    assert res == DiskUsageInfo(
        total=100, used=20, free=80, cluster_name="default", org_name="org"
    )


async def test_storage_disk_usage_path(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project/dir"
        assert request.query == {"op": "GETDISKUSAGE"}
        return web.json_response({"total": 100, "used": 20, "free": 80})

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/dir", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        res = await client.storage.disk_usage(uri=URL("storage:dir"))

    assert res == DiskUsageInfo(
        total=100,
        used=20,
        free=80,
        cluster_name="default",
        uri=URL("storage:dir"),
        org_name="test-org",
    )


async def test_storage_ls_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    file_statuses = [
        {
            "path": "foo",
            "length": 1024,
            "type": "FILE",
            "modificationTime": 0,
            "permission": "read",
        },
        {
            "path": "bar",
            "length": 4 * 1024,
            "type": "DIRECTORY",
            "modificationTime": 0,
            "permission": "read",
        },
        {
            "path": "baz",
            "length": 1,
            "type": "SYMLINK",
            "modificationTime": 0,
            "permission": "read",
            "target": "foo",
        },
        {
            "path": "spam",
            "length": 1,
            "type": "SPAM",
            "modificationTime": 0,
            "permission": "read",
        },
    ]

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage2/test-org/test-project/folder"
        assert request.query == {"op": "LISTSTATUS"}
        return await make_listiter_response(request, file_statuses)

    app = web.Application()
    app.router.add_get("/storage2/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        async with client.storage.list(
            URL("storage://another/test-org/test-project/folder")
        ) as it:
            ret = [file async for file in it]

    assert ret == [
        FileStatus(
            path="foo",
            size=1024,
            type=FileStatusType.FILE,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://another/test-org/test-project/folder/foo"),
        ),
        FileStatus(
            path="bar",
            size=4 * 1024,
            type=FileStatusType.DIRECTORY,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://another/test-org/test-project/folder/bar"),
        ),
        FileStatus(
            path="baz",
            size=1,
            type=FileStatusType.SYMLINK,
            modification_time=0,
            permission=Action.READ,
            target="foo",
            uri=URL("storage://another/test-org/test-project/folder/baz"),
        ),
        FileStatus(
            path="spam",
            size=1,
            type=FileStatusType.UNKNOWN,
            modification_time=0,
            permission=Action.READ,
            uri=URL("storage://another/test-org/test-project/folder/spam"),
        ),
    ]


async def test_storage_ls_error_in_server_response(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    error_result = {"error": "Server is to busy", "errno": "EBUSY"}

    async def handler(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "LISTSTATUS"}
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(error_result).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(OSError) as err:
            async with client.storage.list(URL("storage:folder")) as it:
                async for _ in it:
                    pass
        assert err.value.strerror == "Server is to busy"
        assert err.value.errno == errno.EBUSY


async def test_storage_glob(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler_home(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project"
        assert request.query == {"op": "LISTSTATUS"}
        return await make_listiter_response(
            request,
            [
                {
                    "path": "folder",
                    "length": 0,
                    "type": "DIRECTORY",
                    "modificationTime": 0,
                    "permission": "read",
                }
            ],
        )

    async def handler_folder(request: web.Request) -> web.StreamResponse:
        assert "b3" in request.headers
        assert request.path.rstrip("/") == "/storage/test-org/test-project/folder"
        assert request.query["op"] in ("GETFILESTATUS", "LISTSTATUS")
        if request.query["op"] == "GETFILESTATUS":
            return web.json_response(
                {
                    "FileStatus": {
                        "path": "/test-org/test-project/folder",
                        "type": "DIRECTORY",
                        "length": 0,
                        "modificationTime": 0,
                        "permission": "read",
                    }
                }
            )
        elif request.query["op"] == "LISTSTATUS":
            return await make_listiter_response(
                request,
                [
                    {
                        "path": "foo",
                        "length": 1024,
                        "type": "FILE",
                        "modificationTime": 0,
                        "permission": "read",
                    },
                    {
                        "path": "bar",
                        "length": 0,
                        "type": "DIRECTORY",
                        "modificationTime": 0,
                        "permission": "read",
                    },
                ],
            )
        else:
            raise web.HTTPInternalServerError

    async def handler_foo(request: web.Request) -> web.Response:
        assert "b3" in request.headers
        assert request.path == "/storage/test-org/test-project/folder/foo"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-org/test-project/folder/foo",
                    "length": 1024,
                    "type": "FILE",
                    "modificationTime": 0,
                    "permission": "read",
                }
            }
        )

    async def handler_bar(request: web.Request) -> web.StreamResponse:
        assert request.path.rstrip("/") == "/storage/test-org/test-project/folder/bar"
        if request.query["op"] == "GETFILESTATUS":
            return web.json_response(
                {
                    "FileStatus": {
                        "path": "/test-org/test-project/folder/bar",
                        "length": 0,
                        "type": "DIRECTORY",
                        "modificationTime": 0,
                        "permission": "read",
                    }
                }
            )
        elif request.query["op"] == "LISTSTATUS":
            return await make_listiter_response(
                request,
                [
                    {
                        "path": "baz",
                        "length": 0,
                        "type": "FILE",
                        "modificationTime": 0,
                        "permission": "read",
                    }
                ],
            )
        else:
            raise web.HTTPInternalServerError

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project", handler_home)
    app.router.add_get("/storage/test-org/test-project/", handler_home)
    app.router.add_get("/storage/test-org/test-project/folder", handler_folder)
    app.router.add_get("/storage/test-org/test-project/folder/", handler_folder)
    app.router.add_get("/storage/test-org/test-project/folder/foo", handler_foo)
    app.router.add_get("/storage/test-org/test-project/folder/foo/", handler_foo)
    app.router.add_get("/storage/test-org/test-project/folder/bar", handler_bar)
    app.router.add_get("/storage/test-org/test-project/folder/bar/", handler_bar)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:

        async def glob(pattern: str) -> List[URL]:
            async with client.storage.glob(URL(pattern)) as it:
                return [uri async for uri in it]

        assert await glob("storage:folder") == [URL("storage:folder")]
        assert await glob("storage:folder/") == [URL("storage:folder/")]
        assert await glob("storage:folder/*") == [
            URL("storage:folder/foo"),
            URL("storage:folder/bar"),
        ]
        assert await glob("storage:folder/foo") == [URL("storage:folder/foo")]
        assert await glob("storage:folder/[a-d]*") == [URL("storage:folder/bar")]
        assert await glob("storage:folder/*/") == [URL("storage:folder/bar/")]
        assert await glob("storage:*") == [URL("storage:folder")]
        assert await glob("storage:**") == [
            URL("storage:"),
            URL("storage:folder"),
            URL("storage:folder/foo"),
            URL("storage:folder/bar"),
            URL("storage:folder/bar/baz"),
        ]
        assert await glob("storage:*/foo") == [URL("storage:folder/foo")]
        assert await glob("storage:*/f*") == [URL("storage:folder/foo")]
        assert await glob("storage:**/foo") == [URL("storage:folder/foo")]
        assert await glob("storage:**/f*") == [
            URL("storage:folder"),
            URL("storage:folder/foo"),
        ]
        assert await glob("storage:**/f*/") == [URL("storage:folder/")]
        assert await glob("storage:**/b*") == [
            URL("storage:folder/bar"),
            URL("storage:folder/bar/baz"),
        ]
        assert await glob("storage:**/b*/") == [URL("storage:folder/bar/")]


async def test_storage_rm_file(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    remove_listing = {"path": "/test-org/test-project/file", "is_dir": False}

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(remove_listing).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage/test-org/test-project/file", delete_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.rm(URL("storage:file"))


async def test_storage_rm_file_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    remove_listing = {"path": "/test-project/file", "is_dir": False}

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage2/test-project/file"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(remove_listing).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage2/test-project/file", delete_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.rm(URL("storage://another/test-project/file"))


async def test_storage_rm_file_progress(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    remove_listing = {"path": "/test-org/test-project/file", "is_dir": False}

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(remove_listing).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage/test-org/test-project/file", delete_handler)

    srv = await aiohttp_server(app)

    progress = mock.Mock()
    async with make_client(srv.make_url("/")) as client:
        await client.storage.rm(URL("storage:file"), progress=progress)

    progress.delete.assert_called_with(
        StorageProgressDelete(
            uri=URL("storage://default/test-org/test-project/file"),
            is_dir=False,
        )
    )


async def test_storage_rm_file_progress_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    remove_listing = {"path": "/test-project/file", "is_dir": False}

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage2/test-project/file"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(remove_listing).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage2/test-project/file", delete_handler)

    srv = await aiohttp_server(app)

    progress = mock.Mock()
    async with make_client(srv.make_url("/")) as client:
        await client.storage.rm(
            URL("storage://another/test-project/file"), progress=progress
        )

    progress.delete.assert_called_with(
        StorageProgressDelete(
            uri=URL("storage://another/test-project/file"),
            is_dir=False,
        )
    )


async def test_storage_rm_directory(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def delete_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        return web.json_response(
            {"error": "Target is a directory", "errno": "EISDIR"},
            status=web.HTTPBadRequest.status_code,
        )

    app = web.Application()
    app.router.add_delete("/storage/test-org/test-project/folder", delete_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(IsADirectoryError, match="Target is a directory") as cm:
            await client.storage.rm(URL("storage:folder"))
        assert cm.value.errno == errno.EISDIR


async def test_storage_rm_recursive(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    remove_listing = {
        "path": "/test-org/test-project/folder",
        "is_dir": True,
    }

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "DELETE", "recursive": "true"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(remove_listing).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage/test-org/test-project/folder", delete_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.rm(URL("storage:folder"), recursive=True)


async def test_storage_rm_oserror_in_the_response_stream(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    error_result = {"error": "Server is to busy", "errno": "EBUSY"}

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(error_result).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage/test-org/test-project/file", delete_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(OSError) as err:
            await client.storage.rm(URL("storage:file"))
        assert err.value.strerror == "Server is to busy"
        assert err.value.errno == errno.EBUSY


async def test_storage_rm_generic_error_in_the_response_stream(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    error_result = {"error": "Server failed", "errno": None}

    async def delete_handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        assert request.query == {"op": "DELETE", "recursive": "false"}
        assert request.headers["Accept"] == "application/x-ndjson"
        resp = web.StreamResponse()
        resp.headers["Content-Type"] = "application/x-ndjson"
        await resp.prepare(request)
        await resp.write(json.dumps(error_result).encode() + b"\n")
        return resp

    app = web.Application()
    app.router.add_delete("/storage/test-org/test-project/file", delete_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(Exception) as err:
            await client.storage.rm(URL("storage:file"))
        assert err.value.args[0] == "Server failed"


async def test_storage_mv(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {
            "op": "RENAME",
            "destination": "/test-org/test-project/other",
        }
        return web.Response(status=204)

    app = web.Application()
    app.router.add_post("/storage/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mv(URL("storage:folder"), URL("storage:other"))


async def test_storage_mv_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage2/test-project/folder"
        assert request.query == {"op": "RENAME", "destination": "/test-project/other"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_post("/storage2/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mv(
            URL("storage://another/test-project/folder"),
            URL("storage://another/test-project/other"),
        )


async def test_storage_mv_different_clusters(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(ValueError, match="Cannot move cross-cluster"):
            await client.storage.mv(
                URL("storage:folder"), URL("storage://another/test-project/other")
            )
        with pytest.raises(ValueError, match="Cannot move cross-cluster"):
            await client.storage.mv(
                URL("storage://another/test-project/folder"), URL("storage:other")
            )


async def test_storage_mv_unknown_cluster(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(
            RuntimeError,
            match="Cluster unknown doesn't exist in a list of available clusters",
        ):
            await client.storage.mv(
                URL("storage://unknown/test-project/folder"),
                URL("storage://unknown/test-project/other"),
            )


async def test_storage_mkdir_parents_exist_ok(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder/sub"
        assert request.query == {"op": "MKDIRS"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_put("/storage/test-org/test-project/folder/sub", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mkdir(
            URL("storage:folder/sub"), parents=True, exist_ok=True
        )


async def test_storage_mkdir_parents_exist_ok_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage2/test-project/folder/sub"
        assert request.query == {"op": "MKDIRS"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_put("/storage2/test-project/folder/sub", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mkdir(
            URL("storage://another/test-project/folder/sub"),
            parents=True,
            exist_ok=True,
        )


async def test_storage_mkdir_parents(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def get_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder/sub"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.Response(status=404)

    async def put_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder/sub"
        assert request.query == {"op": "MKDIRS"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder/sub", get_handler)
    app.router.add_put("/storage/test-org/test-project/folder/sub", put_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mkdir(URL("storage:folder/sub"), parents=True)


async def test_storage_mkdir_exist_ok(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def get_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-org/test-project/folder",
                    "type": "DIRECTORY",
                    "length": 1234,
                    "modificationTime": 3456,
                    "permission": "read",
                }
            }
        )

    async def put_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder/sub"
        assert request.query == {"op": "MKDIRS"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder", get_handler)
    app.router.add_put("/storage/test-org/test-project/folder/sub", put_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mkdir(URL("storage:folder/sub"), exist_ok=True)


async def test_storage_mkdir(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def get_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder/sub"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.Response(status=404)

    async def parent_get_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-org/test-project/folder",
                    "type": "DIRECTORY",
                    "length": 1234,
                    "modificationTime": 3456,
                    "permission": "read",
                }
            }
        )

    async def put_handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder/sub"
        assert request.query == {"op": "MKDIRS"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder/sub", get_handler)
    app.router.add_get("/storage/test-org/test-project/folder", parent_get_handler)
    app.router.add_put("/storage/test-org/test-project/folder/sub", put_handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.mkdir(URL("storage:folder/sub"))


async def test_storage_create(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/file"
        assert request.query == {"op": "CREATE"}
        content = await request.read()
        assert content == b"01234"
        return web.Response(status=201)

    app = web.Application()
    app.router.add_put("/storage/test-org/test-project/file", handler)

    srv = await aiohttp_server(app)

    async def gen() -> AsyncIterator[bytes]:
        for i in range(5):
            yield str(i).encode("ascii")

    async with make_client(srv.make_url("/")) as client:
        await client.storage.create(URL("storage:file"), gen())


async def test_storage_create_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage2/test-project/file"
        assert request.query == {"op": "CREATE"}
        content = await request.read()
        assert content == b"01234"
        return web.Response(status=201)

    app = web.Application()
    app.router.add_put("/storage2/test-project/file", handler)

    srv = await aiohttp_server(app)

    async def gen() -> AsyncIterator[bytes]:
        for i in range(5):
            yield str(i).encode("ascii")

    async with make_client(srv.make_url("/")) as client:
        await client.storage.create(URL("storage://another/test-project/file"), gen())


async def test_storage_write(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/file"
        assert request.query == {"op": "WRITE"}
        rng = _parse_content_range(request.headers.get("Content-Range"))
        assert rng == slice(4, 9)
        content = await request.read()
        assert content == b"01234"
        return web.Response(status=200)

    app = web.Application()
    app.router.add_patch("/storage/test-org/test-project/file", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.write(URL("storage:file"), b"01234", 4)


async def test_storage_write_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage2/test-project/file"
        assert request.query == {"op": "WRITE"}
        rng = _parse_content_range(request.headers.get("Content-Range"))
        assert rng == slice(4, 9)
        content = await request.read()
        assert content == b"01234"
        return web.Response(status=200)

    app = web.Application()
    app.router.add_patch("/storage2/test-project/file", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.storage.write(
            URL("storage://another/test-project/file"), b"01234", 4
        )


async def test_storage_stats(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-org/test-project/folder",
                    "type": "DIRECTORY",
                    "length": 1234,
                    "modificationTime": 3456,
                    "permission": "read",
                }
            }
        )

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        stats = await client.storage.stat(URL("storage:folder"))
        assert stats == FileStatus(
            path="/test-org/test-project/folder",
            type=FileStatusType.DIRECTORY,
            size=1234,
            modification_time=3456,
            permission=Action.READ,
            uri=URL("storage://default/test-org/test-project/folder"),
        )


async def test_storage_stats_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage2/test-project/folder"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-project/folder",
                    "type": "DIRECTORY",
                    "length": 1234,
                    "modificationTime": 3456,
                    "permission": "read",
                }
            }
        )

    app = web.Application()
    app.router.add_get("/storage2/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        stats = await client.storage.stat(URL("storage://another/test-project/folder"))
        assert stats == FileStatus(
            path="/test-project/folder",
            type=FileStatusType.DIRECTORY,
            size=1234,
            modification_time=3456,
            permission=Action.READ,
            uri=URL("storage://another/test-project/folder"),
        )


async def test_storage_stats_symlink(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/link"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-org/test-project/link",
                    "type": "SYMLINK",
                    "length": 1234,
                    "modificationTime": 3456,
                    "permission": "read",
                    "target": "folder/subfolder/file",
                }
            }
        )

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/link", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        stats = await client.storage.stat(URL("storage:link"))
        assert stats == FileStatus(
            path="/test-org/test-project/link",
            type=FileStatusType.SYMLINK,
            size=1234,
            modification_time=3456,
            permission=Action.READ,
            target="folder/subfolder/file",
            uri=URL("storage://default/test-org/test-project/link"),
        )


async def test_storage_open(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        if request.query["op"] == "OPEN":
            resp = web.StreamResponse()
            await resp.prepare(request)
            for i in range(5):
                await resp.write(str(i).encode("ascii"))
            return resp
        else:
            raise AssertionError(f"Unknown operation {request.query['op']}")

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/file", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        buf = bytearray()
        async with client.storage.open(URL("storage:file")) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b"01234"


async def test_storage_open_another_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage2/test-project/file"
        if request.query["op"] == "OPEN":
            resp = web.StreamResponse()
            await resp.prepare(request)
            for i in range(5):
                await resp.write(str(i).encode("ascii"))
            return resp
        else:
            raise AssertionError(f"Unknown operation {request.query['op']}")

    app = web.Application()
    app.router.add_get("/storage2/test-project/file", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        buf = bytearray()
        async with client.storage.open(
            URL("storage://another/test-project/file")
        ) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b"01234"


async def test_storage_open_partial_read(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        if request.query["op"] == "OPEN":
            rng = request.http_range
            data = b"ababahalamaha"
            start, stop, _ = rng.indices(len(data))
            return web.Response(
                status=web.HTTPPartialContent.status_code,
                headers={"Content-Range": f"bytes {start}-{stop - 1}/{len(data)}"},
                body=data[start:stop],
            )
        else:
            raise AssertionError(f"Unknown operation {request.query['op']}")

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/file", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        buf = bytearray()
        async with client.storage.open(URL("storage:file"), 5) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b"halamaha"

        buf = bytearray()
        async with client.storage.open(URL("storage:file"), 5, 4) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b"hala"

        buf = bytearray()
        async with client.storage.open(URL("storage:file"), 5, 20) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b"halamaha"

        buf = bytearray()
        async with client.storage.open(URL("storage:file"), 5, 0) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b""


async def test_storage_open_unsupported_partial_read(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        assert request.path == "/storage/test-org/test-project/file"
        if request.query["op"] == "OPEN":
            resp = web.StreamResponse()
            await resp.prepare(request)
            for i in range(5):
                await resp.write(str(i).encode("ascii"))
            return resp
        else:
            raise AssertionError(f"Unknown operation {request.query['op']}")

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/file", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        buf = bytearray()
        async with client.storage.open(URL("storage:file"), 0) as it:
            async for chunk in it:
                buf.extend(chunk)
        assert buf == b"01234"

        with pytest.raises(RuntimeError):
            async with client.storage.open(URL("storage:file"), 5) as it:
                async for chunk in it:
                    pass


async def test_storage_open_directory(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.path == "/storage/test-org/test-project/folder"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/test-org/test-project/folder",
                    "type": "DIRECTORY",
                    "length": 5,
                    "modificationTime": 3456,
                    "permission": "read",
                }
            }
        )

    app = web.Application()
    app.router.add_get("/storage/test-org/test-project/folder", handler)

    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        buf = bytearray()
        with pytest.raises((IsADirectoryError, IllegalArgumentError)):
            async with client.storage.open(URL("storage:folder")) as it:
                async for chunk in it:
                    buf.extend(chunk)
        assert not buf


# test normalizers


# high level API


async def test_storage_upload_file_does_not_exists(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(FileNotFoundError):
            await client.storage.upload_file(
                URL("file:///not-exists-file"), URL("storage://host/path/to/file.txt")
            )


async def test_storage_upload_dir_doesnt_exist(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(IsADirectoryError):
            await client.storage.upload_file(
                URL(FOLDER.as_uri()), URL("storage://host/path/to")
            )


async def test_storage_upload_not_a_file(
    storage_server: Any,
    make_client: _MakeClient,
    storage_path: Path,
    small_block_size: None,
) -> None:
    file_path = Path(os.devnull).absolute()
    target_path = storage_path / "file.txt"
    progress = mock.Mock()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(
            URL(file_path.as_uri()), URL("storage:file.txt"), progress=progress
        )

    uploaded = target_path.read_bytes()
    assert uploaded == b""

    src = URL(file_path.as_uri())
    dst = URL("storage://default/test-org/test-project/file.txt")
    progress.start.assert_called_with(StorageProgressStart(src, dst, 0))
    progress.step.assert_not_called()
    progress.complete.assert_called_with(StorageProgressComplete(src, dst, 0))


async def test_storage_upload_regular_file_to_existing_file_target(
    storage_server: Any,
    make_client: _MakeClient,
    storage_path: Path,
    small_block_size: None,
) -> None:
    file_path = DATA_FOLDER / "file.txt"
    file_size = file_path.stat().st_size
    target_path = storage_path / "file.txt"
    progress = mock.Mock()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(
            URL(file_path.as_uri()), URL("storage:file.txt"), progress=progress
        )

    expected = file_path.read_bytes()
    uploaded = target_path.read_bytes()
    assert uploaded == expected

    src = URL(file_path.as_uri())
    dst = URL("storage://default/test-org/test-project/file.txt")
    progress.start.assert_called_with(StorageProgressStart(src, dst, file_size))
    progress.step.assert_called_with(
        StorageProgressStep(src, dst, file_size, file_size)
    )
    progress.complete.assert_called_with(StorageProgressComplete(src, dst, file_size))


async def test_storage_upload_regular_file_to_existing_dir(
    storage_server: Any,
    make_client: _MakeClient,
    storage_path: Path,
    small_block_size: None,
) -> None:
    file_path = DATA_FOLDER / "file.txt"
    folder = storage_path / "folder"
    folder.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises(IsADirectoryError):
            await client.storage.upload_file(
                URL(file_path.as_uri()), URL("storage:folder")
            )


async def test_storage_upload_regular_file_to_existing_file(
    storage_server: Any,
    make_client: _MakeClient,
    storage_path: Path,
    small_block_size: None,
) -> None:
    file_path = DATA_FOLDER / "file.txt"
    folder = storage_path / "folder"
    folder.mkdir()
    target_path = folder / "file.txt"
    target_path.write_bytes(b"existing file")

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(
            URL(file_path.as_uri()), URL("storage:folder/file.txt")
        )

    expected = file_path.read_bytes()
    uploaded = target_path.read_bytes()
    assert uploaded == expected


async def test_storage_upload_regular_file_to_existing_dir_with_trailing_slash(
    storage_server: Any,
    make_client: _MakeClient,
    storage_path: Path,
    small_block_size: None,
) -> None:
    file_path = DATA_FOLDER / "file.txt"
    folder = storage_path / "folder"
    folder.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises(IsADirectoryError):
            await client.storage.upload_file(
                URL(file_path.as_uri()), URL("storage:folder/")
            )


async def test_storage_upload_regular_file_to_existing_non_dir(
    storage_server: Any,
    make_client: _MakeClient,
    storage_path: Path,
    small_block_size: None,
) -> None:
    file_path = DATA_FOLDER / "file.txt"
    path = storage_path / "file"
    path.write_bytes(b"dummy")

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises(NotADirectoryError):
            await client.storage.upload_file(
                URL(file_path.as_uri()), URL("storage:file/subfile.txt")
            )


async def test_storage_upload_regular_file_to_not_existing(
    storage_server: Any, make_client: _MakeClient, small_block_size: None
) -> None:
    file_path = DATA_FOLDER / "file.txt"

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises(NotADirectoryError):
            await client.storage.upload_file(
                URL(file_path.as_uri()), URL("storage:absent-dir/absent-file.txt")
            )


async def test_storage_upload_recursive_src_doesnt_exist(
    make_client: _MakeClient,
) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(FileNotFoundError):
            await client.storage.upload_dir(
                URL("file:does_not_exist"), URL("storage://host/path/to")
            )


async def test_storage_upload_recursive_src_is_a_file(make_client: _MakeClient) -> None:
    file_path = DATA_FOLDER / "file.txt"

    async with make_client("https://example.com") as client:
        with pytest.raises(NotADirectoryError):
            await client.storage.upload_dir(
                URL(file_path.as_uri()), URL("storage://host/path/to")
            )


async def test_storage_upload_recursive_target_is_a_file(
    storage_server: Any, make_client: _MakeClient, storage_path: Path
) -> None:
    target_file = storage_path / "file.txt"
    target_file.write_bytes(b"dummy")

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises(NotADirectoryError):
            await client.storage.upload_dir(
                URL(DATA_FOLDER.as_uri()), URL("storage:file.txt")
            )


async def test_storage_upload_empty_dir(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    target_dir = storage_path / "folder"
    assert not target_dir.exists()
    src_dir = tmp_path / "empty"
    src_dir.mkdir()
    assert list(src_dir.iterdir()) == []

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(URL(src_dir.as_uri()), URL("storage:folder"))

    assert list(target_dir.iterdir()) == []


async def test_storage_upload_recursive_ok(
    storage_server: Any, make_client: _MakeClient, storage_path: Path
) -> None:
    target_dir = storage_path / "folder"
    target_dir.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(
            URL(DATA_FOLDER.as_uri()) / "nested", URL("storage:folder")
        )
    diff = dircmp(DATA_FOLDER / "nested", target_dir)
    assert not calc_diff(diff)


async def test_storage_upload_recursive_slash_ending(
    storage_server: Any, make_client: _MakeClient, storage_path: Path
) -> None:
    target_dir = storage_path / "folder"
    target_dir.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(
            URL(DATA_FOLDER.as_uri()) / "nested", URL("storage:folder/")
        )
    diff = dircmp(DATA_FOLDER / "nested", target_dir)
    assert not calc_diff(diff)


async def test_storage_download_regular_file_to_absent_file(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    src_file = DATA_FOLDER / "file.txt"
    storage_file = storage_path / "file.txt"
    storage_file.write_bytes(src_file.read_bytes())
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    local_file = local_dir / "file.txt"
    progress = mock.Mock()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(
            URL("storage:file.txt"), URL(local_file.as_uri()), progress=progress
        )

    expected = src_file.read_bytes()
    downloaded = local_file.read_bytes()
    assert downloaded == expected

    src = URL("storage://default/test-org/test-project/file.txt")
    dst = URL(local_file.as_uri())
    file_size = src_file.stat().st_size
    progress.start.assert_called_with(StorageProgressStart(src, dst, file_size))
    progress.step.assert_called_with(
        StorageProgressStep(src, dst, file_size, file_size)
    )
    progress.complete.assert_called_with(StorageProgressComplete(src, dst, file_size))


async def test_storage_download_regular_file_to_existing_file(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    src_file = DATA_FOLDER / "file.txt"
    storage_file = storage_path / "file.txt"
    storage_file.write_bytes(src_file.read_bytes())
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    local_file = local_dir / "file.txt"
    local_file.write_bytes(b"Previous data")

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(
            URL("storage:file.txt"), URL(local_file.as_uri())
        )

    expected = src_file.read_bytes()
    downloaded = local_file.read_bytes()
    assert downloaded == expected


async def test_storage_download_regular_file_to_dir(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    src_file = DATA_FOLDER / "file.txt"
    storage_file = storage_path / "file.txt"
    storage_file.write_bytes(src_file.read_bytes())
    local_dir = tmp_path / "local"
    local_dir.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises((IsADirectoryError, PermissionError)):
            await client.storage.download_file(
                URL("storage:file.txt"), URL(local_dir.as_uri())
            )


async def test_storage_download_regular_file_to_dir_slash_ended(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    src_file = DATA_FOLDER / "file.txt"
    storage_file = storage_path / "file.txt"
    storage_file.write_bytes(src_file.read_bytes())
    local_dir = tmp_path / "local"
    local_dir.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        with pytest.raises((IsADirectoryError, PermissionError)):
            await client.storage.download_file(
                URL("storage:file.txt"), URL(local_dir.as_uri() + "/")
            )


async def test_storage_download_regular_file_to_non_file(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    src_file = DATA_FOLDER / "file.txt"
    storage_file = storage_path / "file.txt"
    storage_file.write_bytes(src_file.read_bytes())

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(
            URL("storage:file.txt"), URL(Path(os.devnull).absolute().as_uri())
        )


async def test_storage_download_empty_dir(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    storage_dir = storage_path / "folder"
    storage_dir.mkdir()
    assert list(storage_dir.iterdir()) == []
    target_dir = tmp_path / "empty"
    assert not target_dir.exists()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(
            URL("storage:folder"), URL(target_dir.as_uri())
        )

    assert list(target_dir.iterdir()) == []


async def test_storage_download_dir(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    storage_dir = storage_path / "folder"
    copytree(DATA_FOLDER / "nested", storage_dir)
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    target_dir = local_dir / "nested"

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(
            URL("storage:folder"), URL(target_dir.as_uri())
        )

    diff = dircmp(DATA_FOLDER / "nested", target_dir)
    assert not calc_diff(diff)


async def test_storage_download_dir_slash_ending(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    storage_dir = storage_path / "folder"
    copytree(DATA_FOLDER / "nested", storage_dir / "nested")
    local_dir = tmp_path / "local"
    local_dir.mkdir()

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(
            URL("storage:folder"), URL(local_dir.as_uri() + "/")
        )

    diff = dircmp(DATA_FOLDER / "nested", local_dir / "nested")
    assert not calc_diff(diff)


@pytest.fixture
def zero_time_threshold(monkeypatch: Any) -> None:
    import apolo_sdk._storage

    monkeypatch.setattr(apolo_sdk._storage, "TIME_THRESHOLD", 0.0)


async def test_storage_upload_file_update(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
    small_block_size: None,
) -> None:
    storage_file = storage_path / "file.txt"
    local_file = tmp_path / "file.txt"
    src = URL(local_file.as_uri())
    dst = URL("storage:file.txt")

    # No destination file
    assert not storage_file.exists()
    local_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, update=True)
    assert storage_file.read_bytes() == b"old content"

    # Source file is newer
    local_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, update=True)
    assert storage_file.read_bytes() == b"new content"

    # Destination file is newer, same size
    await asyncio.sleep(5)
    storage_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, update=True)
    assert storage_file.read_bytes() == b"old"


async def test_storage_upload_file_continue(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
    small_block_size: None,
) -> None:
    storage_file = storage_path / "file.txt"
    local_file = tmp_path / "file.txt"
    src = URL(local_file.as_uri())
    dst = URL("storage:file.txt")

    # No destination file
    assert not storage_file.exists()
    local_file.write_bytes(b"content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"content"

    # Source file is newer
    local_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"new content"

    # Destination file is newer, same size
    await asyncio.sleep(5)
    storage_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"old content"

    # Destination file is shorter
    storage_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"old content"

    # Destination file is longer
    storage_file.write_bytes(b"old long content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_file(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"new content"


async def test_storage_upload_dir_update(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
) -> None:
    storage_file = storage_path / "folder" / "nested" / "file.txt"
    local_dir = tmp_path / "folder"
    local_file = local_dir / "nested" / "file.txt"
    local_file.parent.mkdir(parents=True)
    src = URL(local_dir.as_uri())
    dst = URL("storage:folder")

    # No destination file
    assert not storage_file.exists()
    local_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, update=True)
    assert storage_file.read_bytes() == b"old content"

    # Source file is newer
    local_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, update=True)
    assert storage_file.read_bytes() == b"new content"

    # Destination file is newer, same size
    await asyncio.sleep(5)
    storage_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, update=True)
    assert storage_file.read_bytes() == b"old"


async def test_storage_upload_dir_continue(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
    small_block_size: None,
) -> None:
    storage_file = storage_path / "folder" / "nested" / "file.txt"
    local_dir = tmp_path / "folder"
    local_file = local_dir / "nested" / "file.txt"
    local_file.parent.mkdir(parents=True)
    src = URL(local_dir.as_uri())
    dst = URL("storage:folder")

    # No destination file
    assert not storage_file.exists()
    local_file.write_bytes(b"content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"content"

    # Source file is newer
    local_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"new content"

    # Destination file is newer, same size
    await asyncio.sleep(5)
    storage_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"old content"

    # Destination file is shorter
    storage_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"old content"

    # Destination file is longer
    storage_file.write_bytes(b"old long content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(src, dst, continue_=True)
    assert storage_file.read_bytes() == b"new content"


async def test_storage_download_file_update(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
) -> None:
    storage_file = storage_path / "file.txt"
    local_file = tmp_path / "file.txt"
    src = URL("storage:file.txt")
    dst = URL(local_file.as_uri())

    # No destination file
    assert not local_file.exists()
    storage_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, update=True)
    assert local_file.read_bytes() == b"old content"

    # Source file is newer
    storage_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, update=True)
    assert local_file.read_bytes() == b"new content"

    # Destination file is newer
    await asyncio.sleep(2)
    local_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, update=True)
    assert local_file.read_bytes() == b"old"


async def test_storage_download_file_continue(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
    small_block_size: None,
) -> None:
    storage_file = storage_path / "file.txt"
    local_file = tmp_path / "file.txt"
    src = URL("storage:file.txt")
    dst = URL(local_file.as_uri())

    # No destination file
    assert not local_file.exists()
    storage_file.write_bytes(b"content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, continue_=True)
    assert local_file.read_bytes() == b"content"

    # Source file is newer
    storage_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, continue_=True)
    assert local_file.read_bytes() == b"new content"

    # Destination file is newer, same size
    await asyncio.sleep(2)
    local_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, continue_=True)
    assert local_file.read_bytes() == b"old content"

    # Destination file is shorter
    local_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, continue_=True)
    assert local_file.read_bytes() == b"old content"

    # Destination file is longer
    local_file.write_bytes(b"old long content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_file(src, dst, continue_=True)
    assert local_file.read_bytes() == b"new content"


async def test_storage_download_dir_update(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
) -> None:
    storage_file = storage_path / "folder" / "nested" / "file.txt"
    local_dir = tmp_path / "folder"
    local_file = local_dir / "nested" / "file.txt"
    storage_file.parent.mkdir(parents=True)
    src = URL("storage:folder")
    dst = URL(local_dir.as_uri())

    # No destination file
    assert not local_file.exists()
    storage_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, update=True)
    assert local_file.read_bytes() == b"old content"

    # Source file is newer
    storage_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, update=True)
    assert local_file.read_bytes() == b"new content"

    # Destination file is newer
    await asyncio.sleep(2)
    local_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, update=True)
    assert local_file.read_bytes() == b"old"


async def test_storage_download_dir_continue(
    storage_server: Any,
    make_client: _MakeClient,
    tmp_path: Path,
    storage_path: Path,
    zero_time_threshold: None,
) -> None:
    storage_file = storage_path / "folder" / "nested" / "file.txt"
    local_dir = tmp_path / "folder"
    local_file = local_dir / "nested" / "file.txt"
    storage_file.parent.mkdir(parents=True)
    src = URL("storage:folder")
    dst = URL(local_dir.as_uri())

    # No destination file
    assert not local_file.exists()
    storage_file.write_bytes(b"content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, continue_=True)
    assert local_file.read_bytes() == b"content"

    # Source file is newer
    storage_file.write_bytes(b"new content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, continue_=True)
    assert local_file.read_bytes() == b"new content"

    # Destination file is newer, same size
    await asyncio.sleep(2)
    local_file.write_bytes(b"old content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, continue_=True)
    assert local_file.read_bytes() == b"old content"

    # Destination file is shorter
    local_file.write_bytes(b"old")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, continue_=True)
    assert local_file.read_bytes() == b"old content"

    # Destination file is longer
    local_file.write_bytes(b"old long content")
    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.download_dir(src, dst, continue_=True)
    assert local_file.read_bytes() == b"new content"


async def test_storage_upload_dir_with_ignore_file_names(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    local_dir = tmp_path / "folder"
    local_dir2 = local_dir / "nested"
    local_dir2.mkdir(parents=True)
    for name in "one", "two", "three":
        (local_dir / name).write_bytes(b"")
        (local_dir2 / name).write_bytes(b"")
    (local_dir / ".apoloignore").write_text("one")
    (local_dir2 / ".gitignore").write_text("two")

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(
            URL(local_dir.as_uri()),
            URL("storage:folder"),
            ignore_file_names={".apoloignore", ".gitignore"},
        )

    names = sorted(os.listdir(storage_path / "folder"))
    assert names == [".apoloignore", "nested", "three", "two"]
    names = sorted(os.listdir(storage_path / "folder" / "nested"))
    assert names == [".gitignore", "three"]


async def test_storage_upload_dir_with_parent_ignore_file_names(
    storage_server: Any, make_client: _MakeClient, tmp_path: Path, storage_path: Path
) -> None:
    parent_dir = tmp_path / "parent"
    local_dir = parent_dir / "folder"
    local_dir2 = local_dir / "nested"
    local_dir2.mkdir(parents=True)
    for name in "one", "two", "three":
        (local_dir / name).write_bytes(b"")
        (local_dir2 / name).write_bytes(b"")
    (tmp_path / ".apoloignore").write_text("one")
    (parent_dir / ".gitignore").write_text("*/two")

    async with make_client(storage_server.make_url("/")) as client:
        await client.storage.upload_dir(
            URL(local_dir.as_uri()),
            URL("storage:folder"),
            ignore_file_names={".apoloignore", ".gitignore"},
        )

    names = sorted(os.listdir(storage_path / "folder"))
    assert names == ["nested", "three"]
    names = sorted(os.listdir(storage_path / "folder" / "nested"))
    assert names == ["three", "two"]
