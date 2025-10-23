from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict
from unittest import mock
from urllib.parse import parse_qsl

import pytest
import toml
from aiohttp import web
from yarl import URL

from apolo_sdk import (
    AppsConfig,
    Client,
    Cluster,
    ConfigError,
    ConfigScope,
    PluginManager,
    Preset,
    Project,
    ResourcePool,
)
from apolo_sdk._config import (
    _check_sections,
    _merge_user_configs,
    _validate_user_config,
)
from apolo_sdk._login import _AuthToken
from apolo_sdk._server_cfg import AMDGPUPreset, IntelGPUPreset, NvidiaGPUPreset

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


@pytest.fixture()
def plugin_manager() -> PluginManager:
    manager = PluginManager()
    manager.config.define_str("job", "ps-format")
    manager.config.define_str("job", "top-format")
    manager.config.define_str("job", "life-span")
    manager.config.define_str("job", "cluster-name", scope=ConfigScope.LOCAL)
    manager.config.define_str("job", "org-name", scope=ConfigScope.LOCAL)
    manager.config.define_str_list("storage", "cp-exclude")
    manager.config.define_str_list("storage", "cp-exclude-from-files")
    return manager


class TestMergeUserConfigs:
    def test_empty_dicts(self) -> None:
        assert _merge_user_configs({}, {}) == {}

    def test_empty_newer(self) -> None:
        assert _merge_user_configs({"a": "b"}, {}) == {"a": "b"}

    def test_empty_older(self) -> None:
        assert _merge_user_configs({}, {"a": "b"}) == {"a": "b"}

    def test_not_overlapped(self) -> None:
        assert _merge_user_configs({"a": "b"}, {"c": "d"}) == {"a": "b", "c": "d"}

    def test_merge_subdicts(self) -> None:
        assert _merge_user_configs(
            {"a": {"b": "1", "c": "2"}}, {"a": {"b": "3", "d": "4"}}
        ) == {"a": {"b": "3", "c": "2", "d": "4"}}


class TestUserConfigValidators:
    def test_unsupported_section(self) -> None:
        with pytest.raises(
            ConfigError, match="file.cfg: unsupported config sections: {'other'}"
        ):
            _check_sections({"other": {"key": "val"}}, {"section"}, "file.cfg")

    def test_section_is_not_dict(self) -> None:
        with pytest.raises(
            ConfigError, match="file.cfg: 'a' should be a section, got 1"
        ):
            _check_sections({"a": 1}, {"a"}, "file.cfg")

    def test_invalid_alias_name(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(ConfigError, match="file.cfg: invalid alias name 0123"):
            _validate_user_config(plugin_manager, {"alias": {"0123": "ls"}}, "file.cfg")

    def test_invalid_alias_type(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(ConfigError, match="file.cfg: invalid alias command type"):
            _validate_user_config(
                plugin_manager, {"alias": {"new-name": True}}, "file.cfg"
            )

    def test_extra_session_param(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(
            ConfigError, match="file.cfg: unknown parameters job.unknown-name"
        ):
            _validate_user_config(
                plugin_manager, {"job": {"unknown-name": True}}, "file.cfg"
            )

    def test_invalid_param_type(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(
            ConfigError,
            match="file.cfg: invalid type for job.ps-format, str is expected",
        ):
            _validate_user_config(
                plugin_manager, {"job": {"ps-format": True}}, "file.cfg"
            )

    def test_invalid_complex_type(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(
            ConfigError,
            match="file.cfg: invalid type for storage.cp-exclude, list is expected",
        ):
            _validate_user_config(
                plugin_manager, {"storage": {"cp-exclude": "abc"}}, "file.cfg"
            )

    def test_invalid_complex_item_type(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(
            ConfigError,
            match=(
                r"file.cfg: invalid type for storage.cp-exclude\[0\], "
                "str is expected"
            ),
        ):
            _validate_user_config(
                plugin_manager, {"storage": {"cp-exclude": [1, 2]}}, "file.cfg"
            )

    def test_not_allowed_cluster_name(self, plugin_manager: PluginManager) -> None:
        with pytest.raises(ConfigError, match=r"file.cfg: cluster name is not allowed"):
            _validate_user_config(
                plugin_manager, {"job": {"cluster-name": "another"}}, "file.cfg"
            )


async def test_get_user_config_empty(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        assert await client.config.get_user_config() == {}


async def test_get_user_config_from_global(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        client.config._path.mkdir(parents=True, exist_ok=True)
        global_conf = client.config._path / "user.toml"
        # FIXME: the example may be broken in future versions
        global_conf.write_text(
            toml.dumps({"alias": {"pss": {"cmd": "job ps --short"}}})
        )
        assert await client.config.get_user_config() == {
            "alias": {"pss": {"cmd": "job ps --short"}}
        }


async def test_get_user_config_from_local(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    async with make_client("https://example.com") as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        local_conf = proj_dir / ".apolo.toml"
        # FIXME: the example may be broken in future versions
        local_conf.write_text(toml.dumps({"alias": {"pss": {"cmd": "job ps --short"}}}))
        assert await client.config.get_user_config() == {
            "alias": {"pss": {"cmd": "job ps --short"}}
        }


@pytest.fixture
def multiple_clusters_config() -> Dict[str, Cluster]:
    return {
        "default": Cluster(
            name="default",
            orgs=["test-org", "test-org"],
            registry_url=URL("https://registry-api.dev.apolo.us"),
            storage_url=URL("https://storage-api.dev.apolo.us"),
            users_url=URL("https://users-api.dev.apolo.us"),
            monitoring_url=URL("https://jobs-api.dev.apolo.us"),
            secrets_url=URL("https://secrets-api.dev.apolo.us"),
            disks_url=URL("https://disks-api.dev.apolo.us"),
            buckets_url=URL("https://buckets-api.dev.apolo.us"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                )
            },
            presets={
                "cpu-small": Preset(
                    credits_per_hour=Decimal("10"),
                    cpu=1,
                    memory=2 * 2**30,
                )
            },
            apps=AppsConfig(hostname_templates=["{name}.api.dev.apolo.us"]),
        ),
        "another": Cluster(
            name="another",
            orgs=["some-org", "test-org"],
            registry_url=URL("https://registry2-api.dev.apolo.us"),
            storage_url=URL("https://storage2-api.dev.apolo.us"),
            users_url=URL("https://users2-api.dev.apolo.us"),
            monitoring_url=URL("https://jobs2-api.dev.apolo.us"),
            secrets_url=URL("https://secrets2-api.dev.apolo.us"),
            disks_url=URL("https://disks2-api.dev.apolo.us"),
            buckets_url=URL("https://buckets2-api.dev.apolo.us"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                )
            },
            presets={
                "cpu-large": Preset(
                    credits_per_hour=Decimal("10"),
                    cpu=7,
                    memory=14 * 2**30,
                )
            },
            apps=AppsConfig(hostname_templates=["{name}.api.dev.apolo.us"]),
        ),
        "third": Cluster(
            name="third",
            orgs=["some-org", "a-org"],
            registry_url=URL("https://registry3-api.dev.apolo.us"),
            storage_url=URL("https://storage3-api.dev.apolo.us"),
            users_url=URL("https://users3-api.dev.apolo.us"),
            monitoring_url=URL("https://jobs3-api.dev.apolo.us"),
            secrets_url=URL("https://secrets3-api.dev.apolo.us"),
            disks_url=URL("https://disks3-api.dev.apolo.us"),
            buckets_url=URL("https://buckets3-api.dev.apolo.us"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                )
            },
            presets={
                "cpu-large": Preset(
                    credits_per_hour=Decimal("10"),
                    cpu=7,
                    memory=14 * 2**30,
                )
            },
            apps=AppsConfig(hostname_templates=["{name}.api.dev.apolo.us"]),
        ),
    }


async def test_get_cluster_name_from_local(
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
    multiple_clusters_config: Dict[str, Cluster],
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "cluster-name", scope=ConfigScope.LOCAL)
    async with make_client(
        "https://example.org",
        clusters=multiple_clusters_config,
        plugin_manager=plugin_manager,
    ) as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        assert client.config.cluster_name == "default"
        assert client.config.registry_url == URL("https://registry-api.dev.apolo.us")
        assert client.config.storage_url == URL("https://storage-api.dev.apolo.us")
        assert client.config.monitoring_url == URL("https://jobs-api.dev.apolo.us")
        assert client.config.secrets_url == URL("https://secrets-api.dev.apolo.us")
        assert client.config.disk_api_url == URL("https://disks-api.dev.apolo.us")
        assert client.config.bucket_api_url == URL("https://buckets-api.dev.apolo.us")
        assert client.config.presets == {
            "cpu-small": Preset(
                credits_per_hour=Decimal("10"),
                cpu=1,
                memory=2 * 2**30,
                resource_pool_names=(),
            )
        }

        local_conf = proj_dir / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"cluster-name": "another"}}))
        assert client.config.cluster_name == "another"
        assert client.config.registry_url == URL("https://registry2-api.dev.apolo.us")
        assert client.config.storage_url == URL("https://storage2-api.dev.apolo.us")
        assert client.config.monitoring_url == URL("https://jobs2-api.dev.apolo.us")
        assert client.config.secrets_url == URL("https://secrets2-api.dev.apolo.us")
        assert client.config.disk_api_url == URL("https://disks2-api.dev.apolo.us")
        assert client.config.bucket_api_url == URL("https://buckets2-api.dev.apolo.us")
        assert client.config.presets == {
            "cpu-large": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=14 * 2**30,
                resource_pool_names=(),
            )
        }


async def test_get_cluster_name_from_local_invalid_cluster(
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
    multiple_clusters_config: Dict[str, Cluster],
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "cluster-name", scope=ConfigScope.LOCAL)
    async with make_client(
        "https://example.org", plugin_manager=plugin_manager
    ) as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        assert client.config.cluster_name == "default"

        local_conf = proj_dir / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"cluster-name": "unknown"}}))
        assert client.config.cluster_name == "unknown"
        match = "Cluster unknown doesn't exist.*Please edit local user config file"
        with pytest.raises(RuntimeError, match=match):
            client.config.registry_url
        with pytest.raises(RuntimeError, match=match):
            client.config.storage_url
        with pytest.raises(RuntimeError, match=match):
            client.config.monitoring_url
        with pytest.raises(RuntimeError, match=match):
            client.config.secrets_url
        with pytest.raises(RuntimeError, match=match):
            client.config.presets


async def test_username(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        assert client.config.username == "user"


async def test_presets(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        assert client.config.presets == {
            "cpu-large": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=14336 * 2**20,
                scheduler_enabled=False,
                resource_pool_names=(),
            ),
            "cpu-small": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=2048 * 2**20,
                scheduler_enabled=False,
                resource_pool_names=(),
            ),
            "nvidia-gpu-large": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=61440 * 2**20,
                scheduler_enabled=False,
                nvidia_gpu=NvidiaGPUPreset(count=1),
                resource_pool_names=("nvidia-gpu",),
            ),
            "nvidia-gpu-small": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=30720 * 2**20,
                scheduler_enabled=False,
                nvidia_gpu=NvidiaGPUPreset(count=1, model="nvidia-gpu", memory=10**10),
                resource_pool_names=("nvidia-gpu",),
            ),
            "amd-gpu-large": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=61440 * 2**20,
                scheduler_enabled=False,
                amd_gpu=AMDGPUPreset(count=1),
                resource_pool_names=("amd-gpu",),
            ),
            "amd-gpu-small": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=30720 * 2**20,
                scheduler_enabled=False,
                amd_gpu=AMDGPUPreset(count=1),
                resource_pool_names=("amd-gpu",),
            ),
            "intel-gpu-large": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=61440 * 2**20,
                scheduler_enabled=False,
                intel_gpu=IntelGPUPreset(count=1),
                resource_pool_names=("intel-gpu",),
            ),
            "intel-gpu-small": Preset(
                credits_per_hour=Decimal("10"),
                cpu=7,
                memory=30720 * 2**20,
                scheduler_enabled=False,
                intel_gpu=IntelGPUPreset(count=1),
                resource_pool_names=("intel-gpu",),
            ),
        }


async def test_cluster_name(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        assert client.config.cluster_name == "default"


async def test_no_cluster_name(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), clusters={}) as client:
        with pytest.raises(RuntimeError, match="There are no clusters available"):
            client.config.cluster_name


async def test_clusters(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        assert dict(client.config.clusters) == {
            "default": Cluster(
                name="default",
                orgs=["test-org"],
                registry_url=URL("https://registry-api.dev.apolo.us"),
                storage_url=srv.make_url("/storage"),
                users_url=srv.make_url("/"),
                monitoring_url=srv.make_url("/jobs"),
                secrets_url=srv.make_url("/secrets"),
                disks_url=srv.make_url("/disk"),
                buckets_url=srv.make_url("/buckets"),
                resource_pools=mock.ANY,
                presets=mock.ANY,
                apps=AppsConfig(hostname_templates=["{app_name}.default.neu.ro"]),
            ),
            "another": Cluster(
                name="another",
                orgs=["test-org", "some_org"],
                registry_url=srv.make_url("/registry2"),
                storage_url=srv.make_url("/storage2"),
                users_url=srv.make_url("/"),
                monitoring_url=srv.make_url("/jobs2"),
                secrets_url=srv.make_url("/secrets2"),
                disks_url=srv.make_url("/disk2"),
                buckets_url=srv.make_url("/buckets2"),
                resource_pools=mock.ANY,
                presets=mock.ANY,
                apps=AppsConfig(hostname_templates=["{app_name2}.default.neu.ro"]),
            ),
        }


async def test_org_names(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        assert client.config.available_orgs == ("some_org", "test-org")


async def test_project_name(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        assert client.config.project_name == "test-project"


async def test_projects(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    app = web.Application()
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        projects = {}
        for cluster in client.config.clusters.values():
            project = Project(
                cluster_name=cluster.name,
                org_name=cluster.orgs[0],
                name="test-project",
                role="owner",
            )
            project_other = Project(
                cluster_name=cluster.name,
                org_name=cluster.orgs[0],
                name="other-test-project",
                role="owner",
            )
            projects.update({project.key: project, project_other.key: project_other})

        assert dict(client.config.projects) == projects


async def test_fetch(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    admin_url = "https://admin-api.dev.apolo.us"
    registry_url = "https://registry2-api.dev.apolo.us"
    storage_url = "https://storage2-api.dev.apolo.us"
    users_url = "https://users2-api.dev.apolo.us"
    monitoring_url = "https://jobs2-api.dev.apolo.us"
    secrets_url = "https://secrets2-api.dev.apolo.us"
    disks_url = "https://disks2-api.dev.apolo.us"
    buckets_url = "https://buckets2-api.dev.apolo.us"
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us."
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "authorized": True,
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "headless_callback_url": headless_callback_url,
        "success_redirect_url": success_redirect_url,
        "admin_url": admin_url,
        "clusters": [
            {
                "name": "default",
                "orgs": ["test-org", "some-org"],
                "registry_url": registry_url,
                "storage_url": storage_url,
                "users_url": users_url,
                "monitoring_url": monitoring_url,
                "secrets_url": secrets_url,
                "disks_url": disks_url,
                "buckets_url": buckets_url,
                "resource_pool_types": [
                    {
                        "name": "cpu",
                        "min_size": 1,
                        "max_size": 2,
                        "cpu": 7,
                        "memory": 14 * 2**30,
                        "disk_size": 150 * 2**30,
                    }
                ],
                "resource_presets": [
                    {
                        "name": "cpu-small",
                        "credits_per_hour": "10",
                        "cpu": 2,
                        "memory": 2 * 2**30,
                    }
                ],
            }
        ],
        "projects": [
            {
                "name": "some-project",
                "cluster_name": "default",
                "org_name": "test-org",
                "role": "admin",
            }
        ],
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.add_routes([web.get("/config", handler)])
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        await client.config.fetch()
        assert client.config.clusters == {
            "default": Cluster(
                name="default",
                orgs=["test-org", "some-org"],
                registry_url=URL(registry_url),
                storage_url=URL(storage_url),
                users_url=URL(users_url),
                monitoring_url=URL(monitoring_url),
                secrets_url=URL(secrets_url),
                disks_url=URL(disks_url),
                buckets_url=URL(buckets_url),
                resource_pools={
                    "cpu": ResourcePool(
                        min_size=1,
                        max_size=2,
                        cpu=7,
                        memory=14 * 2**30,
                        disk_size=150 * 2**30,
                    )
                },
                presets={
                    "cpu-small": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=2,
                        memory=2048 * 2**20,
                        scheduler_enabled=False,
                    )
                },
                apps=AppsConfig(hostname_templates=()),
            )
        }

        project = Project(
            name="some-project",
            cluster_name="default",
            org_name="test-org",
            role="admin",
        )
        assert client.config.projects == {project.key: project}


async def test_fetch_without_admin_url(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    registry_url = "https://registry2-api.dev.apolo.us"
    storage_url = "https://storage2-api.dev.apolo.us"
    users_url = "https://users2-api.dev.apolo.us"
    monitoring_url = "https://jobs2-api.dev.apolo.us"
    secrets_url = "https://secrets2-api.dev.apolo.us"
    disks_url = "https://disks2-api.dev.apolo.us"
    buckets_url = "https://buckets2-api.dev.apolo.us"
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us."
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "authorized": True,
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "headless_callback_url": headless_callback_url,
        "success_redirect_url": success_redirect_url,
        "clusters": [
            {
                "name": "default",
                "orgs": ["test-org", "some-org"],
                "registry_url": registry_url,
                "storage_url": storage_url,
                "users_url": users_url,
                "monitoring_url": monitoring_url,
                "secrets_url": secrets_url,
                "disks_url": disks_url,
                "buckets_url": buckets_url,
                "resource_pool_types": [
                    {
                        "name": "cpu",
                        "min_size": 1,
                        "max_size": 2,
                        "cpu": 7,
                        "memory": 14 * 2**30,
                        "disk_size": 150 * 2**30,
                    }
                ],
                "resource_presets": [
                    {
                        "name": "cpu-small",
                        "credits_per_hour": "10",
                        "cpu": 2,
                        "memory": 2 * 2**30,
                    }
                ],
            }
        ],
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.add_routes([web.get("/config", handler)])
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/"), admin_url=None) as client:
        await client.config.fetch()
        assert client.config.admin_url is None


async def test_fetch_dropped_selected_cluster(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    # the test returns the same as for valid answer but the cluster name is different
    admin_url = "https://admin-api.dev.apolo.us"
    registry_url = "https://registry2-api.dev.apolo.us"
    storage_url = "https://storage2-api.dev.apolo.us"
    users_url = "https://users2-api.dev.apolo.us"
    monitoring_url = "https://jobs2-api.dev.apolo.us"
    secrets_url = "https://secrets2-api.dev.apolo.us"
    disks_url = "https://disks2-api.dev.apolo.us"
    buckets_url = "https://buckets2-api.dev.apolo.us"
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.dev.neuro.io"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "authorized": True,
        "admin_url": admin_url,
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "headless_callback_url": headless_callback_url,
        "success_redirect_url": success_redirect_url,
        "clusters": [
            {
                "name": "another",
                "registry_url": registry_url,
                "storage_url": storage_url,
                "users_url": users_url,
                "monitoring_url": monitoring_url,
                "secrets_url": secrets_url,
                "disks_url": disks_url,
                "buckets_url": buckets_url,
                "resource_pool_types": [
                    {
                        "name": "cpu",
                        "min_size": 1,
                        "max_size": 2,
                        "cpu": 7,
                        "memory": 14 * 2**30,
                        "disk_size": 150 * 2**30,
                    }
                ],
                "resource_presets": [
                    {
                        "name": "cpu-small",
                        "credits_per_hour": "10",
                        "cpu": 2,
                        "memory": 2 * 2**30,
                    }
                ],
            }
        ],
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.add_routes([web.get("/config", handler)])
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        with pytest.raises(RuntimeError, match="Cluster default doesn't exist"):
            await client.config.fetch()


async def test_switch_clusters(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        assert client.config.cluster_name == "default"
        await client.config.switch_cluster("another")
        assert client.config.cluster_name == "another"


async def test_switch_cluster_keep_org(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        await client.config.switch_cluster("another")
        await client.config.switch_org("some-org")
        assert client.config.cluster_name == "another"
        assert client.config.org_name == "some-org"
        await client.config.switch_cluster("third")
        assert client.config.cluster_name == "third"
        assert client.config.org_name == "some-org"


async def test_switch_cluster_cant_keep_org_use_none(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        await client.config.switch_cluster("default")
        await client.config.switch_org("test-org")
        assert client.config.cluster_name == "default"
        assert client.config.org_name == "test-org"
        await client.config.switch_cluster("another")
        assert client.config.cluster_name == "another"
        assert client.config.org_name == "test-org"


async def test_switch_cluster_cant_keep_org_use_alphabetical(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        await client.config.switch_cluster("default")
        await client.config.switch_org("test-org")
        assert client.config.cluster_name == "default"
        assert client.config.org_name == "test-org"
        await client.config.switch_cluster("third")
        assert client.config.cluster_name == "third"
        assert client.config.org_name == "a-org"


async def test_switch_cluster_keep_project(make_client: _MakeClient) -> None:
    async with make_client("https://example.org") as client:
        assert client.config.cluster_name == "default"
        assert client.config.project_name == "test-project"
        await client.config.switch_cluster("another")
        assert client.config.cluster_name == "another"
        assert client.config.project_name == "test-project"


async def test_switch_cluster_cant_keep_project_use_none(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        assert client.config.cluster_name == "default"
        assert client.config.project_name == "test-project"
        await client.config.switch_cluster("another")
        assert client.config.cluster_name == "another"
        assert client.config.project_name is None


async def test_switch_cluster_cant_keep_project_use_alphabetical(
    make_client: _MakeClient,
) -> None:
    async with make_client("https://example.org") as client:
        assert client.config.cluster_name == "default"
        assert client.config.project_name == "test-project"
        await client.config.switch_cluster("another")
        await client.config.switch_org("some_org")
        assert client.config.cluster_name == "another"
        assert client.config.project_name is None
        await client.config.switch_cluster("default")
        assert client.config.cluster_name == "default"
        assert client.config.project_name == "other-test-project"


async def test_switch_org(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        assert client.config.org_name == "test-org"
        await client.config.switch_org("test-org")
        assert client.config.org_name == "test-org"


async def test_switch_org_select_first_available_cluster(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        assert client.config.org_name == "test-org"
        await client.config.switch_org("some-org")
        assert client.config.org_name == "some-org"
        assert client.config.cluster_name == "another"


async def test_switch_org_keep_project_use_none(make_client: _MakeClient) -> None:
    async with make_client("https://example.org") as client:
        await client.config.switch_cluster("another")
        assert client.config.org_name == "test-org"
        assert client.config.project_name == "test-project"
        await client.config.switch_org("some_org")
        assert client.config.org_name == "some_org"
        assert client.config.project_name is None


async def test_switch_org_keep_project_use_alphabetical(
    make_client: _MakeClient,
) -> None:
    async with make_client("https://example.org") as client:
        await client.config.switch_cluster("another")
        await client.config.switch_org("some_org")
        assert client.config.org_name == "some_org"
        assert client.config.project_name is None
        await client.config.switch_org("test-org")
        assert client.config.org_name == "test-org"
        assert client.config.project_name == "other-test-project"


async def test_switch_clusters_unknown(make_client: _MakeClient) -> None:
    async with make_client("https://example.org") as client:
        assert client.config.cluster_name == "default"
        with pytest.raises(RuntimeError, match="Cluster unknown doesn't exist"):
            await client.config.switch_cluster("unknown")
        assert client.config.cluster_name == "default"


async def test_switch_org_unknown(
    make_client: _MakeClient, multiple_clusters_config: Dict[str, Cluster]
) -> None:
    async with make_client(
        "https://example.org", clusters=multiple_clusters_config
    ) as client:
        assert client.config.org_name == "test-org"
        with pytest.raises(
            RuntimeError, match="Cannot find available cluster for org unknown"
        ):
            await client.config.switch_org("unknown")
        assert client.config.org_name == "test-org"


async def test_switch_clusters_local(
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
    multiple_clusters_config: Dict[str, Cluster],
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "cluster-name", scope=ConfigScope.LOCAL)
    async with make_client(
        "https://example.org",
        clusters=multiple_clusters_config,
        plugin_manager=plugin_manager,
    ) as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        local_conf = proj_dir / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"cluster-name": "another"}}))
        assert client.config.cluster_name == "another"
        with pytest.raises(RuntimeError, match=r"\.apolo\.toml"):
            await client.config.switch_cluster("default")
        assert client.config.cluster_name == "another"


async def test_switch_org_local(
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
    multiple_clusters_config: Dict[str, Cluster],
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "org-name", scope=ConfigScope.LOCAL)
    async with make_client(
        "https://example.org",
        clusters=multiple_clusters_config,
        plugin_manager=plugin_manager,
    ) as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        local_conf = proj_dir / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"org-name": "test-org"}}))
        assert client.config.org_name == "test-org"
        with pytest.raises(RuntimeError, match=r"\.apolo\.toml"):
            await client.config.switch_org("not-exists")
        assert client.config.org_name == "test-org"


async def test_no_org_local(
    monkeypatch: Any,
    tmp_path: Path,
    make_client: _MakeClient,
    multiple_clusters_config: Dict[str, Cluster],
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "org-name", scope=ConfigScope.LOCAL)
    async with make_client(
        "https://example.org",
        clusters=multiple_clusters_config,
        plugin_manager=plugin_manager,
    ) as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        local_conf = proj_dir / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"org-name": "test-org"}}))
        assert client.config.org_name == "test-org"


async def test_switch_project(make_client: _MakeClient) -> None:
    async with make_client("https://example.org") as client:
        assert client.config.project_name == "test-project"
        await client.config.switch_project("other-test-project")
        assert client.config.project_name == "other-test-project"


async def test_switch_project_unknown(make_client: _MakeClient) -> None:
    async with make_client("https://example.org") as client:
        assert client.config.project_name == "test-project"
        with pytest.raises(RuntimeError, match="Project unknown doesn't exist"):
            await client.config.switch_project("unknown")
        assert client.config.project_name == "test-project"


async def test_switch_project_local(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "project-name", scope=ConfigScope.LOCAL)
    async with make_client(
        "https://example.org", plugin_manager=plugin_manager
    ) as client:
        proj_dir = tmp_path / "project"
        local_dir = proj_dir / "folder"
        local_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(local_dir)
        local_conf = proj_dir / ".apolo.toml"
        local_conf.write_text(toml.dumps({"job": {"project-name": "test-project"}}))
        assert client.config.project_name == "test-project"
        with pytest.raises(RuntimeError, match=r"\.apolo\.toml"):
            await client.config.switch_project("test-project")
        assert client.config.project_name == "test-project"


async def test_check_server_mismatch_clusters(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    # the test returns the same as for valid answer but the cluster name is different

    admin_url = "https://admin-api.dev.apolo.us"
    registry_url = "https://registry2-api.dev.apolo.us"
    storage_url = "https://storage2-api.dev.apolo.us"
    users_url = "https://users2-api.dev.apolo.us"
    monitoring_url = "https://jobs2-api.dev.apolo.us"
    secrets_url = "https://secrets2-api.dev.apolo.us"
    disks_url = "https://disks2-api.dev.apolo.us"
    buckets_url = "https://buckets2-api.dev.apolo.us"
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "authorized": True,
        "admin_url": admin_url,
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "headless_callback_url": headless_callback_url,
        "success_redirect_url": success_redirect_url,
        "clusters": [
            {
                "name": "another",
                "registry_url": registry_url,
                "storage_url": storage_url,
                "users_url": users_url,
                "monitoring_url": monitoring_url,
                "secrets_url": secrets_url,
                "disks_url": disks_url,
                "buckets_url": buckets_url,
                "resource_pool_types": [
                    {
                        "name": "cpu",
                        "min_size": 1,
                        "max_size": 2,
                        "cpu": 7,
                        "memory": 14 * 2**30,
                        "disk_size": 150 * 2**30,
                    }
                ],
                "resource_presets": [
                    {
                        "name": "cpu-small",
                        "credits_per_hour": "10",
                        "cpu": 2,
                        "memory": 2 * 2**30,
                    }
                ],
            }
        ],
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.add_routes([web.get("/config", handler)])
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        # Set expired version
        client.config._config_data.__dict__["version"] = "18.1.1"

        with pytest.raises(ConfigError, match="Apolo Platform CLI was updated"):
            await client.config.check_server()


async def test_check_server_mismatch_auth(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient
) -> None:
    # the test returns the same as for valid answer but the cluster name is different

    admin_url = "https://admin-api.dev.apolo.us"
    registry_url = "https://registry2-api.dev.apolo.us"
    storage_url = "https://storage2-api.dev.apolo.us"
    users_url = "https://users2-api.dev.apolo.us"
    monitoring_url = "https://jobs2-api.dev.apolo.us"
    secrets_url = "https://secrets2-api.dev.apolo.us"
    disks_url = "https://disks2-api.dev.apolo.us"
    buckets_url = "https://buckets2-api.dev.apolo.us"
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    audience = "https://platform.api.dev.apolo.us"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "authorized": True,
        "admin_url": admin_url,
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": "other_client_id",
        "audience": audience,
        "headless_callback_url": headless_callback_url,
        "success_redirect_url": success_redirect_url,
        "clusters": [
            {
                "name": "default",
                "registry_url": registry_url,
                "storage_url": storage_url,
                "users_url": users_url,
                "monitoring_url": monitoring_url,
                "secrets_url": secrets_url,
                "disks_url": disks_url,
                "buckets_url": buckets_url,
                "resource_pool_types": [
                    {
                        "name": "cpu",
                        "min_size": 1,
                        "max_size": 2,
                        "cpu": 7,
                        "memory": 14 * 2**30,
                        "disk_size": 150 * 2**30,
                    }
                ],
                "resource_presets": [
                    {
                        "name": "cpu-small",
                        "credits_per_hour": "10",
                        "cpu": 2,
                        "memory": 2 * 2**30,
                    }
                ],
            }
        ],
    }

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(JSON)

    app = web.Application()
    app.add_routes([web.get("/config", handler)])
    srv = await aiohttp_server(app)

    async with make_client(srv.make_url("/")) as client:
        # Set expired version
        client.config._config_data.__dict__["version"] = "18.1.1"

        with pytest.raises(ConfigError, match="Apolo Platform CLI was updated"):
            await client.config.check_server()


async def test_refresh_token(
    aiohttp_server: _TestServerFactory, make_client: _MakeClient, token: str
) -> None:
    async def handler(request: web.Request) -> web.Response:
        req = dict(parse_qsl(await request.text()))
        assert req == {
            "client_id": "CLIENT-ID",
            "grant_type": "refresh_token",
            "refresh_token": "REFRESH_TOKEN",
        }
        return web.json_response(
            {
                "access_token": "ACCESS_TOKEN",
                "expires_in": 3600,
                "refresh_token": req["refresh_token"],
            }
        )

    app = web.Application()
    app.add_routes([web.post("/oauth/token", handler)])
    srv = await aiohttp_server(app)

    async with make_client(
        srv.make_url("/"), token_url=srv.make_url("/oauth/token")
    ) as client:
        token1 = await client.config.token()

        # Set expired version to far ago
        client.config._config_data.__dict__["auth_token"] = replace(
            _AuthToken.create(token, 3600, "REFRESH_TOKEN"), expiration_time=200
        )

        token2 = await client.config.token()

        assert token1 != token2
        assert token2 == "ACCESS_TOKEN"
