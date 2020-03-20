import asyncio
import base64
import datetime
import errno
import fnmatch
import hashlib
import os
import re
import time
from dataclasses import dataclass
from email.utils import parsedate
from pathlib import Path, PurePath
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    cast,
)

import aiohttp
import attr
from yarl import URL

from .abc import (
    AbstractFileProgress,
    AbstractRecursiveFileProgress,
    StorageProgressComplete,
    StorageProgressEnterDir,
    StorageProgressFail,
    StorageProgressLeaveDir,
    StorageProgressStart,
    StorageProgressStep,
)
from .config import Config
from .core import _Core
from .storage import _always, _has_magic, _run_concurrently
from .url_utils import _extract_path, normalize_local_path_uri, normalize_obj_path_uri
from .users import Action
from .utils import NoPublicConstructor, asynccontextmanager, retries


MAX_OPEN_FILES = 20
READ_SIZE = 2 ** 20  # 1 MiB

ProgressQueueItem = Optional[Any]


def _format_bucket_uri(bucket_name: str, key: str = "") -> URL:
    return URL.build(scheme="object", host=bucket_name, path="/" + key.lstrip("/"))


@dataclass(frozen=True)
class BucketListing:
    name: str
    modification_time: int
    # XXX: Add real bucket permission access level
    permission: Action = Action.READ

    @property
    def uri(self) -> URL:
        return _format_bucket_uri(self.name, "")


@dataclass(frozen=True)
class ObjectListing:
    key: str
    size: int
    modification_time: int

    @property
    def name(self) -> str:
        return PurePath(self.key).name

    bucket_name: str

    @property
    def uri(self) -> URL:
        return _format_bucket_uri(self.bucket_name, self.key)


@dataclass(frozen=True)
class PrefixListing:
    prefix: str

    @property
    def name(self) -> str:
        return PurePath(self.prefix).name

    bucket_name: str

    @property
    def uri(self) -> URL:
        return _format_bucket_uri(self.bucket_name, self.prefix)


ListResult = Union[PrefixListing, ObjectListing]


class Object:
    def __init__(self, resp: aiohttp.ClientResponse, stats: ObjectListing):
        self._resp = resp
        self.stats = stats

    @property
    def body_stream(self) -> aiohttp.StreamReader:
        return self._resp.content


class ObjectStorage(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config
        self._max_keys = 10000
        self._file_sem = asyncio.BoundedSemaphore(MAX_OPEN_FILES)

    async def list_buckets(self) -> List[BucketListing]:
        url = self._config.object_storage_url / "b" / ""
        auth = await self._config._api_auth()

        async with self._core.request("GET", url, auth=auth) as resp:
            res = await resp.json()
            return [_bucket_status_from_data(bucket) for bucket in res]

    async def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        recursive: bool = False,
        max_keys: int = 10000,
    ) -> List[ListResult]:
        url = self._config.object_storage_url / "o" / bucket_name
        auth = await self._config._api_auth()

        query = {"recursive": str(recursive).lower(), "max_keys": str(self._max_keys)}
        if prefix:
            query["prefix"] = prefix
        url = url.with_query(query)

        contents: List[ListResult] = []
        common_prefixes: List[ListResult] = []
        while True:
            async with self._core.request("GET", url, auth=auth) as resp:
                res = await resp.json()
                contents.extend(
                    [_obj_status_from_key(bucket_name, key) for key in res["contents"]]
                )
                common_prefixes.extend(
                    [
                        _obj_status_from_prefix(bucket_name, prefix)
                        for prefix in res["common_prefixes"]
                    ]
                )
                if res["is_truncated"] and res["contents"]:
                    start_after = res["contents"][-1]["key"]
                    url = url.update_query(start_after=start_after)
                else:
                    break
        return common_prefixes + contents

    async def glob_objects(self, bucket_name: str, pattern: str) -> List[ObjectListing]:
        pattern = pattern.lstrip("/")
        parts = pattern.split("/")
        # Limit the search to prefix of keys
        prefix = ""
        for part in parts:
            if _has_magic(part):
                break
            else:
                prefix += part + "/"

        match = re.compile(fnmatch.translate(pattern)).fullmatch
        res = []
        for obj_status in await self.list_objects(
            bucket_name, prefix=prefix, recursive=True
        ):
            # We don't have PrefixListing if recursive is used
            obj_status = cast(ObjectListing, obj_status)
            if match(obj_status.key):
                res.append(obj_status)
        return res

    async def head_object(self, bucket_name: str, key: str) -> ObjectListing:
        url = self._config.object_storage_url / "o" / bucket_name / key
        auth = await self._config._api_auth()

        async with self._core.request("HEAD", url, auth=auth) as resp:
            return _obj_status_from_response(bucket_name, key, resp)

    @asynccontextmanager
    async def get_object(self, bucket_name: str, key: str) -> AsyncIterator[Object]:
        """ Return object status and body stream of the object
        """
        url = self._config.object_storage_url / "o" / bucket_name / key
        auth = await self._config._api_auth()

        timeout = attr.evolve(self._core.timeout, sock_read=None)
        async with self._core.request("GET", url, timeout=timeout, auth=auth) as resp:
            stats = _obj_status_from_response(bucket_name, key, resp)
            yield Object(resp, stats)

    async def fetch_object(self, bucket_name: str, key: str) -> AsyncIterator[bytes]:
        """ Return only bytes data of the object
        """
        async with self.get_object(bucket_name, key) as obj:
            async for data in obj.body_stream.iter_any():
                yield data

    async def put_object(
        self,
        bucket_name: str,
        key: str,
        body_stream: AsyncIterator[bytes],
        size: int,
        content_md5: Optional[str] = None,
    ) -> str:
        url = self._config.object_storage_url / "o" / bucket_name / key
        auth = await self._config._api_auth()
        timeout = attr.evolve(self._core.timeout, sock_read=None)

        # We don't provide Content-Length as transfer endcoding will be `chunked`.
        # But the server needs to know the decoded length of the file.
        headers = {"X-Content-Length": str(size)}
        if content_md5 is not None:
            headers["Content-MD5"] = content_md5

        async with self._core.request(
            "PUT", url, data=body_stream, timeout=timeout, auth=auth
        ) as resp:
            etag = resp.headers["ETag"]
            return etag

    # high-level helpers

    async def _iterate_file(
        self,
        src: Path,
        dst: URL,
        size: int,
        *,
        queue: "asyncio.Queue[ProgressQueueItem]",
    ) -> AsyncIterator[bytes]:
        loop = asyncio.get_event_loop()
        src_url = URL(src.as_uri())
        async with self._file_sem:
            with src.open("rb") as stream:
                await queue.put(StorageProgressStart(src_url, dst, size))
                chunk = await loop.run_in_executor(None, stream.read, READ_SIZE)
                pos = len(chunk)
                while chunk:
                    await queue.put(StorageProgressStep(src_url, dst, pos, size))
                    yield chunk
                    chunk = await loop.run_in_executor(None, stream.read, READ_SIZE)
                    pos += len(chunk)
                await queue.put(StorageProgressComplete(src_url, dst, size))

    async def upload_file(
        self, src: URL, dst: URL, *, progress: Optional[AbstractFileProgress] = None,
    ) -> None:
        src = normalize_local_path_uri(src)
        dst = normalize_obj_path_uri(dst)

        path = _extract_path(src)
        try:
            if not path.exists():
                raise FileNotFoundError(errno.ENOENT, "No such file", str(path))
            if path.is_dir():
                raise IsADirectoryError(
                    errno.EISDIR, "Is a directory, use recursive copy", str(path)
                )
        except OSError as e:
            if getattr(e, "winerror", None) not in (1, 87):
                raise
            # Ignore stat errors for device files like NUL or CON on Windows.
            # See https://bugs.python.org/issue37074
        queue: "asyncio.Queue[ProgressQueueItem]" = asyncio.Queue()
        await _run_progress(queue, progress, self._upload_file(path, dst, queue=queue))

    async def _upload_file(
        self, src_path: Path, dst: URL, *, queue: "asyncio.Queue[ProgressQueueItem]",
    ) -> None:
        assert dst.host
        bucket_name = dst.host
        key = dst.path.lstrip("/")
        size = os.stat(src_path).st_size
        # Be careful not to have too many opened files.
        async with self._file_sem:
            content_md5 = await calc_md5(src_path)

        for retry in retries(f"Fail to upload {dst}"):
            async with retry:
                await self.put_object(
                    bucket_name=bucket_name,
                    key=key,
                    body_stream=self._iterate_file(src_path, dst, size, queue=queue),
                    size=size,
                    content_md5=content_md5,
                )

    async def upload_dir(
        self,
        src: URL,
        dst: URL,
        *,
        filter: Optional[Callable[[str], Awaitable[bool]]] = None,
        progress: Optional[AbstractRecursiveFileProgress] = None,
    ) -> None:
        if filter is None:
            filter = _always
        src = normalize_local_path_uri(src)
        dst = normalize_obj_path_uri(dst)
        path = _extract_path(src).resolve()
        if not path.exists():
            raise FileNotFoundError(errno.ENOENT, "No such file", str(path))
        if not path.is_dir():
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", str(path))
        queue: "asyncio.Queue[ProgressQueueItem]" = asyncio.Queue()
        await _run_progress(
            queue,
            progress,
            self._upload_dir(src, path, dst, "", filter=filter, queue=queue),
        )

    async def _upload_dir(
        self,
        src: URL,
        src_path: Path,
        dst: URL,
        rel_path: str,
        *,
        filter: Callable[[str], Awaitable[bool]],
        queue: "asyncio.Queue[ProgressQueueItem]",
    ) -> None:
        tasks = []
        await queue.put(StorageProgressEnterDir(src, dst))
        loop = asyncio.get_event_loop()
        async with self._file_sem:
            folder = await loop.run_in_executor(None, lambda: list(src_path.iterdir()))

        for child in folder:
            name = child.name
            child_rel_path = f"{rel_path}/{name}" if rel_path else name
            if not await filter(child_rel_path):
                continue
            if child.is_file():
                tasks.append(
                    self._upload_file(src_path / name, dst / name, queue=queue)
                )
            elif child.is_dir():
                tasks.append(
                    self._upload_dir(
                        src / name,
                        src_path / name,
                        dst / name,
                        child_rel_path,
                        filter=filter,
                        queue=queue,
                    )
                )
            else:
                await queue.put(
                    StorageProgressFail(
                        src / name,
                        dst / name,
                        f"Cannot upload {child}, not regular file/directory",
                    )
                )
        await _run_concurrently(tasks)
        await queue.put(StorageProgressLeaveDir(src, dst))

    async def download_file(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        progress: Optional[AbstractFileProgress] = None,
    ) -> None:
        src = normalize_obj_path_uri(src)
        dst = normalize_local_path_uri(dst)
        path = _extract_path(dst)
        assert src.host
        src_stat = await self.head_object(
            bucket_name=src.host, key=src.path.lstrip("/")
        )
        queue: "asyncio.Queue[ProgressQueueItem]" = asyncio.Queue()
        await _run_progress(
            queue,
            progress,
            self._download_file(src, dst, path, src_stat.size, queue=queue),
        )

    async def _download_file(
        self,
        src: URL,
        dst: URL,
        dst_path: Path,
        size: int,
        *,
        queue: "asyncio.Queue[ProgressQueueItem]",
    ) -> None:
        loop = asyncio.get_event_loop()
        async with self._file_sem:
            with dst_path.open("wb") as stream:
                await queue.put(StorageProgressStart(src, dst, size))
                for retry in retries(f"Fail to download {src}"):
                    async with retry:
                        pos = 0
                        assert src.host is not None
                        async for chunk in self.fetch_object(
                            bucket_name=src.host, key=src.path.lstrip("/")
                        ):
                            pos += len(chunk)
                            await queue.put(StorageProgressStep(src, dst, pos, size))
                            await loop.run_in_executor(None, stream.write, chunk)
                await queue.put(StorageProgressComplete(src, dst, size))

    async def download_dir(
        self,
        src: URL,
        dst: URL,
        *,
        filter: Optional[Callable[[str], Awaitable[bool]]] = None,
        progress: Optional[AbstractRecursiveFileProgress] = None,
    ) -> None:
        if filter is None:
            filter = _always
        src = normalize_obj_path_uri(src)
        dst = normalize_local_path_uri(dst)
        path = _extract_path(dst)
        queue: "asyncio.Queue[ProgressQueueItem]" = asyncio.Queue()
        await _run_progress(
            queue,
            progress,
            self._download_dir(src, dst, path, filter=filter, queue=queue),
        )

    async def _download_dir(
        self,
        src: URL,
        dst: URL,
        dst_path: Path,
        *,
        filter: Callable[[str], Awaitable[bool]],
        queue: "asyncio.Queue[ProgressQueueItem]",
    ) -> None:
        dst_path.mkdir(parents=True, exist_ok=True)
        await queue.put(StorageProgressEnterDir(src, dst))
        assert src.host
        tasks = []

        prefix_path = src.path.strip("/")
        if prefix_path:
            prefix_path += "/"
        for retry in retries(f"Fail to list {src}"):
            async with retry:
                folder = await self.list_objects(
                    bucket_name=src.host, prefix=prefix_path, recursive=False
                )

        for child in folder:
            name = child.name
            assert child.path.startswith(prefix_path)
            child_rel_path = child.path[len(prefix_path) :]
            if not await filter(child_rel_path):
                continue
            if child.is_file():
                tasks.append(
                    self._download_file(
                        src / name,
                        dst / name,
                        dst_path / name,
                        child.size,
                        queue=queue,
                    )
                )
            elif child.is_dir():
                tasks.append(
                    self._download_dir(
                        src / name,
                        dst / name,
                        dst_path / name,
                        filter=filter,
                        queue=queue,
                    )
                )
        await _run_concurrently(tasks)
        await queue.put(StorageProgressLeaveDir(src, dst))


def _bucket_status_from_data(data: Dict[str, Any]) -> BucketListing:
    mtime = datetime.datetime.fromisoformat(data["creation_date"]).timestamp()
    return BucketListing(name=data["name"], modification_time=int(mtime))


def _obj_status_from_key(bucket_name: str, data: Dict[str, Any]) -> ObjectListing:
    return ObjectListing(
        bucket_name=bucket_name,
        key=data["key"],
        size=int(data["size"]),
        modification_time=int(data["last_modified"]),
    )


def _obj_status_from_prefix(bucket_name: str, data: Dict[str, Any]) -> PrefixListing:
    return PrefixListing(bucket_name=bucket_name, prefix=data["prefix"])


def _obj_status_from_response(
    bucket_name: str, key: str, resp: aiohttp.ClientResponse
) -> ObjectListing:
    modification_time = 0
    if "Last-Modified" in resp.headers:
        timetuple = parsedate(resp.headers["Last-Modified"])
        if timetuple is not None:
            modification_time = int(time.mktime(timetuple))
    return ObjectListing(
        bucket_name=bucket_name,
        key=key,
        size=resp.content_length or 0,
        modification_time=modification_time,
    )


async def _run_progress(
    queue: "asyncio.Queue[ProgressQueueItem]",
    progress: Optional[AbstractFileProgress],
    coro: Awaitable[None],
) -> None:
    async def wrapped() -> None:
        try:
            await coro
        finally:
            await queue.put(None)

    loop = asyncio.get_event_loop()
    task = loop.create_task(wrapped())
    while True:
        item = await queue.get()
        if item is None:
            break

        if progress is None:
            # Just ignore event if we don't have a listener
            continue
        if isinstance(item, StorageProgressStart):
            progress.start(item)
        elif isinstance(item, StorageProgressComplete):
            progress.complete(item)
        elif isinstance(item, StorageProgressStep):
            progress.step(item)
        else:
            progress = cast(AbstractRecursiveFileProgress, progress)

            if isinstance(item, StorageProgressEnterDir):
                progress.enter(item)
            elif isinstance(item, StorageProgressLeaveDir):
                progress.leave(item)
            elif isinstance(item, StorageProgressFail):
                progress.fail(item)

    await task


async def calc_md5(path: Path) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _calc_md5_blocking, path)


def _calc_md5_blocking(path: Path) -> str:
    md5 = hashlib.md5()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(READ_SIZE)
            if not chunk:
                break
            md5.update(chunk)
    return base64.b64encode(md5.digest()).decode("ascii")
