from collections.abc import Callable

from apolo_sdk import Client

_MakeClient = Callable[..., Client]


async def test_client_username(make_client: _MakeClient) -> None:
    async with make_client("http://example.com") as client:
        assert client.username == "user"


async def test_client_double_closing(make_client: _MakeClient) -> None:
    client = make_client("http://example.com")
    assert not client._closed
    await client.close()
    assert client._closed
    await client.close()
    assert client._closed
