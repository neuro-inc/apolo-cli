from typing import Any

from apolo_sdk._vcluster import _merge_configs


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
