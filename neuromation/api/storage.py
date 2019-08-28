import asyncio
import enum
import errno
import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISREG
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
)

import attr
from yarl import URL

import neuromation

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
from .config import _Config
from .core import ResourceNotFound, _Core
from .url_utils import (
    _extract_path,
    normalize_local_path_uri,
    normalize_storage_path_uri,
)
from .users import Action
from .utils import NoPublicConstructor


MAX_OPEN_FILES = 100
READ_SIZE = 2 ** 20  # 1 MiB

Printer = Callable[[str], None]


class FileStatusType(str, enum.Enum):
    DIRECTORY = "DIRECTORY"
    FILE = "FILE"


@dataclass(frozen=True)
class FileStatus:
    path: str
    size: int
    type: FileStatusType
    modification_time: int
    permission: Action

    def is_file(self) -> bool:
        return self.type == FileStatusType.FILE

    def is_dir(self) -> bool:
        return self.type == FileStatusType.DIRECTORY

    @property
    def name(self) -> str:
        return Path(self.path).name


class Storage(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: _Config) -> None:
        self._core = core
        self._config = config
        self._file_sem = asyncio.BoundedSemaphore(MAX_OPEN_FILES)

    def _uri_to_path(self, uri: URL) -> str:
        uri = normalize_storage_path_uri(uri, self._config.auth_token.username)
        prefix = uri.host + "/" if uri.host else ""
        return prefix + uri.path.lstrip("/")

    async def ls(self, uri: URL) -> List[FileStatus]:
        url = self._config.cluster_config.storage_url / self._uri_to_path(uri)
        url = url.with_query(op="LISTSTATUS")

        async with self._core.request("GET", url) as resp:
            res = await resp.json()
            return [
                _file_status_from_api(status)
                for status in res["FileStatuses"]["FileStatus"]
            ]

    async def glob(self, uri: URL, *, dironly: bool = False) -> AsyncIterator[URL]:
        if not _has_magic(uri.path):
            yield uri
            return
        basename = uri.name
        glob_in_dir: Callable[[URL, str, bool], AsyncIterator[URL]]
        if not _has_magic(basename):
            glob_in_dir = self._glob0
        elif not _isrecursive(basename):
            glob_in_dir = self._glob1
        else:
            glob_in_dir = self._glob2
        async for parent in self.glob(uri.parent, dironly=True):
            async for x in glob_in_dir(parent, basename, dironly):
                yield x

    async def _glob2(
        self, parent: URL, pattern: str, dironly: bool
    ) -> AsyncIterator[URL]:
        assert _isrecursive(pattern)
        yield parent
        async for x in self._rlistdir(parent, dironly):
            yield x

    async def _glob1(
        self, parent: URL, pattern: str, dironly: bool
    ) -> AsyncIterator[URL]:
        allow_hidden = _ishidden(pattern)
        match = re.compile(fnmatch.translate(pattern)).fullmatch
        async for stat in self._iterdir(parent, dironly):
            name = stat.path
            if (allow_hidden or not _ishidden(name)) and match(name):
                yield parent / name

    async def _glob0(
        self, parent: URL, basename: str, dironly: bool
    ) -> AsyncIterator[URL]:
        uri = parent / basename
        try:
            await self.stats(uri)
        except ResourceNotFound:
            return
        yield uri

    async def _iterdir(self, uri: URL, dironly: bool) -> AsyncIterator[FileStatus]:
        for stat in await self.ls(uri):
            if not dironly or stat.is_dir():
                yield stat

    async def _rlistdir(self, uri: URL, dironly: bool) -> AsyncIterator[URL]:
        async for stat in self._iterdir(uri, dironly):
            name = stat.path
            if not _ishidden(name):
                x = uri / name
                yield x
                if stat.is_dir():
                    async for y in self._rlistdir(x, dironly):
                        yield y

    async def mkdirs(
        self, uri: URL, *, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if not exist_ok:
            try:
                await self.stats(uri)
            except ResourceNotFound:
                pass
            else:
                raise FileExistsError(errno.EEXIST, "File exists", str(uri))

        if not parents:
            parent = uri
            while not parent.name and parent != parent.parent:
                parent = parent.parent
            parent = parent.parent
            if parent != parent.parent:
                try:
                    await self.stats(parent)
                except ResourceNotFound:
                    raise FileNotFoundError(
                        errno.ENOENT, "No such directory", str(parent)
                    )

        url = self._config.cluster_config.storage_url / self._uri_to_path(uri)
        url = url.with_query(op="MKDIRS")

        async with self._core.request("PUT", url) as resp:
            resp  # resp.status == 201

    async def create(self, uri: URL, data: AsyncIterator[bytes]) -> None:
        path = self._uri_to_path(uri)
        assert path, "Creation in root is not allowed"
        url = self._config.cluster_config.storage_url / path
        url = url.with_query(op="CREATE")
        timeout = attr.evolve(self._core.timeout, sock_read=None)

        async with self._core.request("PUT", url, data=data, timeout=timeout) as resp:
            resp  # resp.status == 201

    async def stats(self, uri: URL) -> FileStatus:
        url = self._config.cluster_config.storage_url / self._uri_to_path(uri)
        url = url.with_query(op="GETFILESTATUS")

        async with self._core.request("GET", url) as resp:
            res = await resp.json()
            return _file_status_from_api(res["FileStatus"])

    async def _is_dir(self, uri: URL) -> bool:
        if uri.scheme == "storage":
            try:
                stat = await self.stats(uri)
                return stat.is_dir()
            except ResourceNotFound:
                pass
        elif uri.scheme == "file":
            path = _extract_path(uri)
            return path.is_dir()
        return False

    async def open(self, uri: URL) -> AsyncIterator[bytes]:
        url = self._config.cluster_config.storage_url / self._uri_to_path(uri)
        url = url.with_query(op="OPEN")
        timeout = attr.evolve(self._core.timeout, sock_read=None)

        async with self._core.request("GET", url, timeout=timeout) as resp:
            async for data in resp.content.iter_any():
                yield data

    async def rm(self, uri: URL, *, recursive: bool = False) -> None:
        path = self._uri_to_path(uri)
        # TODO (asvetlov): add a minor protection against deleting everything from root
        # or user volume root, however force operation here should allow user to delete
        # everything.
        #
        # Now it doesn't make sense because URL for root folder (storage:///) is not
        # supported
        #
        # parts = path.split('/')
        # if final_path == root_data_path or final_path.parent == root_data_path:
        #     raise ValueError("Invalid path value.")

        if not recursive:
            stats = await self.stats(uri)
            if stats.type is FileStatusType.DIRECTORY:
                raise IsADirectoryError(
                    errno.EISDIR, "Is a directory, use recursive remove", str(uri)
                )

        url = self._config.cluster_config.storage_url / path
        url = url.with_query(op="DELETE")

        async with self._core.request("DELETE", url) as resp:
            resp  # resp.status == 204

    async def mv(self, src: URL, dst: URL) -> None:
        url = self._config.cluster_config.storage_url / self._uri_to_path(src)
        url = url.with_query(op="RENAME", destination="/" + self._uri_to_path(dst))

        async with self._core.request("POST", url) as resp:
            resp  # resp.status == 204

    # high-level helpers

    async def _iterate_file(
        self, src: Path, dst: URL, *, progress: AbstractFileProgress
    ) -> AsyncIterator[bytes]:
        loop = asyncio.get_event_loop()
        src_url = URL(src.as_uri())
        async with self._file_sem:
            with src.open("rb") as stream:
                size = os.stat(stream.fileno()).st_size
                progress.start(StorageProgressStart(src_url, dst, size))
                chunk = await loop.run_in_executor(None, stream.read, READ_SIZE)
                pos = len(chunk)
                while chunk:
                    progress.step(StorageProgressStep(src_url, dst, pos, size))
                    yield chunk
                    chunk = await loop.run_in_executor(None, stream.read, READ_SIZE)
                    pos += len(chunk)
                progress.complete(StorageProgressComplete(src_url, dst, size))

    async def upload_file(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        progress: Optional[AbstractFileProgress] = None,
    ) -> None:
        if progress is None:
            progress = _DummyProgress()
        src = normalize_local_path_uri(src)
        dst = normalize_storage_path_uri(dst, self._config.auth_token.username)
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
        try:
            dst_stat = await self.stats(dst)
            if dst_stat.is_dir():
                raise IsADirectoryError(errno.EISDIR, "Is a directory", str(dst))
        except ResourceNotFound:
            # target doesn't exist, lookup for parent dir
            try:
                dst_parent_stat = await self.stats(dst.parent)
                if not dst_parent_stat.is_dir():
                    # parent path should be a folder
                    raise NotADirectoryError(
                        errno.ENOTDIR, "Not a directory", str(dst.parent)
                    )
            except ResourceNotFound:
                raise NotADirectoryError(
                    errno.ENOTDIR, "Not a directory", str(dst.parent)
                )
        else:
            try:
                src_stat = path.stat()
            except OSError:
                pass
            else:
                if (
                    S_ISREG(src_stat.st_mode)
                    and dst_stat.size == src_stat.st_size
                    and dst_stat.modification_time >= src_stat.st_mtime
                ):
                    return
        await self._upload_file(path, dst, update=update, progress=progress)

    async def _upload_file(
        self, src_path: Path, dst: URL, *, update: bool, progress: AbstractFileProgress
    ) -> None:
        await self.create(dst, self._iterate_file(src_path, dst, progress=progress))

    async def upload_dir(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        progress: Optional[AbstractRecursiveFileProgress] = None,
    ) -> None:
        if progress is None:
            progress = _DummyProgress()
        src = normalize_local_path_uri(src)
        dst = normalize_storage_path_uri(dst, self._config.auth_token.username)
        path = _extract_path(src).resolve()
        if not path.exists():
            raise FileNotFoundError(errno.ENOENT, "No such file", str(path))
        if not path.is_dir():
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", str(path))
        await self._upload_dir(src, path, dst, update=update, progress=progress)

    async def _upload_dir(
        self,
        src: URL,
        src_path: Path,
        dst: URL,
        *,
        update: bool,
        progress: AbstractRecursiveFileProgress,
    ) -> None:
        try:
            await self.mkdirs(dst, exist_ok=True)
        except neuromation.api.IllegalArgumentError:
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", str(dst))
        progress.enter(StorageProgressEnterDir(src, dst))
        tasks = []
        if update:
            dst_entries = {item.name: item for item in await self.ls(dst)}
        else:
            dst_entries = {}
        async with self._file_sem:
            folder = sorted(
                src_path.iterdir(), key=lambda item: (item.is_dir(), item.name)
            )
        for child in folder:
            name = child.name
            if child.is_file():
                if name in dst_entries:
                    src_stat = child.stat()
                    dst_entry = dst_entries[name]
                    if (
                        dst_entry.is_file()
                        and dst_entry.size == src_stat.st_size
                        and dst_entry.modification_time >= src_stat.st_mtime
                    ):
                        continue
                tasks.append(
                    self._upload_file(
                        src_path / name, dst / name, update=update, progress=progress
                    )
                )
            elif child.is_dir():
                tasks.append(
                    self._upload_dir(
                        src / name,
                        src_path / name,
                        dst / name,
                        update=update,
                        progress=progress,
                    )
                )
            else:
                # This case is for uploading non-regular file,
                # e.g. blocking device or unix socket
                # Coverage temporary skipped, the line is waiting for a champion
                progress.fail(
                    StorageProgressFail(
                        src / name,
                        dst / name,
                        f"Cannot upload {child}, not regular file/directory",
                    )
                )  # pragma: no cover
        await _run_concurrently(tasks)
        progress.leave(StorageProgressLeaveDir(src, dst))

    async def download_file(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        progress: Optional[AbstractFileProgress] = None,
    ) -> None:
        if progress is None:
            progress = _DummyProgress()
        src = normalize_storage_path_uri(src, self._config.auth_token.username)
        dst = normalize_local_path_uri(dst)
        path = _extract_path(dst)
        src_stat = await self.stats(src)
        if not src_stat.is_file():
            raise IsADirectoryError(errno.EISDIR, "Is a directory", str(src))
        try:
            dst_stat = path.stat()
        except OSError:
            pass
        else:
            if (
                S_ISREG(dst_stat.st_mode)
                and dst_stat.st_size == src_stat.size
                and dst_stat.st_mtime >= src_stat.modification_time
            ):
                return
        await self._download_file(
            src, dst, path, src_stat.size, update=update, progress=progress
        )

    async def _download_file(
        self,
        src: URL,
        dst: URL,
        dst_path: Path,
        size: int,
        *,
        update: bool,
        progress: AbstractFileProgress,
    ) -> None:
        loop = asyncio.get_event_loop()
        async with self._file_sem:
            with dst_path.open("wb") as stream:
                progress.start(StorageProgressStart(src, dst, size))
                pos = 0
                async for chunk in self.open(src):
                    pos += len(chunk)
                    progress.step(StorageProgressStep(src, dst, pos, size))
                    await loop.run_in_executor(None, stream.write, chunk)
                progress.complete(StorageProgressComplete(src, dst, size))

    async def download_dir(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        progress: Optional[AbstractRecursiveFileProgress] = None,
    ) -> None:
        if progress is None:
            progress = _DummyProgress()
        src = normalize_storage_path_uri(src, self._config.auth_token.username)
        dst = normalize_local_path_uri(dst)
        path = _extract_path(dst)
        await self._download_dir(src, dst, path, update=update, progress=progress)

    async def _download_dir(
        self,
        src: URL,
        dst: URL,
        dst_path: Path,
        *,
        update: bool,
        progress: AbstractRecursiveFileProgress,
    ) -> None:
        dst_path.mkdir(parents=True, exist_ok=True)
        progress.enter(StorageProgressEnterDir(src, dst))
        tasks = []
        if update:
            async with self._file_sem:
                dst_entries = {item.name: item for item in dst_path.iterdir()}
        else:
            dst_entries = {}
        folder = sorted(await self.ls(src), key=lambda item: (item.is_dir(), item.name))
        for child in folder:
            name = child.name
            if child.is_file():
                if name in dst_entries:
                    dst_entry = dst_entries[name]
                    if dst_entry.is_file():
                        dst_stat = dst_entry.stat()
                        if (
                            dst_stat.st_size == child.size
                            and dst_stat.st_mtime >= child.modification_time
                        ):
                            continue
                tasks.append(
                    self._download_file(
                        src / name,
                        dst / name,
                        dst_path / name,
                        child.size,
                        update=update,
                        progress=progress,
                    )
                )
            elif child.is_dir():
                tasks.append(
                    self._download_dir(
                        src / name,
                        dst / name,
                        dst_path / name,
                        update=update,
                        progress=progress,
                    )
                )
            else:
                progress.fail(
                    StorageProgressFail(
                        src / name,
                        dst / name,
                        f"Cannot download {child}, not regular file/directory",
                    )
                )  # pragma: no cover
        await _run_concurrently(tasks)
        progress.leave(StorageProgressLeaveDir(src, dst))


_magic_check = re.compile("(?:[*?[])")


def _has_magic(s: str) -> bool:
    return _magic_check.search(s) is not None


def _ishidden(name: str) -> bool:
    return name.startswith(".")


def _isrecursive(pattern: str) -> bool:
    return pattern == "**"


def _file_status_from_api(values: Dict[str, Any]) -> FileStatus:
    return FileStatus(
        path=values["path"],
        type=FileStatusType(values["type"]),
        size=int(values["length"]),
        modification_time=int(values["modificationTime"]),
        permission=Action(values["permission"]),
    )


async def _run_concurrently(coros: Iterable[Awaitable[Any]]) -> None:
    loop = asyncio.get_event_loop()
    tasks: "Iterable[asyncio.Future[Any]]" = [loop.create_task(coro) for coro in coros]
    if not tasks:
        return
    try:
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            await task
    except:  # noqa: E722
        for task in tasks:
            task.cancel()
        # wait for actual cancellation, ignore all exceptions raised from tasks
        if tasks:
            await asyncio.wait(tasks)
        raise  # pragma: no cover


class _DummyProgress(AbstractRecursiveFileProgress):
    def start(self, data: StorageProgressStart) -> None:
        pass

    def complete(self, data: StorageProgressComplete) -> None:
        pass

    def step(self, data: StorageProgressStep) -> None:
        pass

    def enter(self, data: StorageProgressEnterDir) -> None:
        pass

    def leave(self, data: StorageProgressLeaveDir) -> None:
        pass

    def fail(self, data: StorageProgressFail) -> None:
        pass
