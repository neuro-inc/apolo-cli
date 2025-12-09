import abc
import enum
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import (
    Any,
)

from yarl import URL

from ._rewrite import rewrite_module
from ._utils import AsyncContextManager


@rewrite_module
@dataclass(frozen=True)
class BucketEntry(abc.ABC):
    key: str
    bucket: "Bucket"
    size: int
    created_at: datetime | None = None
    modified_at: datetime | None = None

    @property
    def name(self) -> str:
        return PurePosixPath(self.key).name

    @property
    def uri(self) -> URL:
        # Bucket key is an arbitrary string, so it can start with "/",
        # so we have to use this way to append it to bucket url
        return URL(str(self.bucket.uri) + "/" + self.key)

    @abc.abstractmethod
    def is_file(self) -> bool:
        pass

    @abc.abstractmethod
    def is_dir(self) -> bool:
        pass


@rewrite_module
class BlobObject(BucketEntry):
    def is_file(self) -> bool:
        return not self.is_dir()

    def is_dir(self) -> bool:
        return self.key.endswith("/") and self.size == 0


@rewrite_module
class BlobCommonPrefix(BucketEntry):
    size: int = 0
    # This is "folder" analog in blobs
    # objects of this type will be only returned in
    # non recursive look-ups, to group multiple keys
    # in single entry.

    def is_file(self) -> bool:
        return False

    def is_dir(self) -> bool:
        return True


@rewrite_module
class BucketProvider(abc.ABC):
    """
    Defines how to execute generic blob operations in a specific bucket provider
    """

    bucket: "Bucket"

    @classmethod
    @abc.abstractmethod
    def create(
        cls,
        bucket: "Bucket",
        _get_credentials: Callable[[], Awaitable["BucketCredentials"]],
    ) -> AsyncContextManager["BucketProvider"]:
        pass

    @abc.abstractmethod
    def list_blobs(
        self, prefix: str, recursive: bool = False, limit: int | None = None
    ) -> AsyncContextManager[AsyncIterator[BucketEntry]]:
        pass

    @abc.abstractmethod
    async def head_blob(self, key: str) -> BucketEntry:
        pass

    @abc.abstractmethod
    async def put_blob(
        self,
        key: str,
        body: AsyncIterator[bytes] | bytes,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        pass

    @abc.abstractmethod
    def fetch_blob(
        self, key: str, offset: int = 0
    ) -> AsyncContextManager[AsyncIterator[bytes]]:
        pass

    @abc.abstractmethod
    async def delete_blob(
        self,
        key: str,
    ) -> None:
        pass

    @abc.abstractmethod
    async def get_time_diff_to_local(self) -> tuple[float, float]:
        pass


@rewrite_module
@dataclass(frozen=True)
class Bucket:
    id: str
    owner: str
    cluster_name: str
    org_name: str
    project_name: str
    provider: "Bucket.Provider"
    created_at: datetime
    imported: bool
    public: bool = False
    name: str | None = None

    @property
    def uri(self) -> URL:
        base = f"blob://{self.cluster_name}"
        if self.org_name:
            base += f"/{self.org_name}"
        return URL(f"{base}/{self.project_name}/{self.name or self.id}")

    def get_key_for_uri(self, uri: URL) -> str:
        self_uris = [self.uri]
        if self.name:
            self_uris.append(self.uri.parent / self.id)
        uri_str = str(uri)
        for self_uri in self_uris:
            self_uri_str = str(self_uri)
            if uri_str.startswith(self_uri_str):
                return uri_str[len(self_uri_str) :].lstrip("/")
        raise ValueError(f"URI {uri} is not related to bucket {self.uri}")

    class Provider(str, enum.Enum):
        AWS = "aws"
        MINIO = "minio"
        AZURE = "azure"
        GCP = "gcp"
        OPEN_STACK = "open_stack"


@rewrite_module
@dataclass(frozen=True)
class BucketUsage:
    total_bytes: int
    object_count: int


@rewrite_module
@dataclass(frozen=True)
class BucketCredentials:
    bucket_id: str
    provider: "Bucket.Provider"
    credentials: Mapping[str, str]


@rewrite_module
@dataclass(frozen=True)
class PersistentBucketCredentials:
    id: str
    owner: str
    cluster_name: str
    name: str | None
    read_only: bool
    credentials: list[BucketCredentials]


@rewrite_module
class MeasureTimeDiffMixin:
    def __init__(self) -> None:
        self._min_time_diff: float | None = 0
        self._max_time_diff: float | None = 0

    def _wrap_api_call(
        self,
        _make_call: Callable[..., Awaitable[Any]],
        get_date: Callable[[Any], datetime],
    ) -> Callable[..., Awaitable[Any]]:
        @asynccontextmanager
        async def _ctx_manager(*args: Any, **kwargs: Any) -> AsyncIterator[Any]:
            yield await _make_call(*args, **kwargs)

        manager_wrapped = self._wrap_api_call_ctx_manager(_ctx_manager, get_date)

        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            async with manager_wrapped(*args, **kwargs) as res:
                return res

        return _wrapper

    def _wrap_api_call_ctx_manager(
        self,
        _make_call: Callable[..., AsyncContextManager[Any]],
        get_date: Callable[[Any], datetime],
    ) -> Callable[..., AsyncContextManager[Any]]:
        def _average(cur_approx: float | None, new_val: float) -> float:
            if cur_approx is None:
                return new_val
            return cur_approx * 0.9 + new_val * 0.1

        @asynccontextmanager
        async def _wrapper(*args: Any, **kwargs: Any) -> AsyncIterator[Any]:
            before = time.time()
            async with _make_call(*args, **kwargs) as res:
                after = time.time()
                yield res
            try:
                server_dt = get_date(res)
            except Exception:
                pass
            else:
                server_time = server_dt.timestamp()
                # Remove 1 because server time has been truncated
                # and can be up to 1 second less than the actual value.
                self._min_time_diff = _average(
                    cur_approx=self._min_time_diff,
                    new_val=before - server_time - 1.0,
                )
                self._max_time_diff = _average(
                    cur_approx=self._min_time_diff,
                    new_val=after - server_time,
                )

        return _wrapper

    async def get_time_diff_to_local(self) -> tuple[float, float]:
        if self._min_time_diff is None or self._max_time_diff is None:
            return 0, 0
        return self._min_time_diff, self._max_time_diff
