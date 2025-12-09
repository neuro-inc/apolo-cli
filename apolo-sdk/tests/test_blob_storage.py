from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import (
    Any,
    AsyncContextManager,
)

import pytest

from apolo_sdk import (
    BlobCommonPrefix,
    BlobObject,
    Bucket,
    BucketCredentials,
    BucketEntry,
    ResourceNotFound,
)
from apolo_sdk._bucket_base import BucketProvider
from apolo_sdk._buckets import BucketFS
from apolo_sdk._utils import asyncgeneratorcontextmanager


class MockBucketProvider(BucketProvider):
    def __init__(self, bucket: Bucket):
        self.keys: dict[str, Mapping[str, Any]] = {}
        self.bucket = bucket

    @classmethod
    def create(
        cls,
        bucket: "Bucket",
        _get_credentials: Callable[[], Awaitable["BucketCredentials"]],
    ) -> AsyncContextManager[BucketProvider]:
        raise NotImplementedError

    @asyncgeneratorcontextmanager
    async def list_blobs(
        self, prefix: str, recursive: bool = False, limit: int | None = None
    ) -> AsyncIterator[BucketEntry]:
        common_prefixes = set()
        for key in self.keys:
            if key.startswith(prefix):
                post_prefix = key[len(prefix) :]
                if recursive or ("/" not in post_prefix):
                    yield await self.head_blob(key)
                elif not recursive:
                    common, _ = post_prefix.split("/", 1)
                    common_prefixes.add(prefix + common)
        for common in common_prefixes:
            yield BlobCommonPrefix(
                key=common,
                bucket=self.bucket,
                size=0,
            )

    async def head_blob(self, key: str) -> BucketEntry:
        if key not in self.keys:
            raise ResourceNotFound
        return BlobObject(
            key=key,
            size=len(self.keys[key]["data"]),
            bucket=self.bucket,
            modified_at=self.keys[key]["modified_at"],
        )

    async def put_blob(
        self,
        key: str,
        body: AsyncIterator[bytes] | bytes,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        if not isinstance(body, bytes):
            body = b"".join([chunk async for chunk in body])
        self.keys[key] = {
            "data": body,
            "modified_at": datetime.now(timezone.utc),
        }

    @asyncgeneratorcontextmanager
    async def fetch_blob(self, key: str, offset: int = 0) -> AsyncIterator[bytes]:
        data = self.keys[key]["data"]
        data = data[offset:]
        yield data

    async def delete_blob(self, key: str) -> None:
        self.keys.pop(key)

    async def get_time_diff_to_local(self) -> tuple[float, float]:
        return 0, 0


@pytest.fixture()
def mock_bucket() -> Bucket:
    return Bucket(
        id="test-bucket-id",
        name="test-bucket",
        cluster_name="test-cluster",
        owner="test-user",
        created_at=datetime.now(timezone.utc),
        provider=Bucket.Provider.AWS,
        imported=False,
        org_name="test-org",
        project_name="test-project",
    )


@pytest.fixture()
def mock_bucket_provider(mock_bucket: Bucket) -> MockBucketProvider:
    return MockBucketProvider(mock_bucket)


@pytest.fixture()
def bucket_fs(mock_bucket_provider: BucketProvider) -> BucketFS:
    return BucketFS(mock_bucket_provider)


async def test_bucket_fs_exists(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    assert await bucket_fs.exists(PurePosixPath("/"))
    assert await bucket_fs.exists(PurePosixPath(""))
    assert not await bucket_fs.exists(PurePosixPath("some_key"))
    assert not await bucket_fs.exists(PurePosixPath("some_key/foo"))

    await mock_bucket_provider.put_blob("some_key/foo", b"data")

    assert await bucket_fs.exists(PurePosixPath("some_key/foo"))
    assert await bucket_fs.exists(PurePosixPath("some_key"))
    assert not await bucket_fs.exists(PurePosixPath("some_key/foo/bar"))


async def test_bucket_fs_is_dir(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    assert await bucket_fs.is_dir(PurePosixPath("/"))
    assert await bucket_fs.is_dir(PurePosixPath(""))

    await mock_bucket_provider.put_blob("some_key/foo", b"data")
    await mock_bucket_provider.put_blob("some_key/bar/", b"")

    assert await bucket_fs.is_dir(PurePosixPath("some_key"))
    assert await bucket_fs.is_dir(PurePosixPath("some_key/bar"))
    assert not await bucket_fs.is_dir(PurePosixPath("some_key/foo"))


async def test_bucket_fs_is_file(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    assert not await bucket_fs.is_file(PurePosixPath("/"))
    assert not await bucket_fs.is_file(PurePosixPath(""))

    await mock_bucket_provider.put_blob("some_key/foo", b"data")
    await mock_bucket_provider.put_blob("some_key/bar/", b"")

    assert not await bucket_fs.is_file(PurePosixPath("some_key"))
    assert not await bucket_fs.is_file(PurePosixPath("some_key/bar"))
    assert await bucket_fs.is_file(PurePosixPath("some_key/foo"))


async def test_bucket_fs_stat(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    before = datetime.now().timestamp()
    await mock_bucket_provider.put_blob("some_key/foo", b"data")
    after = datetime.now().timestamp()

    res = await bucket_fs.stat(PurePosixPath("some_key/foo"))
    assert res.name == "foo"
    assert res.path == PurePosixPath("some_key/foo")
    assert res.size == 4
    assert res.modification_time
    assert before <= res.modification_time <= after


async def test_bucket_fs_read_chunks(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    await mock_bucket_provider.put_blob("some_key/foo", b"data")

    res1 = b""
    async with bucket_fs.read_chunks(PurePosixPath("some_key/foo")) as it:
        async for chunk in it:
            res1 += chunk
    assert res1 == b"data"

    res2 = b""
    async with bucket_fs.read_chunks(PurePosixPath("some_key/foo"), 2) as it:
        async for chunk in it:
            res2 += chunk
    assert res2 == b"ta"


async def test_bucket_fs_write_chunks(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    async def gen() -> AsyncIterator[bytes]:
        for _ in range(10):
            yield b"some_data"

    await bucket_fs.write_chunks(PurePosixPath("some_key/foo"), gen())
    assert await bucket_fs.read(PurePosixPath("some_key/foo")) == b"some_data" * 10


async def test_bucket_fs_iter_dir(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    await mock_bucket_provider.put_blob("some_key/", b"")
    await mock_bucket_provider.put_blob("some_key/foo", b"data")
    await mock_bucket_provider.put_blob("some_key/bar1/", b"")
    await mock_bucket_provider.put_blob("some_key/bar2/baz", b"data")

    res = set()
    async with bucket_fs.iter_dir(PurePosixPath("some_key")) as it:
        async for path in it:
            res.add(str(path))

    assert res == {"some_key/foo", "some_key/bar1", "some_key/bar2"}


async def test_bucket_fs_mkdir(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    path = PurePosixPath("some_key/foo")
    await bucket_fs.mkdir(path)
    assert await bucket_fs.exists(path)
    assert await bucket_fs.is_dir(path)


async def test_bucket_fs_mkdir_root(
    bucket_fs: BucketFS, mock_bucket_provider: MockBucketProvider
) -> None:
    with pytest.raises(ValueError):
        await bucket_fs.mkdir(PurePosixPath(""))
