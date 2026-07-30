from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest

from apolo_sdk._s3_bucket_provider import S3Provider


class StreamingBody:
    """Streaming body covering both sides of aiobotocore 3.8's enter change."""

    def __init__(self, *chunks: bytes, enter_returns_self: bool) -> None:
        self._chunks = chunks
        self._enter_returns_self = enter_returns_self

    async def __aenter__(self) -> Any:
        if self._enter_returns_self:
            return self
        return LegacyStream(*self._chunks)

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def _iterate(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._iterate()


class LegacyContent:
    def __init__(self, *chunks: bytes) -> None:
        self._chunks = chunks

    async def iter_any(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


class LegacyStream:
    def __init__(self, *chunks: bytes) -> None:
        self.content = LegacyContent(*chunks)


@pytest.mark.parametrize(
    "enter_returns_self",
    [False, True],
    ids=["pre-3.8-raw-enter-result", "3.8-body-enter-result"],
)
async def test_fetch_blob_uses_public_streaming_body_api(
    enter_returns_self: bool,
) -> None:
    body = StreamingBody(b"first", b"second", enter_returns_self=enter_returns_self)
    client = AsyncMock()
    client.get_object.return_value = {"Body": body}
    provider = object.__new__(S3Provider)
    provider._client = client
    provider._bucket_name = "bucket"

    async with provider.fetch_blob("path/blob", offset=10) as stream:
        chunks = [chunk async for chunk in stream]

    assert chunks == [b"first", b"second"]
    client.get_object.assert_awaited_once_with(
        Bucket="bucket", Key="path/blob", Range="bytes=10-"
    )
