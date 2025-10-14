from decimal import Decimal

import aiohttp
import pytest
from aiohttp import web
from yarl import URL

from apolo_sdk import AppsConfig, AuthError, Cluster, Preset, Project, ResourcePool
from apolo_sdk._login import _AuthConfig
from apolo_sdk._server_cfg import (
    AMDGPU,
    AMDGPUPreset,
    IntelGPU,
    IntelGPUPreset,
    NvidiaGPU,
    NvidiaGPUPreset,
    _ServerConfig,
    get_server_config,
)

from tests import _TestClientFactory


async def test_get_server_config_no_clusters(
    aiohttp_client: _TestClientFactory,
) -> None:
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    callback_urls = [
        "http://127.0.0.1:54540",
        "http://127.0.0.1:54541",
        "http://127.0.0.1:54542",
    ]
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "callback_urls": callback_urls,
        "success_redirect_url": success_redirect_url,
        "headless_callback_url": headless_callback_url,
    }

    async def handler(request: web.Request) -> web.Response:
        assert "Authorization" not in request.headers
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/config", handler)
    client = await aiohttp_client(app)

    config = await get_server_config(client.session, client.make_url("/"))
    assert config == _ServerConfig(
        auth_config=_AuthConfig(
            auth_url=URL(auth_url),
            token_url=URL(token_url),
            logout_url=URL(logout_url),
            client_id=client_id,
            audience=audience,
            headless_callback_url=URL(headless_callback_url),
            callback_urls=tuple(URL(u) for u in callback_urls),
            success_redirect_url=URL(success_redirect_url),
        ),
        clusters={},
        projects={},
        admin_url=None,
    )


async def test_get_server_config_no_callback_urls(
    aiohttp_client: _TestClientFactory,
) -> None:
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "headless_callback_url": headless_callback_url,
        "success_redirect_url": success_redirect_url,
    }

    async def handler(request: web.Request) -> web.Response:
        assert "Authorization" not in request.headers
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/config", handler)
    client = await aiohttp_client(app)

    config = await get_server_config(client.session, client.make_url("/"))
    assert config == _ServerConfig(
        auth_config=_AuthConfig(
            auth_url=URL(auth_url),
            token_url=URL(token_url),
            logout_url=URL(logout_url),
            client_id=client_id,
            audience=audience,
            headless_callback_url=URL(headless_callback_url),
            success_redirect_url=URL(success_redirect_url),
        ),
        clusters={},
        projects={},
        admin_url=None,
    )


async def test_get_server_config_with_token(
    aiohttp_client: _TestClientFactory,
) -> None:
    admin_url = "https://admin-api.dev.apolo.us"
    registry_url = "https://registry.api.dev.apolo.us"
    storage_url = "https://storage.api.dev.apolo.us"
    users_url = "https://api.dev.apolo.us/users"
    monitoring_url = "https://api.dev.apolo.us/monitoring"
    secrets_url = "https://api.dev.apolo.us/secrets"
    disks_url = "https://api.dev.apolo.us/disks"
    buckets_url = "https://api.dev.apolo.us/buckets"
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
                "name": "default",
                "monitoring_url": monitoring_url,
                "storage_url": storage_url,
                "registry_url": registry_url,
                "users_url": users_url,
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
                        "nvidia_gpu": {
                            "count": 1,
                            "model": "nvidia-gpu",
                            "memory": 10**10,
                        },
                        "resource_pool_names": ["nvidia-gpu"],
                        "available_resource_pool_names": [],
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
                        "available_resource_pool_names": [],
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
                    {
                        "name": "cpu-large-p",
                        "credits_per_hour": "10",
                        "cpu": 3,
                        "memory": 14 * 2**30,
                        "scheduler_enabled": True,
                        "preemptible_node": True,
                    },
                ],
                "apps": {
                    "apps_hostname_templates": "customtemplate",
                },
            }
        ],
        "projects": [
            {
                "cluster_name": "default",
                "org_name": None,
                "name": "test-project",
                "role": "owner",
            }
        ],
    }

    async def handler(request: web.Request) -> web.Response:
        assert request.headers["Authorization"] == "Bearer bananatoken"
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/config", handler)
    client = await aiohttp_client(app)

    config = await get_server_config(
        client.session, client.make_url("/"), token="bananatoken"
    )
    project = Project(
        cluster_name="default", org_name="NO_ORG", name="test-project", role="owner"
    )
    assert config == _ServerConfig(
        auth_config=_AuthConfig(
            auth_url=URL(auth_url),
            token_url=URL(token_url),
            logout_url=URL(logout_url),
            client_id=client_id,
            audience=audience,
            headless_callback_url=URL(headless_callback_url),
            success_redirect_url=URL(success_redirect_url),
        ),
        admin_url=URL(admin_url),
        clusters={
            "default": Cluster(
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
                    ),
                    "nvidia-gpu": ResourcePool(
                        min_size=0,
                        max_size=1,
                        cpu=7,
                        memory=60 * 2**30,
                        disk_size=150 * 2**30,
                        nvidia_gpu=NvidiaGPU(
                            count=1, model="nvidia-gpu", memory=10**10
                        ),
                        nvidia_migs={
                            "1g.5gb": NvidiaGPU(
                                count=1, model="nvidia-gpu-1g.5gb", memory=5 * 10**9
                            )
                        },
                    ),
                    "amd-gpu": ResourcePool(
                        min_size=0,
                        max_size=1,
                        cpu=7,
                        memory=60 * 2**30,
                        disk_size=150 * 2**30,
                        amd_gpu=AMDGPU(count=1, model="amd-gpu"),
                    ),
                    "intel-gpu": ResourcePool(
                        min_size=0,
                        max_size=1,
                        cpu=7,
                        memory=60 * 2**30,
                        disk_size=150 * 2**30,
                        intel_gpu=IntelGPU(count=1, model="intel-gpu"),
                    ),
                },
                presets={
                    "nvidia-gpu-small": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=30 * 2**30,
                        nvidia_gpu=NvidiaGPUPreset(
                            count=1, model="nvidia-gpu", memory=10**10
                        ),
                        resource_pool_names=("nvidia-gpu",),
                        available_resource_pool_names=(),
                    ),
                    "nvidia-gpu-large": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=60 * 2**30,
                        nvidia_gpu=NvidiaGPUPreset(count=1),
                        resource_pool_names=("nvidia-gpu",),
                        available_resource_pool_names=("nvidia-gpu",),
                    ),
                    "nvidia-mig": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=30 * 2**30,
                        nvidia_migs={
                            "1g.5gb": NvidiaGPUPreset(
                                count=1, model="nvidia-gpu-1g.5gb", memory=5 * 10**9
                            )
                        },
                        resource_pool_names=("nvidia-gpu",),
                    ),
                    "amd-gpu-small": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=30 * 2**30,
                        amd_gpu=AMDGPUPreset(count=1),
                        resource_pool_names=("amd-gpu",),
                        available_resource_pool_names=("amd-gpu",),
                    ),
                    "amd-gpu-large": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=60 * 2**30,
                        amd_gpu=AMDGPUPreset(count=1),
                        resource_pool_names=("amd-gpu",),
                        available_resource_pool_names=("amd-gpu",),
                    ),
                    "intel-gpu-small": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=30 * 2**30,
                        intel_gpu=IntelGPUPreset(count=1),
                        resource_pool_names=("intel-gpu",),
                        available_resource_pool_names=("intel-gpu",),
                    ),
                    "intel-gpu-large": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=7,
                        memory=60 * 2**30,
                        intel_gpu=IntelGPUPreset(count=1),
                        resource_pool_names=("intel-gpu",),
                        available_resource_pool_names=("intel-gpu",),
                    ),
                    "cpu-small": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=2,
                        memory=2 * 2**30,
                        available_resource_pool_names=("cpu",),
                    ),
                    "cpu-large": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=3,
                        memory=14 * 2**30,
                        available_resource_pool_names=("cpu",),
                    ),
                    "cpu-large-p": Preset(
                        credits_per_hour=Decimal("10"),
                        cpu=3,
                        memory=14 * 2**30,
                        scheduler_enabled=True,
                        preemptible_node=True,
                        available_resource_pool_names=(),
                    ),
                },
                name="default",
                orgs=["NO_ORG"],
                apps=AppsConfig(hostname_templates="customtemplate"),
            )
        },
        projects={project.key: project},
    )


async def test_get_server_config_with_token_no_clusters(
    aiohttp_client: _TestClientFactory,
) -> None:
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    callback_urls = [
        "http://127.0.0.1:54540",
        "http://127.0.0.1:54541",
        "http://127.0.0.1:54542",
    ]
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "authorized": True,
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "callback_urls": callback_urls,
        "success_redirect_url": success_redirect_url,
        "headless_callback_url": headless_callback_url,
    }

    async def handler(request: web.Request) -> web.Response:
        assert request.headers["Authorization"] == "Bearer bananatoken"
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/config", handler)
    client = await aiohttp_client(app)

    config = await get_server_config(
        client.session, client.make_url("/"), token="bananatoken"
    )
    assert config == _ServerConfig(
        auth_config=_AuthConfig(
            auth_url=URL(auth_url),
            token_url=URL(token_url),
            logout_url=URL(logout_url),
            client_id=client_id,
            audience=audience,
            headless_callback_url=URL(headless_callback_url),
            callback_urls=tuple(URL(u) for u in callback_urls),
            success_redirect_url=URL(success_redirect_url),
        ),
        clusters={},
        projects={},
        admin_url=None,
    )


async def test_get_server_config_unauthorized(
    aiohttp_client: _TestClientFactory,
) -> None:
    auth_url = "https://dev-neuro.auth0.com/authorize"
    token_url = "https://dev-neuro.auth0.com/oauth/token"
    logout_url = "https://dev-neuro.auth0.com/v2/logout"
    client_id = "this_is_client_id"
    audience = "https://platform.api.dev.apolo.us"
    headless_callback_url = "https://api.dev.apolo.us/oauth/show-code"
    callback_urls = [
        "http://127.0.0.1:54540",
        "http://127.0.0.1:54541",
        "http://127.0.0.1:54542",
    ]
    success_redirect_url = "https://platform.neu.ro"
    JSON = {
        "auth_url": auth_url,
        "token_url": token_url,
        "logout_url": logout_url,
        "client_id": client_id,
        "audience": audience,
        "callback_urls": callback_urls,
        "success_redirect_url": success_redirect_url,
        "headless_callback_url": headless_callback_url,
    }

    async def handler(request: web.Request) -> web.Response:
        assert request.headers["Authorization"] == "Bearer bananatoken"
        return web.json_response(JSON)

    app = web.Application()
    app.router.add_get("/config", handler)
    client = await aiohttp_client(app)

    with pytest.raises(AuthError, match="Cannot authorize user"):
        await get_server_config(
            client.session, client.make_url("/"), token="bananatoken"
        )


async def test_get_server_config__fail(aiohttp_client: _TestClientFactory) -> None:
    async def handler(request: web.Request) -> web.Response:
        raise aiohttp.web.HTTPInternalServerError(reason="unexpected server error")

    app = web.Application()
    app.router.add_get("/config", handler)
    client = await aiohttp_client(app)

    with pytest.raises(RuntimeError, match="Unable to get server configuration: 500"):
        await get_server_config(client.session, client.make_url("/"))
