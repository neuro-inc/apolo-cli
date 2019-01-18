import pytest
from aiohttp import web
from yarl import URL

from neuromation.clientv2 import ClientV2, FileStatus, FileStatusType


async def test_uri_to_path_non_storage(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        with pytest.raises(ValueError):
            client.storage._uri_to_path(URL("bad-schema://something"))


async def test_uri_to_path_home(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage://~/path")) == "user/path"


async def test_uri_to_path_no_user(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage:/data")) == "user/data"


async def test_uri_to_path_explicit_user(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage://alice/data")) == "alice/data"


async def test_uri_to_path_to_file(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert (
            client.storage._uri_to_path(URL("storage://alice/data/foo.txt"))
            == "alice/data/foo.txt"
        )


async def test_uri_to_path_strip_slash(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert (
            client.storage._uri_to_path(URL("storage://alice/data/foo.txt/"))
            == "alice/data/foo.txt"
        )


async def test_uri_to_path_root(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage:")) == "user"


async def test_uri_to_path_root2(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage:/")) == "user"


async def test_uri_to_path_root3(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage://")) == "user"


@pytest.mark.xfail
async def test_uri_to_path_root4(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage:///")) == "/"


async def test_uri_to_path_relative(token):
    async with ClientV2(URL("https://example.com"), token) as client:
        assert client.storage._uri_to_path(URL("storage:path")) == "user/path"


async def test_storage_ls(aiohttp_server, token):
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
                    "type": "DIR",
                    "modificationTime": 0,
                    "permission": "read",
                },
            ]
        }
    }

    async def handler(request):
        assert request.path == "/storage/user/folder"
        assert request.query == {"op": "LISTSTATUS"}
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/storage/user/folder", handler)

    srv = await aiohttp_server(app)

    async with ClientV2(srv.make_url("/"), token) as client:
        ret = await client.storage.ls(URL("storage://~/folder"))

    assert ret == [
        FileStatus(
            path="foo", size=1024, type="FILE", modification_time=0, permission="read"
        ),
        FileStatus(
            path="bar",
            size=4 * 1024,
            type="DIR",
            modification_time=0,
            permission="read",
        ),
    ]


async def test_storage_rm(aiohttp_server, token):
    async def handler(request):
        assert request.path == "/storage/user/folder"
        assert request.query == {"op": "DELETE"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_delete("/storage/user/folder", handler)

    srv = await aiohttp_server(app)

    async with ClientV2(srv.make_url("/"), token) as client:
        await client.storage.rm(URL("storage://~/folder"))


async def test_storage_mv(aiohttp_server, token):
    async def handler(request):
        assert request.path == "/storage/user/folder"
        assert request.query == {"op": "RENAME", "destination": "/user/other"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_post("/storage/user/folder", handler)

    srv = await aiohttp_server(app)

    async with ClientV2(srv.make_url("/"), token) as client:
        await client.storage.mv(URL("storage://~/folder"), URL("storage://~/other"))


async def test_storage_mkdir(aiohttp_server, token):
    async def handler(request):
        assert request.path == "/storage/user/folder"
        assert request.query == {"op": "MKDIRS"}
        return web.Response(status=204)

    app = web.Application()
    app.router.add_put("/storage/user/folder", handler)

    srv = await aiohttp_server(app)

    async with ClientV2(srv.make_url("/"), token) as client:
        await client.storage.mkdirs(URL("storage://~/folder"))


async def test_storage_create(aiohttp_server, token):
    async def handler(request):
        assert request.path == "/storage/user/file"
        assert request.query == {"op": "CREATE"}
        content = await request.read()
        assert content == b"01234"
        return web.Response(status=201)

    app = web.Application()
    app.router.add_put("/storage/user/file", handler)

    srv = await aiohttp_server(app)

    async def gen():
        for i in range(5):
            yield str(i).encode("ascii")

    async with ClientV2(srv.make_url("/"), token) as client:
        await client.storage.create(URL("storage://~/file"), gen())


async def test_storage_stats(aiohttp_server, token):
    async def handler(request):
        assert request.path == "/storage/user/folder"
        assert request.query == {"op": "GETFILESTATUS"}
        return web.json_response(
            {
                "FileStatus": {
                    "path": "/user/folder",
                    "type": "DIRECTORY",
                    "length": 1234,
                    "modificationTime": 3456,
                    "permission": "read",
                }
            }
        )

    app = web.Application()
    app.router.add_get("/storage/user/folder", handler)

    srv = await aiohttp_server(app)

    async with ClientV2(srv.make_url("/"), token) as client:
        stats = await client.storage.stats(URL("storage://~/folder"))
        assert stats == FileStatus(
            path="/user/folder",
            type=FileStatusType.DIRECTORY,
            size=1234,
            modification_time=3456,
            permission="read",
        )


async def test_storage_normalize(token):
    async with ClientV2("https://example.com", token) as client:
        url = client.storage.normalize(URL("storage:path/to/file.txt"))
        assert url.scheme == "storage"
        assert url.host is None
        assert url.path == "path/to/file.txt"


async def test_storage_normalize_home_dir(token):
    async with ClientV2("https://example.com", token) as client:
        url = client.storage.normalize(URL("storage://~/file.txt"))
        assert url.scheme == "storage"
        assert url.host == "user"
        assert url.path == "/file.txt"


async def test_storage_normalize_bad_scheme(token):
    async with ClientV2("https://example.com", token) as client:
        with pytest.raises(
            ValueError, match="Path should be targeting platform storage."
        ):
            client.storage.normalize(URL("other:path/to/file.txt"))


async def test_storage_normalize_local(token):
    async with ClientV2("https://example.com", token) as client:
        url = client.storage.normalize_local(URL("file:///path/to/file.txt"))
        assert url.scheme == "file"
        assert url.host is None
        assert url.path == "/path/to/file.txt"


async def test_storage_normalize_local_bad_scheme(token):
    async with ClientV2("https://example.com", token) as client:
        with pytest.raises(
            ValueError, match="Path should be targeting local file system."
        ):
            client.storage.normalize_local(URL("other:path/to/file.txt"))


async def test_storage_normalize_local_expand_user(token, monkeypatch):
    monkeypatch.setenv("HOME", "/home/user")
    async with ClientV2("https://example.com", token) as client:
        url = client.storage.normalize_local(URL("file:~/path/to/file.txt"))
        assert url.scheme == "file"
        assert url.host is None
        assert url.path == "/home/user/path/to/file.txt"


async def test_storage_normalize_local_with_host(token):
    async with ClientV2("https://example.com", token) as client:
        with pytest.raises(ValueError, match="Host part is not allowed"):
            client.storage.normalize_local(URL("file://host/path/to/file.txt"))
