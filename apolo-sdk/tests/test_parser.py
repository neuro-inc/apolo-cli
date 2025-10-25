from typing import Callable

import pytest
from yarl import URL

from apolo_sdk import Client, DiskVolume, LocalImage, RemoteImage, SecretFile, Volume
from apolo_sdk._parsing_utils import _get_url_authority

_MakeClient = Callable[..., Client]


@pytest.mark.parametrize(
    "volume",
    [
        "storage:///",
        ":",
        "::::",
        "",
        "storage:///data/:/data/rest:wrong",
        "storage://cluster/project/path:to:/storage/location",
        "storage://cluster/project/path/to:/storage/loca:tion",
        "storage://cluster/project/path/to#fragment:/storage/location",
        "storage://cluster/project/path/to#:/storage/location",
        "storage://cluster/project/path/to?key=value:/storage/location",
        "storage://cluster/project/path/to?:/storage/location",
        "storage://user@cluster/project/path/to:/storage/location",
        "storage://:password@cluster/project/path/to:/storage/location",
        "storage://:@cluster/project/path/to:/storage/location",
        "storage://cluster:1234/project/path/to:/storage/location",
    ],
)
async def test_volume_from_str_fail(volume: str, make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(ValueError):
            client.parse.volume(volume)


@pytest.mark.parametrize(
    "volume",
    [
        "disk://",
        "disk://cluster/project/name:/disk/location:rw:more",
        "disk://cluster/project/name:/disk/location:rwo",
        "disk://cluster/project/na:me:/disk/location",
        "disk://cluster/project/name:/disk/loca:tion",
        "disk://cluster/project/name#fragment:/disk/location",
        "disk://cluster/project/name#:/disk/location",
        "disk://cluster/project/name?key=value:/disk/location",
        "disk://cluster/project/name?:/disk/location",
        "disk://user@cluster/project/name:/disk/location",
        "disk://:password@cluster/project/name:/disk/location",
        "disk://:@cluster/project/name:/disk/location",
        "disk://cluster:1234/project/name:/disk/location",
        "secret://cluster/project/secret:/var/secret:ro",
        "secret://cluster/project/sec:ret:/secret/location",
        "secret://cluster/project/secret:/secret/loca:tion",
        "secret://cluster/project/secret#fragment:/secret/location",
        "secret://cluster/project/secret#:/secret/location",
        "secret://cluster/project/secret?key=value:/secret/location",
        "secret://cluster/project/secret?:/secret/location",
        "secret://user@cluster/project/secret:/secret/location",
        "secret://:password@cluster/project/secret:/secret/location",
        "secret://:@cluster/project/secret:/secret/location",
        "secret://cluster:1234/project/secret:/secret/location",
        "dissk://f1/f2/f3:/f1:rw",
    ],
)
async def test_parse_volumes_fail(volume: str, make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        with pytest.raises(ValueError):
            client.parse.volumes([volume])


async def test_parse_volumes(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        volumes_str = [
            "storage://cluster/user/path/to1:/storage/location1:rw",
            "storage://cluster/user/path/to2:/storage/location2:ro",
            "secret://cluster/user/secret1:/secret/location3",
            "disk://cluster/user/disk1:/disk/location4:rw",
            "disk://cluster/user/disk2:/disk/location5:ro",
        ]
        result = client.parse.volumes(volumes_str)
        assert set(result.volumes) == {
            Volume(URL("storage://cluster/user/path/to1"), "/storage/location1", False),
            Volume(URL("storage://cluster/user/path/to2"), "/storage/location2", True),
        }
        assert set(result.secret_files) == {
            SecretFile(URL("secret://cluster/user/secret1"), "/secret/location3")
        }
        assert set(result.disk_volumes) == {
            DiskVolume(URL("disk://cluster/user/disk1"), "/disk/location4", False),
            DiskVolume(URL("disk://cluster/user/disk2"), "/disk/location5", True),
        }


async def test_parse_volumes_special_chars(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        volumes_str = [
            "storage://cluster/user/path/to%23%252d%3a%3f%40%C3%9F:/storage:rw",
            "secret://cluster/user/secret%23%252d%3a%3f%40%C3%9F:/secret",
            "disk://cluster/user/disk%23%252d%3a%3f%40%C3%9F:/disk:rw",
        ]
        result = client.parse.volumes(volumes_str)
        assert result.volumes == [
            Volume(
                URL("storage://cluster/user/path/to%23%252d%3a%3f%40%C3%9F"),
                "/storage",
                False,
            ),
        ]
        assert result.volumes[0].storage_uri.path == "/user/path/to#%2d:?@ß"
        assert result.secret_files == [
            SecretFile(
                URL("secret://cluster/user/secret%23%252d%3a%3f%40%C3%9F"),
                "/secret",
            )
        ]
        assert result.secret_files[0].secret_uri.path == "/user/secret#%2d:?@ß"
        assert result.disk_volumes == [
            DiskVolume(
                URL("disk://cluster/user/disk%23%252d%3a%3f%40%C3%9F"),
                "/disk",
                False,
            ),
        ]
        assert result.disk_volumes[0].disk_uri.path == "/user/disk#%2d:?@ß"


async def test_parse_local(make_client: _MakeClient) -> None:
    async with make_client("https://api.localhost.localdomain") as client:
        result = client.parse.local_image("bananas:latest")
    assert result == LocalImage("bananas", "latest")


async def test_parse_remote(make_client: _MakeClient) -> None:
    async with make_client("https://api.localhost.localdomain") as client:
        result = client.parse.remote_image("image://default/project/bananas:latest")
    assert result == RemoteImage.new_platform_image(
        name="bananas",
        tag="latest",
        registry="registry-api.dev.apolo.us",
        cluster_name="default",
        org_name="test-org",
        project_name="project",
    )


async def test_parse_remote_registry_image(make_client: _MakeClient) -> None:
    async with make_client(
        "https://api.localhost.localdomain", registry_url="http://localhost:5000"
    ) as client:
        result = client.parse.remote_image(
            "localhost:5000/project/library/bananas:latest"
        )
    assert result == RemoteImage.new_platform_image(
        name="library/bananas",
        tag="latest",
        registry="localhost:5000",
        cluster_name="default",
        org_name="test-org",
        project_name="project",
    )


async def test_parse_remote_public(make_client: _MakeClient) -> None:
    async with make_client(
        "https://api.localhost.localdomain", registry_url="http://localhost:5000"
    ) as client:
        result = client.parse.remote_image("ubuntu:latest")
    assert result == RemoteImage.new_external_image(name="ubuntu", tag="latest")


def test_get_url_authority_with_explicit_port() -> None:
    url = URL("http://example.com:8080/")
    assert _get_url_authority(url) == "example.com:8080"


def test_get_url_authority_with_implicit_port() -> None:
    url = URL("http://example.com/")  # here `url.port == 80`
    assert _get_url_authority(url) == "example.com"


def test_get_url_authority_without_port() -> None:
    url = URL("scheme://example.com/")  # here `url.port is None`
    assert _get_url_authority(url) == "example.com"


def test_get_url_authority_without_host() -> None:
    url = URL("scheme://")
    with pytest.raises(AssertionError):
        _get_url_authority(url)


async def test_parse_secret_files_keeps_order(make_client: _MakeClient) -> None:
    # Check for regression
    volumes = [
        "secret:first:/var/secrets/first",
        "secret:second:/var/secrets/second",
        "secret:third:/var/secrets/third",
    ]
    async with make_client("https://example.com") as client:
        volumes_parsed = client.parse.volumes(volumes)

    assert volumes_parsed.secret_files == [
        SecretFile(
            URL(f"secret://default/test-org/{client.config.project_name}/first"),
            "/var/secrets/first",
        ),
        SecretFile(
            URL(f"secret://default/test-org/{client.config.project_name}/second"),
            "/var/secrets/second",
        ),
        SecretFile(
            URL(f"secret://default/test-org/{client.config.project_name}/third"),
            "/var/secrets/third",
        ),
    ]


async def test_normalize_uri_short_from_short(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        ret = client.parse.normalize_uri(URL("storage:dir"), short=True)
        assert ret == URL("storage:dir")


async def test_normalize_uri_short_from_long(make_client: _MakeClient) -> None:
    async with make_client("https://example.com") as client:
        ret = client.parse.normalize_uri(URL("storage:dir/"), short=True)
        assert ret == URL("storage:dir")
