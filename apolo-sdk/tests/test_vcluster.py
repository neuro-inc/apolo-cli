from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml
from aiohttp import web

from apolo_sdk import (
    Client,
    KubeServiceAccount,
)
from apolo_sdk._vcluster import _merge_configs

from tests import _TestServerFactory


def test_merge_configs_add() -> None:
    kube_conf = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority": "/home/andrew/.minikube/ca.crt",
                    "server": "https://192.168.49.2:8443",
                },
                "name": "minikube",
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "minikube",
                    "namespace": "default",
                    "user": "minikube",
                },
                "name": "minikube",
            }
        ],
        "current-context": "minikube",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "minikube",
                "user": {
                    "client-certificate": "/home/andrew/.minikube/client.crt",
                    "client-key": "/home/andrew/.minikube/client.key",
                },
            }
        ],
    }
    sa_conf = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "kubernetes",
                    "user": "andrew-ac3",
                    "namespace": "default",
                },
                "name": "kubernetes-super-admin@kubernetes",
            }
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "users": [
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data>",
                },
            }
        ],
    }

    _merge_configs(kube_conf, sa_conf)

    assert {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority": "/home/andrew/.minikube/ca.crt",
                    "server": "https://192.168.49.2:8443",
                },
                "name": "minikube",
            },
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            },
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "minikube",
                    "namespace": "default",
                    "user": "minikube",
                },
                "name": "minikube",
            },
            {
                "context": {
                    "cluster": "kubernetes",
                    "namespace": "default",
                    "user": "andrew-ac3",
                },
                "name": "kubernetes-super-admin@kubernetes",
            },
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "minikube",
                "user": {
                    "client-certificate": "/home/andrew/.minikube/client.crt",
                    "client-key": "/home/andrew/.minikube/client.key",
                },
            },
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data>",
                },
            },
        ],
    } == kube_conf


def test_merge_configs_override() -> None:
    kube_conf = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority": "/home/andrew/.minikube/ca.crt",
                    "server": "https://192.168.49.2:8443",
                },
                "name": "minikube",
            },
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            },
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "minikube",
                    "namespace": "default",
                    "user": "minikube",
                },
                "name": "minikube",
            },
            {
                "context": {
                    "cluster": "kubernetes",
                    "namespace": "default",
                    "user": "andrew-ac3",
                },
                "name": "kubernetes-super-admin@kubernetes",
            },
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "minikube",
                "user": {
                    "client-certificate": "/home/andrew/.minikube/client.crt",
                    "client-key": "/home/andrew/.minikube/client.key",
                },
            },
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data>",
                },
            },
        ],
    }
    sa_conf = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data2>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "kubernetes",
                    "user": "andrew-ac3",
                    "namespace": "default",
                },
                "name": "kubernetes-super-admin@kubernetes",
            }
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "users": [
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data2>",
                },
            }
        ],
    }

    _merge_configs(kube_conf, sa_conf)

    assert {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority": "/home/andrew/.minikube/ca.crt",
                    "server": "https://192.168.49.2:8443",
                },
                "name": "minikube",
            },
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data2>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            },
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "minikube",
                    "namespace": "default",
                    "user": "minikube",
                },
                "name": "minikube",
            },
            {
                "context": {
                    "cluster": "kubernetes",
                    "namespace": "default",
                    "user": "andrew-ac3",
                },
                "name": "kubernetes-super-admin@kubernetes",
            },
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "minikube",
                "user": {
                    "client-certificate": "/home/andrew/.minikube/client.crt",
                    "client-key": "/home/andrew/.minikube/client.key",
                },
            },
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data2>",
                },
            },
        ],
    } == kube_conf


def test_merge_configs_empty() -> None:
    kube_conf: dict[str, Any] = {}
    sa_conf = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "kubernetes",
                    "user": "andrew-ac3",
                    "namespace": "default",
                },
                "name": "kubernetes-super-admin@kubernetes",
            }
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "users": [
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data>",
                },
            }
        ],
    }

    _merge_configs(kube_conf, sa_conf)

    assert {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "kubernetes",
                    "user": "andrew-ac3",
                    "namespace": "default",
                },
                "name": "kubernetes-super-admin@kubernetes",
            }
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "users": [
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data>",
                },
            }
        ],
    }


async def test_list_service_accounts(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert (
            request.path == "/apis/vcluster/v1/kube/cluster/default"
            "/org/superorg/project/test/config"
        )
        return web.json_response(
            [
                {
                    "user": "user",
                    "name": "name",
                    "created_at": "2025-05-07 11:00:00+00:00",
                    "expired_at": "2026-05-07 11:00:00+00:00",
                }
            ]
        )

    web_app = web.Application()
    web_app.router.add_get(
        "/apis/vcluster/v1/kube/cluster/{cluster}"
        "/org/{org}/project/{project}/config",
        handler,
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        sas = []
        async with client.vcluster.list_service_accounts(
            cluster_name="default", org_name="superorg", project_name="test"
        ) as it:
            async for sa in it:
                sas.append(sa)

        assert len(sas) == 1
        assert isinstance(sas[0], KubeServiceAccount)
        assert sas[0].user == "user"
        assert sas[0].name == "name"
        assert sas[0].created_at == datetime(2025, 5, 7, 11, 0, 0, tzinfo=timezone.utc)
        assert sas[0].expired_at == datetime(2026, 5, 7, 11, 0, 0, tzinfo=timezone.utc)


async def test_delete_service_accounts(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert (
            request.path == "/apis/vcluster/v1/kube/cluster/default/"
            "org/superorg/project/test/config/name"
        )
        return web.json_response(
            {
                "user": "user",
                "name": "name",
                "created_at": "2025-05-07 11:00:00+00:00",
                "expired_at": "2026-05-07 11:00:00+00:00",
            }
        )

    web_app = web.Application()
    web_app.router.add_delete(
        "/apis/vcluster/v1/kube/cluster/{cluster}/"
        "org/{org}/project/{project}/config/{name}",
        handler,
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        sa = await client.vcluster.delete_service_account(
            "name", cluster_name="default", org_name="superorg", project_name="test"
        )
        assert isinstance(sa, KubeServiceAccount)
        assert sa.user == "user"
        assert sa.name == "name"
        assert sa.created_at == datetime(2025, 5, 7, 11, 0, 0, tzinfo=timezone.utc)
        assert sa.expired_at == datetime(2026, 5, 7, 11, 0, 0, tzinfo=timezone.utc)


async def test_create_service_accounts(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert (
            request.path == "/apis/vcluster/v1/kube/cluster/default/"
            "org/superorg/project/test/config"
        )
        js = await request.json()
        assert js == {"name": "name", "ttl": 3600.0}
        return web.Response(
            text=yaml.safe_dump(
                {
                    "apiVersion": "v1",
                    "clusters": [
                        {
                            "cluster": {
                                "certificate-authority-data": "<cert-data>",
                                "server": "https://example.dev.apolo.us:443",
                            },
                            "name": "kubernetes",
                        }
                    ],
                    "contexts": [
                        {
                            "context": {
                                "cluster": "kubernetes",
                                "user": "andrew-ac3",
                                "namespace": "default",
                            },
                            "name": "kubernetes-super-admin@kubernetes",
                        }
                    ],
                    "current-context": "kubernetes-super-admin@kubernetes",
                    "kind": "Config",
                    "users": [
                        {
                            "name": "andrew-ac3",
                            "user": {
                                "token": "<token-data>",
                            },
                        }
                    ],
                }
            ),
            content_type="application/x-yaml",
        )

    web_app = web.Application()
    web_app.router.add_post(
        "/apis/vcluster/v1/kube/cluster/{cluster}/"
        "org/{org}/project/{project}/config",
        handler,
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        yml = await client.vcluster.create_service_account(
            "name",
            cluster_name="default",
            org_name="superorg",
            project_name="test",
            ttl=timedelta(hours=1),
        )
        js = yaml.safe_load(yml)
        assert js == {
            "apiVersion": "v1",
            "clusters": [
                {
                    "cluster": {
                        "certificate-authority-data": "<cert-data>",
                        "server": "https://example.dev.apolo.us:443",
                    },
                    "name": "kubernetes",
                },
            ],
            "contexts": [
                {
                    "context": {
                        "cluster": "kubernetes",
                        "namespace": "default",
                        "user": "andrew-ac3",
                    },
                    "name": "kubernetes-super-admin@kubernetes",
                },
            ],
            "current-context": "kubernetes-super-admin@kubernetes",
            "kind": "Config",
            "users": [
                {
                    "name": "andrew-ac3",
                    "user": {
                        "token": "<token-data>",
                    },
                },
            ],
        }


async def test_regenerate_service_account(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert (
            request.path == "/apis/vcluster/v1/kube/cluster/default/"
            "org/superorg/project/test/config/name"
        )
        js = await request.json()
        assert js == {"ttl": 3600.0}
        return web.Response(
            text=yaml.safe_dump(
                {
                    "apiVersion": "v1",
                    "clusters": [
                        {
                            "cluster": {
                                "certificate-authority-data": "<cert-data>",
                                "server": "https://example.dev.apolo.us:443",
                            },
                            "name": "kubernetes",
                        }
                    ],
                    "contexts": [
                        {
                            "context": {
                                "cluster": "kubernetes",
                                "user": "andrew-ac3",
                                "namespace": "default",
                            },
                            "name": "kubernetes-super-admin@kubernetes",
                        }
                    ],
                    "current-context": "kubernetes-super-admin@kubernetes",
                    "kind": "Config",
                    "users": [
                        {
                            "name": "andrew-ac3",
                            "user": {
                                "token": "<token-data>",
                            },
                        }
                    ],
                }
            ),
            content_type="application/x-yaml",
        )

    web_app = web.Application()
    web_app.router.add_put(
        "/apis/vcluster/v1/kube/cluster/{cluster}/"
        "org/{org}/project/{project}/config/name",
        handler,
    )
    srv = await aiohttp_server(web_app)

    async with make_client(srv.make_url("/")) as client:
        yml = await client.vcluster.regenerate_service_account(
            "name",
            cluster_name="default",
            org_name="superorg",
            project_name="test",
            ttl=timedelta(hours=1),
        )
        js = yaml.safe_load(yml)
        assert js == {
            "apiVersion": "v1",
            "clusters": [
                {
                    "cluster": {
                        "certificate-authority-data": "<cert-data>",
                        "server": "https://example.dev.apolo.us:443",
                    },
                    "name": "kubernetes",
                },
            ],
            "contexts": [
                {
                    "context": {
                        "cluster": "kubernetes",
                        "namespace": "default",
                        "user": "andrew-ac3",
                    },
                    "name": "kubernetes-super-admin@kubernetes",
                },
            ],
            "current-context": "kubernetes-super-admin@kubernetes",
            "kind": "Config",
            "users": [
                {
                    "name": "andrew-ac3",
                    "user": {
                        "token": "<token-data>",
                    },
                },
            ],
        }


async def test_activate_service_account(
    aiohttp_server: _TestServerFactory,
    make_client: Callable[..., Client],
    monkeypatch: Any,
) -> None:
    cfg = {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": "<cert-data>",
                    "server": "https://example.dev.apolo.us:443",
                },
                "name": "kubernetes",
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": "kubernetes",
                    "user": "andrew-ac3",
                    "namespace": "default",
                },
                "name": "kubernetes-super-admin@kubernetes",
            }
        ],
        "current-context": "kubernetes-super-admin@kubernetes",
        "kind": "Config",
        "users": [
            {
                "name": "andrew-ac3",
                "user": {
                    "token": "<token-data>",
                },
            }
        ],
    }

    web_app = web.Application()
    srv = await aiohttp_server(web_app)
    async with make_client(srv.make_url("/")) as client:
        folder = client.config.path / "default" / "superorg" / "test"
        folder.mkdir(parents=True)
        with (folder / f"{client.config.username}-name.yaml").open("w") as f:
            yaml.safe_dump(cfg, f)
        monkeypatch.setenv("HOME", str(client.config.path.parent))
        config_file = client.config.path.parent / ".kube" / "config"
        assert not config_file.exists()
        await client.vcluster.activate_service_account(
            "name",
            cluster_name="default",
            org_name="superorg",
            project_name="test",
        )
        txt = config_file.read_text()
        assert yaml.safe_load(txt) == cfg
