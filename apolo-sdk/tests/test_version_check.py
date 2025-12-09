import asyncio
import socket
import ssl
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import aiohttp
import dateutil.parser
import pytest
import trustme
from aiohttp import web
from aiohttp.abc import AbstractResolver, ResolveResult
from aiohttp.test_utils import unused_port

from apolo_sdk import Client, PluginManager

PYPI_JSON = {
    "info": {
        "author": "Neu.ro Team",
        "author_email": "team@neu.ro",
        "bugtrack_url": None,
        "classifiers": [
            "Development Status :: 4 - Beta",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "Intended Audience :: Information Technology",
            "Intended Audience :: Science/Research",
            "License :: Other/Proprietary License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Topic :: Scientific/Engineering :: Artificial Intelligence",
            "Topic :: Software Development",
            "Topic :: Utilities",
        ],
        "description": "blablabla this is description",
        "description_content_type": "text/markdown",
        "docs_url": None,
        "download_url": "",
        "downloads": {"last_day": -1, "last_month": -1, "last_week": -1},
        "home_page": "https://neu.ro/",
        "keywords": "",
        "license": "",
        "maintainer": "",
        "maintainer_email": "",
        "name": "apolo-cli",
        "package_url": "https://pypi.org/project/apolo-cli/",
        "platform": "",
        "project_url": "https://pypi.org/project/apolo-cli/",
        "project_urls": {"Homepage": "https://neu.ro/"},
        "release_url": "https://pypi.org/project/apolo-cli/50.1.1/",
        "requires_dist": [
            "aiohttp (>=3.0)",
            "python-jose (>=3.0.0)",
            "python-dateutil (>=2.7.0)",
            "yarl (>=1.3.0)",
            "aiodocker (>=0.14.0)",
            "click (>=4.0)",
            'dataclasses (>=0.5) ; python_version < "3.7"',
            'async-generator (>=1.5) ; python_version < "3.7"',
        ],
        "requires_python": ">=3.6.0",
        "summary": "Apolo Platform API client",
        "version": "50.1.1",
    },
    "last_serial": 4757285,
    "releases": {
        "0.2.0b0": [
            {
                "comment_text": "",
                "digests": {
                    "md5": "bc66247d61fcedb18e6dcc87f4f2bbbe",
                    "sha256": "6747274972648...abe9d8ba44f59635bac6e",
                },
                "downloads": -1,
                "filename": "apolo-cli-0.2.0b0-py3-none-any.whl",
                "has_sig": False,
                "md5_digest": "bc66247d61fcedb18e6dcc87f4f2bbbe",
                "packagetype": "bdist_wheel",
                "python_version": "py3",
                "requires_python": ">=3.6.0",
                "size": 47043,
                "upload_time": "2019-01-28T20:01:21",
                "url": "https://files.pytho...ation-50.1.1-py3-none-any.whl",
            }
        ],
        "50.1.1": [
            {
                "comment_text": "",
                "digests": {
                    "md5": "8dd303ee04215ff7f5c2e7f03a6409da",
                    "sha256": "fd50b1f904c4...af6213c363ec5a83f3168aae1b8",
                },
                "downloads": -1,
                "filename": "apolo-cli-50.1.1-py3-none-any.whl",
                "has_sig": False,
                "md5_digest": "8dd303ee04215ff7f5c2e7f03a6409da",
                "packagetype": "bdist_wheel",
                "python_version": "py3",
                "requires_python": ">=3.6.0",
                "size": 48633,
                "upload_time": "2019-01-29T23:45:22",
                "url": "https://files.pytho...ation-50.1.1-py3-none-any.whl",
            },
            {
                "comment_text": "",
                "digests": {
                    "md5": "d8cb5a5984c291e69b9b0bf34423c865",
                    "sha256": "046832c04d4e7...38f6514d0e5b9acc4939",
                },
                "downloads": -1,
                "filename": "apolo-cli-50.1.1.tar.gz",
                "has_sig": False,
                "md5_digest": "af8fea5f3df6f7f81e9c6cbc6dd7c1e8",
                "packagetype": "sdist",
                "python_version": "source",
                "requires_python": None,
                "size": 156721,
                "upload_time": "2019-01-30T00:02:23",
                "url": "https://files.pytho...ation-50.1.1.tar.gz",
            },
        ],
    },
    "urls": [
        {
            "comment_text": "",
            "digests": {
                "md5": "8dd303ee04215ff7f5c2e7f03a6409da",
                "sha256": "fd50b1f90c...c5a83f3168aae1b8",
            },
            "downloads": -1,
            "filename": "apolo-cli-50.1.1-py3-none-any.whl",
            "has_sig": False,
            "md5_digest": "8dd303ee04215ff7f5c2e7f03a6409da",
            "packagetype": "bdist_wheel",
            "python_version": "py3",
            "requires_python": ">=3.6.0",
            "size": 48633,
            "upload_time": "2019-01-29T23:45:22",
            "url": "https://files.pytho...ation-50.1.1-py3-none-any.whl",
        }
    ],
}


@pytest.fixture
def tls_certificate_authority() -> Any:
    return trustme.CA()


@pytest.fixture
def tls_certificate(tls_certificate_authority: Any) -> Any:
    return tls_certificate_authority.issue_server_cert("localhost", "127.0.0.1", "::1")


@pytest.fixture
def ssl_ctx(tls_certificate: Any) -> ssl.SSLContext:
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_certificate.configure_cert(ssl_ctx)
    return ssl_ctx


@pytest.fixture
def client_ssl_ctx(tls_certificate_authority: Any) -> ssl.SSLContext:
    ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    tls_certificate_authority.configure_trust(ssl_ctx)
    return ssl_ctx


class FakeResolver(AbstractResolver):
    _LOCAL_HOST = {0: "127.0.0.1", socket.AF_INET: "127.0.0.1", socket.AF_INET6: "::1"}

    def __init__(self, fakes: dict[str, int]) -> None:
        """fakes -- dns -> port dict"""
        self._fakes = fakes

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> list[ResolveResult]:
        return [
            {
                "hostname": host,
                "host": "127.0.0.1",
                "port": self._fakes["pypi.org"],
                "family": family,
                "proto": 0,
                "flags": socket.AI_NUMERICHOST,
            }
        ]

    async def close(self) -> None:
        pass


class FakePyPI:
    def __init__(self, ssl_context: ssl.SSLContext) -> None:
        self.app = web.Application()
        self.app.router.add_routes([web.get("/pypi/apolo-cli/json", self.json_info)])
        self.runner: web.AppRunner | None = None
        self.ssl_context = ssl_context
        self.response: tuple[int, dict[str, Any]] | None = None

    async def start(self) -> dict[str, int]:
        port = unused_port()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", port, ssl_context=self.ssl_context)
        await site.start()
        return {"pypi.org": port}

    async def stop(self) -> None:
        assert self.runner is not None
        # await asyncio.sleep(0.1)
        await self.runner.cleanup()

    async def json_info(self, request: web.Request) -> web.Response:
        assert self.response is not None
        return web.json_response(self.response[1], status=self.response[0])


@pytest.fixture()
async def fake_pypi(
    ssl_ctx: ssl.SSLContext,
) -> AsyncIterator[tuple[FakePyPI, dict[str, int]]]:
    fake_pypi = FakePyPI(ssl_ctx)
    info = await fake_pypi.start()
    yield fake_pypi, info
    await fake_pypi.stop()


APOLO_CLI_UPGRADE = """\
You are using Apolo Platform Client {old_ver}, however {new_ver} is available.
You should consider upgrading via the following command:
    python -m pip install --upgrade apolo-cli
"""


def get_apolo_cli_txt(old: str, new: str) -> str:
    return APOLO_CLI_UPGRADE.format(old_ver=old, new_ver=new)


@pytest.fixture()
async def client(
    fake_pypi: tuple[FakePyPI, dict[str, int]],
    make_client: Callable[..., Client],
) -> AsyncIterator[Client]:
    resolver = FakeResolver(fake_pypi[1])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False, keepalive_timeout=0)
    plugin_manager = PluginManager()
    plugin_manager.version_checker.register("apolo-cli", get_apolo_cli_txt)
    client = make_client("http://example.com", plugin_manager=plugin_manager)
    old_session = client._session
    client._session = aiohttp.ClientSession(connector=connector)
    client._core._session = client._session
    await old_session.close()
    yield client
    await client.close()
    await asyncio.sleep(0.5)  # can be removed for aiohttp 4.0


@pytest.fixture
def pypi_server(fake_pypi: tuple[FakePyPI, dict[str, int]]) -> FakePyPI:
    return fake_pypi[0]


async def test_update(pypi_server: FakePyPI, client: Client) -> None:
    pypi_server.response = (200, PYPI_JSON)

    t0 = time.time()
    await client.version_checker.update()
    assert len(client.version_checker._records) == 1
    record = client.version_checker._records["apolo-cli"]
    assert record["package"] == "apolo-cli"
    assert record["version"] == "50.1.1"
    assert (
        record["uploaded"] == dateutil.parser.parse("2019-01-30T00:02:23").timestamp()
    )
    assert t0 <= record["checked"] <= time.time()

    with client.config._open_db() as db:
        ret = list(db.execute("SELECT package, version FROM pypi"))
        assert len(ret) == 1
        assert list(ret[0]) == ["apolo-cli", "50.1.1"]


async def test_update_no_releases(pypi_server: FakePyPI, client: Client) -> None:
    pypi_server.response = (200, {})

    await client.version_checker.update()
    assert not client.version_checker._records


async def test_update_non_200(pypi_server: FakePyPI, client: Client) -> None:
    pypi_server.response = (403, {"Status": "Forbidden"})

    await client.version_checker.update()
    assert not client.version_checker._records


async def test_get_outdated(pypi_server: FakePyPI, client: Client) -> None:
    pypi_server.response = (200, PYPI_JSON)

    await client.version_checker.update()
    outdated = await client.version_checker.get_outdated()
    assert "apolo-cli" in outdated.keys()
