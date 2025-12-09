import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
from yarl import URL

from apolo_sdk import Client
from apolo_sdk._url_utils import (
    _extract_path,
    normalize_local_path_uri,
    normalize_storage_path_uri,
    uri_from_cli,
)


@pytest.fixture
async def client(make_client: Callable[..., Client]) -> AsyncIterator[Client]:
    async with make_client("https://example.com") as client:
        yield client


# asvetlov: I don't like autouse but it is the fastest fix
@pytest.fixture(autouse=True)
def fake_homedir(monkeypatch: Any, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return Path.home()


@pytest.fixture
def pwd() -> Path:
    return Path.cwd()


async def test_config_username(token: str, client: Client) -> None:
    assert client.username == "user"


def test_uri_from_cli_relative_path() -> None:
    uri = uri_from_cli("path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == Path("path/to/file.txt").absolute().as_uri()


def test_uri_from_cli_absolute_path() -> None:
    uri = uri_from_cli("/path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == Path("/path/to/file.txt").absolute().as_uri()


def test_uri_from_cli_relative_path_special_chars() -> None:
    uri = uri_from_cli("path/to/file#%23:?@~", "testuser", "test-cluster", None)
    assert uri.path.endswith("/path/to/file#%23:?@~")


def test_uri_from_cli_absolute_path_special_chars() -> None:
    uri = uri_from_cli("/path/to/file#%23:?@~", "testuser", "test-cluster", None)
    assert _extract_path(uri) == Path("/path/to/file#%23:?@~").absolute()


def test_uri_from_cli_path_with_tilde(fake_homedir: Path) -> None:
    uri = uri_from_cli("~/path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == (fake_homedir / "path/to/file.txt").as_uri()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="expanduser() does not fail for unknown user on Windows",
)
def test_uri_from_cli_path_with_tilde_unknown_user() -> None:
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        uri_from_cli("~unknownuser/path/to/file.txt", "testuser", "test-cluster", None)


def test_uri_from_cli_tilde_only(fake_homedir: Path) -> None:
    uri = uri_from_cli("~", "testuser", "test-cluster", None)
    assert str(uri) == fake_homedir.as_uri()


def test_uri_from_cli_relative_file_uri() -> None:
    uri = uri_from_cli("file:path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == Path("path/to/file.txt").absolute().as_uri()


def test_uri_from_cli_absolute_file_uri() -> None:
    uri = uri_from_cli("file:/path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == Path("/path/to/file.txt").absolute().as_uri()
    uri = uri_from_cli("file:///path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == Path("/path/to/file.txt").absolute().as_uri()


def test_uri_from_cli_relative_file_uri_special_chars() -> None:
    uri = uri_from_cli(
        "file:path/to/file%23%252d%3f:@~%C3%9F", "testuser", "test-cluster", None
    )
    assert uri.path.endswith("/path/to/file#%2d?:@~ß")


def test_uri_from_cli_absolute_file_uri_special_chars() -> None:
    uri = uri_from_cli(
        "file:/path/to/file%23%252d%3f:@~%C3%9F", "testuser", "test-cluster", None
    )
    assert uri.path.endswith("/path/to/file#%2d?:@~ß")


def test_uri_from_cli_relative_storage_uri() -> None:
    uri = uri_from_cli("storage:path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == "storage://test-cluster/testuser/path/to/file.txt"
    uri = uri_from_cli("storage:/path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == "storage://test-cluster/path/to/file.txt"


def test_uri_from_cli_absolute_storage_uri() -> None:
    uri = uri_from_cli(
        "storage://otheruser/path/to/file.txt", "testuser", "test-cluster", None
    )
    assert str(uri) == "storage://otheruser/path/to/file.txt"
    uri = uri_from_cli("storage:///path/to/file.txt", "testuser", "test-cluster", None)
    assert str(uri) == "storage://test-cluster/path/to/file.txt"


def test_uri_from_cli_absolute_storage_uri_special_chars() -> None:
    uri = uri_from_cli(
        "storage://cluster/user/path/to/file%23%252d%3f:@~%C3%9F",
        "testuser",
        "test-cluster",
        None,
    )
    assert uri.path == "/user/path/to/file#%2d?:@~ß"


def test_uri_from_cli_numberic_path() -> None:
    uri = uri_from_cli("256", "testuser", "test-cluster", None)
    assert str(uri) == Path("256").absolute().as_uri()
    uri = uri_from_cli("123456", "testuser", "test-cluster", None)
    assert str(uri) == Path("123456").absolute().as_uri()
    uri = uri_from_cli("file:256", "testuser", "test-cluster", None)
    assert str(uri) == Path("256").absolute().as_uri()
    uri = uri_from_cli("file:123456", "testuser", "test-cluster", None)
    assert str(uri) == Path("123456").absolute().as_uri()
    uri = uri_from_cli("storage:256", "testuser", "test-cluster", None)
    assert str(uri) == "storage://test-cluster/testuser/256"
    uri = uri_from_cli("storage:123456", "testuser", "test-cluster", None)
    assert str(uri) == "storage://test-cluster/testuser/123456"


@pytest.mark.parametrize(
    "path_or_uri",
    [
        "https://cluster/user/path/to",
        "file://cluster/user/path/to",
        "file:/path/to#fragment",
        "file:/path/to#",
        "file:/path/to?key=value",
        "file:/path/to?",
    ],
)
async def test_uri_from_cli__file__fail(path_or_uri: str) -> None:
    with pytest.raises(ValueError):
        uri_from_cli(path_or_uri, "u", "c", None, allowed_schemes=("file",))


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "https://cluster/user/path/to",
        "storage://cluster/user/path/to#fragment",
        "storage://cluster/user/path/to#",
        "storage://cluster/user/path/to?key=value",
        "storage://cluster/user/path/to?",
        "storage://user@cluster/user/path/to",
        "storage://:password@cluster/user/path/to",
        "storage://:@cluster/user/path/to",
        "storage://cluster:1234/user/path/to",
    ],
)
async def test_uri_from_cli__storage__fail(uri: str) -> None:
    with pytest.raises(ValueError):
        uri_from_cli(uri, "u", "c", None, allowed_schemes=("storage",))


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "https://cluster/user/image",
        "image://cluster/user/image#fragment",
        "image://cluster/user/image#",
        "image://cluster/user/image?key=value",
        "image://cluster/user/image?",
        "image://user@cluster/user/image",
        "image://:password@cluster/user/image",
        "image://:@cluster/user/image",
        "image://cluster:1234/user/image",
    ],
)
async def test_uri_from_cli__image__fail(uri: str) -> None:
    with pytest.raises(ValueError):
        uri_from_cli(uri, "u", "c", None, allowed_schemes=("image",))


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "https://cluster/bucket/object",
        "blob://cluster/bucket/object#fragment",
        "blob://cluster/bucket/object#",
        "blob://cluster/bucket/object?key=value",
        "blob://cluster/bucket/object?",
        "blob://user@cluster/bucket/object",
        "blob://:password@cluster/bucket/object",
        "blob://:@cluster/bucket/object",
        "blob://cluster:1234/bucket/object",
    ],
)
async def test_uri_from_cli__blob__fail(uri: str) -> None:
    with pytest.raises(ValueError):
        uri_from_cli(uri, "u", "c", None, allowed_schemes=("blob",))


async def test_normalize_storage_path_uri_no_path(client: Client) -> None:
    url = URL("storage:")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/user"
    assert str(url) == "storage://test-cluster/user"


async def test_normalize_local_path_uri_no_path(pwd: Path) -> None:
    url = URL("file:")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd


async def test_normalize_storage_path_uri_no_slashes(client: Client) -> None:
    url = URL("storage:file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/user/file.txt"
    assert str(url) == "storage://test-cluster/user/file.txt"


async def test_normalize_storage_path_uri_no_slashes_with_org(client: Client) -> None:
    url = URL("storage:file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", "test-org")
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/test-org/user/file.txt"
    assert str(url) == "storage://test-cluster/test-org/user/file.txt"


async def test_normalize_local_path_uri_no_slashes(pwd: Path) -> None:
    url = URL("file:file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "file.txt"


async def test_normalize_storage_path_uri__0_slashes_relative(client: Client) -> None:
    url = URL("storage:path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/user/path/to/file.txt"
    assert str(url) == "storage://test-cluster/user/path/to/file.txt"


async def test_normalize_storage_path_uri__0_slashes_relative_with_org(
    client: Client,
) -> None:
    url = URL("storage:path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", "test-org")
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/test-org/user/path/to/file.txt"
    assert str(url) == "storage://test-cluster/test-org/user/path/to/file.txt"


async def test_normalize_local_path_uri__0_slashes_relative(pwd: Path) -> None:
    url = URL("file:path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "path/to/file.txt"


async def test_normalize_storage_path_uri__1_slash_absolute(client: Client) -> None:
    url = URL("storage:/path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/path/to/file.txt"
    assert str(url) == "storage://test-cluster/path/to/file.txt"


async def test_normalize_storage_path_uri__1_slash_absolute_with_org(
    client: Client,
) -> None:
    url = URL("storage:/path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", "test-org")
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/test-org/path/to/file.txt"
    assert str(url) == "storage://test-cluster/test-org/path/to/file.txt"


async def test_normalize_local_path_uri__1_slash_absolute(pwd: Path) -> None:
    url = URL("file:/path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == Path(pwd.drive + "/path/to/file.txt")


async def test_normalize_storage_path_uri__2_slashes(client: Client) -> None:
    url = URL("storage://path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "path"
    assert url.path == "/to/file.txt"
    assert str(url) == "storage://path/to/file.txt"


async def test_normalize_local_path_uri__2_slashes(pwd: Path) -> None:
    url = URL("file://path/to/file.txt")
    with pytest.raises(
        ValueError, match="Host part is not allowed in file URI, found 'path'"
    ):
        url = normalize_local_path_uri(url)


async def test_normalize_storage_path_uri__3_slashes_relative(client: Client) -> None:
    url = URL("storage:///path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/path/to/file.txt"
    assert str(url) == "storage://test-cluster/path/to/file.txt"


async def test_normalize_local_path_uri__3_slashes_relative(pwd: Path) -> None:
    url = URL("file:///path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == Path(pwd.drive + "/path/to/file.txt")


async def test_normalize_storage_path_uri__4_slashes_relative(client: Client) -> None:
    url = URL("storage:////path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/path/to/file.txt"
    assert str(url) == "storage://test-cluster/path/to/file.txt"


@pytest.mark.skipif(sys.platform == "win32", reason="Doesn't work on Windows")
async def test_normalize_local_path_uri__4_slashes_relative() -> None:
    url = URL("file:////path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert url.path == "/path/to/file.txt"
    assert str(url) == f"file:///path/to/file.txt"


@pytest.mark.parametrize(
    "uri_str",
    [
        "",
        "https://cluster/user/path/to",
        "storage://cluster/user/path/to#fragment",
        "storage://cluster/user/path/to?key=value",
        "storage://user@cluster/user/path/to",
        "storage://:password@cluster/user/path/to",
        "storage://:@cluster/user/path/to",
        "storage://cluster:1234/user/path/to",
    ],
)
async def test_normalize_storage_path_uri__fail(uri_str: str) -> None:
    uri = URL(uri_str)
    with pytest.raises(ValueError):
        normalize_storage_path_uri(uri, "test-user", "test-cluster", None)


async def test_normalize_storage_path_uri__tilde_in_relative_path(
    client: Client,
) -> None:
    url = URL("storage:~/path/to/file.txt")
    with pytest.raises(ValueError, match=".*Cannot expand user.*"):
        normalize_storage_path_uri(url, client.username, "test-cluster", None)


async def test_normalize_local_path_uri__tilde_in_relative_path(
    fake_homedir: Path,
) -> None:
    url = URL("file:~/path/to/file.txt")
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        normalize_local_path_uri(url)


async def test_normalize_storage_path_uri__tilde_in_relative_path_2(
    client: Client,
) -> None:
    url = URL("storage:./~/path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/user/~/path/to/file.txt"
    assert str(url) == "storage://test-cluster/user/~/path/to/file.txt"


async def test_normalize_local_path_uri__tilde_in_relative_path_2(
    pwd: Path,
) -> None:
    url = URL("file:./~/path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "~/path/to/file.txt"
    assert str(url) == (pwd / "~/path/to/file.txt").as_uri().replace("%7E", "~")


async def test_normalize_storage_path_uri__tilde_in_relative_path_3(
    client: Client,
) -> None:
    url = URL("storage:path/to~file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/user/path/to~file.txt"
    assert str(url) == "storage://test-cluster/user/path/to~file.txt"


async def test_normalize_local_path_uri__tilde_in_relative_path_3(
    fake_homedir: Path, pwd: Path
) -> None:
    url = URL("file:path/to~file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "path/to~file.txt"
    assert str(url) == (pwd / "path/to~file.txt").as_uri().replace("%7E", "~")


async def test_normalize_storage_path_uri__tilde_in_absolute_path(
    client: Client,
) -> None:
    url = URL("storage:/~/path/to/file.txt")
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        normalize_storage_path_uri(url, client.username, "test-cluster", None)


async def test_normalize_local_path_uri__tilde_in_absolute_path(
    fake_homedir: Path, pwd: Path
) -> None:
    url = URL("file:/~/path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "/~/path/to/file.txt"
    assert str(url) == (pwd / "/~/path/to/file.txt").as_uri().replace("%7E", "~")


async def test_normalize_storage_path_uri__tilde_in_host(client: Client) -> None:
    url = URL("storage://~/path/to/file.txt")
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        normalize_storage_path_uri(url, client.username, "test-cluster", None)


async def test_normalize_local_path_uri__tilde_in_host(
    client: Client, pwd: Path
) -> None:
    url = URL("file://~/path/to/file.txt")
    with pytest.raises(
        ValueError, match=f"Host part is not allowed in file URI, found '~'"
    ):
        url = normalize_local_path_uri(url)


async def test_normalize_storage_path_uri__bad_scheme(client: Client) -> None:
    with pytest.raises(ValueError, match="Invalid storage scheme 'other:'"):
        url = URL("other:path/to/file.txt")
        normalize_storage_path_uri(url, client.username, "test-cluster", None)


async def test_normalize_local_path_uri__bad_scheme() -> None:
    with pytest.raises(ValueError, match="Invalid local file scheme 'other:'"):
        url = URL("other:path/to/file.txt")
        normalize_local_path_uri(url)


# The tests below check that f(f(x)) == f(x) where f is a path normalization function


async def test_normalize_storage_path_uri__no_slash__double(client: Client) -> None:
    url = URL("storage:path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/user/path/to/file.txt"
    assert str(url) == "storage://test-cluster/user/path/to/file.txt"


async def test_normalize_local_path_uri__no_slash__double(pwd: Path) -> None:
    url = URL("file:path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "path/to/file.txt"


async def test_normalize_storage_path_uri__tilde_slash__double(client: Client) -> None:
    url = URL("storage:~/path/to/file.txt")
    with pytest.raises(ValueError, match=".*Cannot expand user.*"):
        normalize_storage_path_uri(url, client.username, "test-cluster", None)


async def test_normalize_local_path_uri__tilde_slash__double() -> None:
    url = URL("file:~/path/to/file.txt")
    with pytest.raises(ValueError, match=r"Cannot expand user for "):
        normalize_local_path_uri(url)


async def test_normalize_storage_path_uri__3_slashes__double(client: Client) -> None:
    url = URL("storage:///path/to/file.txt")
    url = normalize_storage_path_uri(url, client.username, "test-cluster", None)
    assert url.scheme == "storage"
    assert url.host == "test-cluster"
    assert url.path == "/path/to/file.txt"
    assert str(url) == "storage://test-cluster/path/to/file.txt"


async def test_normalize_local_path_uri__3_slashes__double(pwd: Path) -> None:
    url = URL(f"file:///{pwd}/path/to/file.txt")
    url = normalize_local_path_uri(url)
    assert url.scheme == "file"
    assert url.host is None
    assert _extract_path(url) == pwd / "path/to/file.txt"
    assert str(url) == (pwd / "path/to/file.txt").as_uri()


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows")
def test_normalized_path() -> None:
    p = URL("file:///Z:/neuro/platform-api-clients/python/setup.py")
    assert normalize_local_path_uri(p) == p


@pytest.mark.parametrize(
    "uri_str",
    [
        "",
        "https://cluster/user/path/to",
        "file://cluster/user/path/to",
        "file:/path/to#fragment",
        "file:/path/to?key=value",
    ],
)
async def test_normalize_local_path_uri__fail(uri_str: str) -> None:
    uri = URL(uri_str)
    with pytest.raises(ValueError):
        normalize_local_path_uri(uri)
