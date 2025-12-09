import asyncio
import base64
import json
import os
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest import mock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer as _TestServer
from jose import jws
from yarl import URL

from apolo_sdk import (
    PASS_CONFIG_ENV_NAME,
    AuthError,
    Cluster,
    ConfigError,
    Factory,
    Project,
    __version__,
)
from apolo_sdk._config import _AuthConfig, _AuthToken, _ConfigData
from apolo_sdk._config_factory import _choose_path
from apolo_sdk._login import JWT_STANDALONE_SECRET

from tests import _TestServerFactory


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: Any) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)  # Like as it's not enough
    if os.name == "nt" and sys.version_info >= (3, 8):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    else:
        monkeypatch.setenv("HOME", str(tmp_path))

    return tmp_path


@pytest.fixture
def config_dir(
    tmp_home: Path, token: str, auth_config: _AuthConfig, cluster_config: Cluster
) -> Path:
    config_path = tmp_home / ".apolo"
    _create_config(config_path, token, auth_config, cluster_config)
    return config_path


def _create_config(
    rc_path: Path,
    token: str,
    auth_config: _AuthConfig,
    cluster_config: Cluster,
    project: Project | None = None,
) -> str:
    config = _ConfigData(
        auth_config=auth_config,
        auth_token=_AuthToken.create_non_expiring(token),
        url=URL("https://api.dev.apolo.us/api/v1"),
        admin_url=URL("https://api.dev.apolo.us/apis/admin/v1"),
        version=__version__,
        cluster_name=cluster_config.name,
        org_name=cluster_config.orgs[0],
        clusters={cluster_config.name: cluster_config},
        projects={project.key: project} if project else {},
        project_name=project.name if project else None,
    )
    Factory(rc_path)._save(config)
    assert rc_path.exists()
    return token


@dataclass
class MockForLoginControl:
    client_id: str = "banana"


@pytest.fixture
async def mock_for_login_factory(
    aiohttp_server: _TestServerFactory,
    token: str,
    unused_tcp_port_factory: Callable[[], int],
) -> Callable[[MockForLoginControl], Awaitable[_TestServer]]:
    async def _factory(
        control: MockForLoginControl, auth_enabled: bool = True
    ) -> _TestServer:
        callback_urls = [
            f"http://127.0.0.1:{unused_tcp_port_factory()}",
            f"http://127.0.0.1:{unused_tcp_port_factory()}",
            f"http://127.0.0.1:{unused_tcp_port_factory()}",
        ]

        async def config_handler(request: web.Request) -> web.Response:
            config_json: dict[str, Any] = {
                "auth_url": str(srv.make_url("/authorize")),
                "token_url": str(srv.make_url("/oauth/token")),
                "logout_url": str(srv.make_url("/v2/logout")),
                "admin_url": str(srv.make_url("/apis/admin/v1")),
                "client_id": control.client_id,
                "audience": "https://test.api.dev.apolo.us",
                "headless_callback_url": str(srv.make_url("/oauth/show-code")),
                "callback_urls": callback_urls,
                "success_redirect_url": "http://example.com",
            }

            if not auth_enabled or (
                "Authorization" in request.headers
                and "incorrect" not in request.headers["Authorization"]
            ):
                cluster_config: dict[str, Any] = {
                    "name": "default",
                    "orgs": ["test-org"],
                    "registry_url": "https://registry-dev.test.com",
                    "storage_url": "https://storage-dev.test.com",
                    "users_url": "https://users-dev.test.com",
                    "monitoring_url": "https://monitoring-dev.test.com",
                    "secrets_url": "https://secrets-dev.test.com",
                    "disks_url": "https://disks-dev.test.com",
                    "buckets_url": "https://buckets-dev.test.com",
                    "resource_pool_types": [
                        {
                            "name": "cpu",
                            "min_size": 1,
                            "max_size": 2,
                            "cpu": 7,
                            "memory": 14 * 2**30,
                            "disk_size": 150 * 2**30,
                        },
                        {
                            "name": "nvidia-gpu",
                            "min_size": 0,
                            "max_size": 1,
                            "cpu": 7,
                            "memory": 60 * 2**30,
                            "disk_size": 150 * 2**30,
                            "nvidia_gpu": {
                                "count": 1,
                                "model": "nvidia-gpu",
                                "memory": 10**10,
                            },
                            "nvidia_migs": {
                                "1g.5gb": {
                                    "count": 1,
                                    "model": "nvidia-gpu-1g.5gb",
                                    "memory": 5 * 10**9,
                                }
                            },
                        },
                        {
                            "name": "amd-gpu",
                            "min_size": 0,
                            "max_size": 1,
                            "cpu": 7,
                            "memory": 60 * 2**30,
                            "disk_size": 150 * 2**30,
                            "amd_gpu": {"count": 1, "model": "amd-gpu"},
                        },
                        {
                            "name": "intel-gpu",
                            "min_size": 0,
                            "max_size": 1,
                            "cpu": 7,
                            "memory": 60 * 2**30,
                            "disk_size": 150 * 2**30,
                            "intel_gpu": {"count": 1, "model": "intel-gpu"},
                        },
                    ],
                    "resource_presets": [
                        {
                            "name": "nvidia-gpu-small",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 30 * 2**30,
                            "nvidia_gpu": {"count": 1},
                            "resource_pool_names": ["nvidia-gpu"],
                            "available_resource_pool_names": ["nvidia-gpu"],
                        },
                        {
                            "name": "nvidia-gpu-large",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 60 * 2**30,
                            "nvidia_gpu": {"count": 1},
                            "resource_pool_names": ["nvidia-gpu"],
                            "available_resource_pool_names": ["nvidia-gpu"],
                        },
                        {
                            "name": "nvidia-mig",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 30 * 2**30,
                            "nvidia_migs": {
                                "1g.5gb": {
                                    "count": 1,
                                    "model": "nvidia-gpu-1g.5gb",
                                    "memory": 5 * 10**9,
                                }
                            },
                            "resource_pool_names": ["nvidia-gpu"],
                            "available_resource_pool_names": ["nvidia-gpu"],
                        },
                        {
                            "name": "amd-gpu-small",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 30 * 2**30,
                            "amd_gpu": {"count": 1},
                            "resource_pool_names": ["amd-gpu"],
                            "available_resource_pool_names": ["amd-gpu"],
                        },
                        {
                            "name": "amd-gpu-large",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 60 * 2**30,
                            "amd_gpu": {"count": 1},
                            "resource_pool_names": ["amd-gpu"],
                            "available_resource_pool_names": ["amd-gpu"],
                        },
                        {
                            "name": "intel-gpu-small",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 30 * 2**30,
                            "intel_gpu": {"count": 1},
                            "resource_pool_names": ["intel-gpu"],
                            "available_resource_pool_names": ["intel-gpu"],
                        },
                        {
                            "name": "intel-gpu-large",
                            "credits_per_hour": "10",
                            "cpu": 7,
                            "memory": 60 * 2**30,
                            "intel_gpu": {"count": 1},
                            "resource_pool_names": ["intel-gpu"],
                            "available_resource_pool_names": ["intel-gpu"],
                        },
                        {
                            "name": "cpu-small",
                            "credits_per_hour": "10",
                            "cpu": 2,
                            "memory": 2 * 2**30,
                            "available_resource_pool_names": ["cpu"],
                        },
                        {
                            "name": "cpu-large",
                            "credits_per_hour": "10",
                            "cpu": 3,
                            "memory": 14 * 2**30,
                            "available_resource_pool_names": ["cpu"],
                        },
                    ],
                }
                project_config: dict[str, Any] = {
                    "cluster_name": "default",
                    "org_name": "test-org",
                    "name": "default",
                    "role": "owner",
                }
                config_json.update(
                    {
                        "authorized": True,
                        "clusters": [
                            {**cluster_config, "name": "default"},
                            {**cluster_config, "name": "default2"},
                        ],
                        "projects": [
                            project_config,
                            {**project_config, "name": "default2"},
                        ],
                    }
                )
            else:
                config_json["authorized"] = False
            return web.json_response(config_json)

        async def show_code(request: web.Request) -> web.Response:
            return web.json_response({})

        async def authorize(request: web.Request) -> web.Response:
            url = URL(request.query["redirect_uri"]).with_query(code="test_auth_code")
            raise web.HTTPSeeOther(location=url)

        async def new_token(request: web.Request) -> web.Response:
            return web.json_response(
                {"access_token": token, "expires_in": 3600, "refresh_token": token}
            )

        app = web.Application()
        app.router.add_get("/config", config_handler)
        app.router.add_get("/oauth/show-code", show_code)
        app.router.add_get("/authorize", authorize)
        app.router.add_post("/oauth/token", new_token)
        srv = await aiohttp_server(app)
        return srv

    return _factory


@pytest.fixture
async def mock_for_login(
    mock_for_login_factory: Callable[[MockForLoginControl], Awaitable[_TestServer]],
) -> _TestServer:
    return await mock_for_login_factory(MockForLoginControl())


class TestConfigFileInteraction:
    async def test_config_file_absent(self, tmp_home: Path) -> None:
        with pytest.raises(ConfigError, match=r"file.+not exists"):
            await Factory().get()

    async def test_config_dir_is_file(self, tmp_home: Path) -> None:
        Path(tmp_home / ".apolo").write_text("something")
        with pytest.raises(ConfigError, match=r"not a directory"):
            await Factory().get()

    async def test_config_file_is_dir(self, tmp_home: Path) -> None:
        path = Path(tmp_home / ".apolo")
        path.mkdir()
        (path / "db").mkdir()
        with pytest.raises(ConfigError, match=r"not a regular file"):
            await Factory().get()

    async def test_default_path(
        self,
        tmp_home: Path,
        token: str,
        auth_config: _AuthConfig,
        cluster_config: Cluster,
    ) -> None:
        token = _create_config(tmp_home / ".apolo", token, auth_config, cluster_config)
        client = await Factory().get()
        await client.close()
        assert await client.config.token() == token

    async def test_preset_serialization(
        self,
        tmp_home: Path,
        token: str,
        auth_config: _AuthConfig,
        cluster_config: Cluster,
    ) -> None:
        _create_config(tmp_home / ".apolo", token, auth_config, cluster_config)
        client = await Factory().get()
        await client.close()
        assert len(client.presets) > 0
        assert not client.presets["cpu-large"].scheduler_enabled
        assert not client.presets["cpu-large"].preemptible_node
        assert client.presets["cpu-large-p"].scheduler_enabled
        assert client.presets["cpu-large-p"].preemptible_node

    async def test_project_serialization(
        self,
        tmp_home: Path,
        token: str,
        auth_config: _AuthConfig,
        cluster_config: Cluster,
    ) -> None:
        project = Project(
            cluster_name="default",
            org_name="test_org",
            name="test-project",
            role="owner",
        )
        _create_config(tmp_home / ".apolo", token, auth_config, cluster_config, project)
        client = await Factory().get()
        await client.close()
        assert client.config.project_name == project.name
        assert dict(client.config.projects) == {project.key: project}

    async def test_shorten_path(
        self,
        tmp_home: Path,
        token: str,
        auth_config: _AuthConfig,
        cluster_config: Cluster,
    ) -> None:
        token = _create_config(
            tmp_home / "test.nmrc", token, auth_config, cluster_config
        )
        client = await Factory(Path("~/test.nmrc")).get()
        await client.close()
        assert await client.config.token() == token

    async def test_full_path(
        self,
        tmp_home: Path,
        token: str,
        auth_config: _AuthConfig,
        cluster_config: Cluster,
    ) -> None:
        config_path = tmp_home / "test.nmrc"
        token = _create_config(config_path, token, auth_config, cluster_config)
        client = await Factory(config_path).get()
        await client.close()
        assert await client.config.token() == token

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows does not supports UNIX-like permissions",
    )
    async def test_file_permissions(self, config_dir: Path) -> None:
        Path(config_dir).chmod(0o777)
        with pytest.raises(ConfigError, match=r"permission"):
            await Factory().get()


class TestLogin:
    async def show_dummy_browser(self, url: URL) -> None:
        async with aiohttp.ClientSession() as client:
            await client.get(url, allow_redirects=True)

    async def test_login_already_logged(self, config_dir: Path) -> None:
        with pytest.raises(ConfigError, match=r"already exists"):
            await Factory().login(self.show_dummy_browser)

    async def test_normal_login(
        self, tmp_home: Path, mock_for_login: _TestServer
    ) -> None:
        await Factory().login(self.show_dummy_browser, url=mock_for_login.make_url("/"))
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "

    async def test_login_to_server_without_auth(
        self,
        tmp_home: Path,
        mock_for_login_factory: Callable[..., Awaitable[_TestServer]],
    ) -> None:
        mock_for_login = await mock_for_login_factory(
            MockForLoginControl(), auth_enabled=False
        )
        await Factory().login(self.show_dummy_browser, url=mock_for_login.make_url("/"))
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "

        client = await Factory(Path(rc_path)).get()
        await client.close()
        token = await client.config.token()

        assert client.config.username == "user"
        jws.verify(
            token, JWT_STANDALONE_SECRET, algorithms="HS256"
        )  # verify it is standalone token


class TestLoginWithToken:
    async def test_login_with_token_already_logged(self, config_dir: Path) -> None:
        with pytest.raises(ConfigError, match=r"already exists"):
            await Factory().login_with_token(token="tokenstr")

    async def test_normal_login(
        self, tmp_home: Path, mock_for_login: _TestServer
    ) -> None:
        await Factory().login_with_token(
            token="tokenstr", url=mock_for_login.make_url("/")
        )
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "

    async def test_incorrect_token(
        self, tmp_home: Path, mock_for_login: _TestServer
    ) -> None:
        with pytest.raises(AuthError):
            await Factory().login_with_token(
                token="incorrect", url=mock_for_login.make_url("/")
            )
        rc_path = tmp_home / ".apolo"
        assert not Path(rc_path).exists(), "Config file not written after login "


class TestLoginPassedConfig:
    @pytest.fixture()
    def make_conf_data(
        self, mock_for_login: _TestServer
    ) -> Callable[[str, str | None, str | None], str]:
        def _make_config(
            token: str,
            project_name: str | None = "default",
            org_name: str | None = "test-org",
        ) -> str:
            data = {
                "token": token,
                "cluster": "default",
                "url": str(mock_for_login.make_url("/")),
                "org_name": org_name,
                "project_name": project_name,
            }
            return base64.b64encode(json.dumps(data).encode()).decode()

        return _make_config

    @pytest.fixture()
    def set_conf_to_env(
        self,
        monkeypatch: Any,
        make_conf_data: Callable[[str, str | None, str | None], str],
    ) -> Callable[[str], None]:
        def _set_env(token: str) -> None:
            config_data = make_conf_data(token)  # type: ignore
            monkeypatch.setenv(PASS_CONFIG_ENV_NAME, config_data)

        return _set_env

    async def test_login_with_passed_config_already_logged(
        self, set_conf_to_env: Callable[[str], None], config_dir: Path
    ) -> None:
        set_conf_to_env("tokenstr")
        with pytest.raises(ConfigError, match=r"already exists"):
            await Factory().login_with_passed_config()

    async def test_auto_login(
        self, tmp_home: Path, set_conf_to_env: Callable[[str], None]
    ) -> None:
        set_conf_to_env("tokenstr")
        client = await Factory().get()
        await client.close()
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "

    async def test_auto_login_fail(
        self, tmp_home: Path, set_conf_to_env: Callable[[str], None]
    ) -> None:
        set_conf_to_env("incorrect")
        with pytest.raises(AuthError):
            await Factory().get()
        rc_path = tmp_home / ".apolo"
        assert not Path(rc_path).exists(), "Config file not written after login "

    async def test_normal_login(
        self, tmp_home: Path, set_conf_to_env: Callable[[str], None]
    ) -> None:
        set_conf_to_env("tokenstr")
        await Factory().login_with_passed_config()
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "

    async def test_normal_login_direct_token(
        self,
        tmp_home: Path,
        make_conf_data: Callable[[str, str | None, str | None], str],
    ) -> None:
        token_data = make_conf_data("tokenstr")  # type: ignore
        await Factory().login_with_passed_config(token_data)
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "

    async def test_incorrect_token(
        self, tmp_home: Path, set_conf_to_env: Callable[[str], None]
    ) -> None:
        set_conf_to_env("incorrect")
        with pytest.raises(AuthError):
            await Factory().login_with_passed_config()
        rc_path = tmp_home / ".apolo"
        assert not Path(rc_path).exists(), "Config file written after bad login "

    async def test_bad_data(
        self,
        tmp_home: Path,
        monkeypatch: Any,
    ) -> None:
        monkeypatch.setenv(PASS_CONFIG_ENV_NAME, "something")
        with pytest.raises(ConfigError):
            await Factory().login_with_passed_config()
        rc_path = tmp_home / ".apolo"
        assert not Path(rc_path).exists(), "Config file written after bad login "

    async def test_no_data(
        self,
        tmp_home: Path,
        monkeypatch: Any,
    ) -> None:
        with pytest.raises(ConfigError):
            await Factory().login_with_passed_config()
        rc_path = tmp_home / ".apolo"
        assert not Path(rc_path).exists(), "Config file written after bad login "

    async def test_login_project_set(
        self,
        tmp_home: Path,
        monkeypatch: Any,
        make_conf_data: Callable[[str, str | None], str],
    ) -> None:
        pass_cfg_data = make_conf_data("tokenstr", "default2")
        monkeypatch.setenv(PASS_CONFIG_ENV_NAME, pass_cfg_data)
        client = await Factory().get()
        await client.close()
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "
        assert client.config.project_name == "default2"
        assert client.config.org_name == "test-org"


class TestHeadlessLogin:
    async def test_login_headless_already_logged(self, config_dir: Path) -> None:
        async def get_auth_code_cb(url: URL) -> str:
            return ""

        with pytest.raises(ConfigError, match=r"already exists"):
            await Factory().login_headless(get_auth_code_cb)

    async def test_normal_login(
        self, tmp_home: Path, mock_for_login: _TestServer
    ) -> None:
        async def get_auth_code_cb(url: URL) -> str:
            assert url.with_query(None) == mock_for_login.make_url("/authorize")

            assert dict(url.query) == {
                "response_type": "code",
                "code_challenge": mock.ANY,
                "code_challenge_method": "S256",
                "client_id": "banana",
                "redirect_uri": str(mock_for_login.make_url("/oauth/show-code")),
                "scope": "offline_access",
                "audience": "https://test.api.dev.apolo.us",
            }
            return "test_code"

        await Factory().login_headless(
            get_auth_code_cb, url=mock_for_login.make_url("/")
        )
        rc_path = tmp_home / ".apolo"
        assert Path(rc_path).exists(), "Config file not written after login "


class TestLogout:
    async def test_logout_no_browser_callback(self, config_dir: Path) -> None:
        await Factory().logout()
        assert not config_dir.exists(), "Config not removed after logout\n" + "\n".join(
            p.name for p in config_dir.iterdir()
        )

    async def test_logout_with_browser_callback(
        self, auth_config: _AuthConfig, config_dir: Path
    ) -> None:
        async def show_browser(url: URL) -> None:
            expected_logout_url = auth_config.logout_url.with_query(
                client_id=auth_config.client_id
            )
            assert url == expected_logout_url

        await Factory().logout(show_browser)
        assert not config_dir.exists(), "Config not removed after logout\n" + "\n".join(
            p.name for p in config_dir.iterdir()
        )


class TestConfigRecovery:
    async def show_dummy_browser(self, url: URL) -> None:
        async with aiohttp.ClientSession() as client:
            await client.get(url, allow_redirects=True)

    async def test_recovery(
        self,
        tmp_home: Path,
        mock_for_login_factory: Callable[[MockForLoginControl], Awaitable[_TestServer]],
    ) -> None:
        control = MockForLoginControl(client_id="test1")
        mock_for_login = await mock_for_login_factory(control)
        await Factory().login(self.show_dummy_browser, url=mock_for_login.make_url("/"))
        with mock.patch("apolo_sdk.__version__", "21.13.13"):  # Impossible version
            # AS: I have no idea why we change client_id in tests,
            # it leads to auth_config mismatch
            # control.client_id = "test2"
            client = await Factory().get()
            assert client.config._config_data.version == "21.13.13"
            await client.close()

        await mock_for_login.close()
        await asyncio.sleep(0.01)

    async def test_recovery_cluster_is_preserved(
        self,
        tmp_home: Path,
        mock_for_login_factory: Callable[[MockForLoginControl], Awaitable[_TestServer]],
    ) -> None:
        control = MockForLoginControl(client_id="test1")
        mock_for_login = await mock_for_login_factory(control)
        await Factory().login(self.show_dummy_browser, url=mock_for_login.make_url("/"))
        async with await Factory().get() as client:
            await client.config.switch_cluster("default2")

        with mock.patch("apolo_sdk.__version__", "21.13.13"):  # Impossible version
            # AS: I have no idea why we change client_id in tests,
            # it leads to auth_config mismatch
            # control.client_id = "test2"
            client = await Factory().get()
            assert client.config.cluster_name == "default2"
            await client.close()

        await mock_for_login.close()
        await asyncio.sleep(0.01)


class TestChoosePath:
    def test_explicit(self, tmp_home: Path) -> None:
        path = tmp_home / "explicit"
        assert _choose_path(path) == path

    def test_default(self, tmp_home: Path) -> None:
        assert _choose_path(None) == Path("~/.apolo").expanduser()

    def test_fallback(self, tmp_home: Path) -> None:
        path = tmp_home / ".neuro"
        path.mkdir()
        (path / "db").write_text("")
        assert _choose_path(None) == path

    def test_default_wins(self, tmp_home: Path) -> None:
        path = tmp_home / ".apolo"
        path.mkdir()
        old_path = tmp_home / ".neuro"
        old_path.mkdir()
        (path / "db").write_text("")
        assert _choose_path(None) == path

    def test_config_overrides(self, tmp_home: Path, monkeypatch: Any) -> None:
        path = tmp_home / "config_overrride"
        path.mkdir()
        (path / "db").write_text("")
        monkeypatch.setenv("APOLO_CONFIG", str(path))
        assert _choose_path(None) == path

    def test_old_config_overrides(self, tmp_home: Path, monkeypatch: Any) -> None:
        path = tmp_home / "old_config_overrride"
        path.mkdir()
        (path / "db").write_text("")
        monkeypatch.setenv("NEUROMATION_CONFIG", str(path))
        assert _choose_path(None) == path
