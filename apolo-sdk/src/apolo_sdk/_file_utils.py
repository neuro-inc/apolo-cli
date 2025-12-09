import abc
import asyncio
import errno
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import (
    AbstractSet,
    Generic,
    TypeVar,
)

from yarl import URL

from ._abc import (
    AbstractDeleteProgress,
    AbstractFileProgress,
    AbstractRecursiveFileProgress,
    StorageProgressComplete,
    StorageProgressDelete,
    StorageProgressEnterDir,
    StorageProgressFail,
    StorageProgressLeaveDir,
    StorageProgressStart,
    StorageProgressStep,
    _AsyncAbstractDeleteProgress,
    _AsyncAbstractFileProgress,
    _AsyncAbstractRecursiveFileProgress,
)
from ._file_filter import AsyncFilterFunc, FileFilter
from ._storage import _always, run_concurrently, run_progress
from ._utils import AsyncContextManager, asyncgeneratorcontextmanager, queue_calls

logger = logging.getLogger(__package__)


TIME_THRESHOLD = 1.0
MAX_OPEN_FILES = 10
READ_SIZE = 2**20  # 1 MiB


FS_PATH = TypeVar("FS_PATH")
FS_PATH_STAT = TypeVar("FS_PATH_STAT")


# file_sem in FS


class FileSystem(Generic[FS_PATH], abc.ABC):
    fs_name: str
    supports_offset_read: bool
    supports_offset_write: bool

    @dataclass(frozen=True)
    class BasicStat(Generic[FS_PATH_STAT]):
        path: FS_PATH_STAT
        name: str
        size: int
        modification_time: float | None

    @abc.abstractmethod
    async def exists(self, path: FS_PATH) -> bool:
        pass

    @abc.abstractmethod
    async def is_dir(self, path: FS_PATH) -> bool:
        pass

    @abc.abstractmethod
    async def is_file(self, path: FS_PATH) -> bool:
        pass

    @abc.abstractmethod
    async def stat(self, path: FS_PATH) -> "FileSystem.BasicStat[FS_PATH]":
        pass

    @abc.abstractmethod
    def read_chunks(
        self, path: FS_PATH, offset: int = 0
    ) -> AsyncContextManager[AsyncIterator[bytes]]:
        pass

    async def read(self, path: FS_PATH) -> bytes:
        data = b""
        async with self.read_chunks(path) as chunks:
            async for chunk in chunks:
                data += chunk
        return data

    @abc.abstractmethod
    async def write_chunks(
        self,
        path: FS_PATH,
        body: AsyncIterator[bytes],
        offset: int = 0,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        pass

    @abc.abstractmethod
    async def rm(self, path: FS_PATH) -> None:
        pass

    @abc.abstractmethod
    def iter_dir(self, path: FS_PATH) -> AsyncContextManager[AsyncIterator[FS_PATH]]:
        pass

    @abc.abstractmethod
    async def mkdir(self, dst: FS_PATH) -> None:
        pass

    @abc.abstractmethod
    async def rmdir(self, path: FS_PATH) -> None:
        pass

    @abc.abstractmethod
    def to_url(self, path: FS_PATH) -> URL:
        pass

    @abc.abstractmethod
    async def get_time_diff_to_local(self) -> tuple[float, float]:
        # Returns possible interval (min_diff, max_diff)
        pass

    @abc.abstractmethod
    def parent(self, path: FS_PATH) -> FS_PATH:
        pass

    @abc.abstractmethod
    def name(self, path: FS_PATH) -> str:
        pass

    @abc.abstractmethod
    def child(self, path: FS_PATH, child: str) -> FS_PATH:
        pass


class LocalFS(FileSystem[Path]):
    fs_name = "Local"
    supports_offset_read = True
    supports_offset_write = True

    def __init__(self) -> None:
        self._file_sem = asyncio.BoundedSemaphore(MAX_OPEN_FILES)

    async def exists(self, path: Path) -> bool:
        return path.exists()

    async def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    async def is_file(self, path: Path) -> bool:
        return path.is_file()

    async def stat(self, path: Path) -> "FileSystem.BasicStat[Path]":
        stat = path.stat()
        return FileSystem.BasicStat(
            name=path.name,
            path=path,
            modification_time=stat.st_mtime,
            size=stat.st_size,
        )

    @asynccontextmanager
    async def read_chunks(
        self, path: Path, offset: int = 0
    ) -> AsyncIterator[AsyncIterator[bytes]]:
        loop = asyncio.get_event_loop()
        async with self._file_sem:

            async def _gen() -> AsyncIterator[bytes]:
                with path.open("rb") as stream:
                    stream.seek(offset)
                    chunk = await loop.run_in_executor(None, stream.read, READ_SIZE)
                    while chunk:
                        yield chunk
                        chunk = await loop.run_in_executor(None, stream.read, READ_SIZE)

            gen = _gen()
            try:
                yield gen
            finally:
                await gen.aclose()  # type: ignore

    async def write_chunks(
        self,
        path: Path,
        body: AsyncIterator[bytes],
        offset: int = 0,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        loop = asyncio.get_event_loop()
        with path.open("rb+" if offset else "wb") as stream:
            if offset:
                stream.seek(offset)
            async for chunk in body:
                await loop.run_in_executor(None, stream.write, chunk)
                if progress:
                    await progress(len(chunk))

    @asyncgeneratorcontextmanager
    async def iter_dir(self, path: Path) -> AsyncIterator[Path]:
        loop = asyncio.get_event_loop()
        async with self._file_sem:
            for item in await loop.run_in_executor(None, lambda: list(path.iterdir())):
                yield item

    async def mkdir(self, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)

    def to_url(self, path: Path) -> URL:
        return URL(path.as_uri())

    async def get_time_diff_to_local(self) -> tuple[float, float]:
        return 0, 0

    def parent(self, path: Path) -> Path:
        return path.parent

    def name(self, path: Path) -> str:
        return path.name

    def child(self, path: Path, child: str) -> Path:
        return path / child

    async def rm(self, path: Path) -> None:
        path.unlink()

    async def rmdir(self, path: Path) -> None:
        path.rmdir()


async def rm(
    fs: FileSystem[FS_PATH],
    path: FS_PATH,
    recursive: bool,
    progress: AbstractDeleteProgress | None = None,
) -> None:
    if not await fs.exists(path):
        raise FileNotFoundError(errno.ENOENT, "No such file or directory", str(path))
    if not recursive and await fs.is_dir(path):
        raise IsADirectoryError(
            errno.EISDIR, "Is a directory, use recursive remove", str(path)
        )

    async_progress: _AsyncAbstractDeleteProgress
    queue, async_progress = queue_calls(progress)

    async def _rm_file(file_path: FS_PATH) -> None:
        await fs.rm(file_path)
        await async_progress.delete(
            StorageProgressDelete(uri=fs.to_url(file_path), is_dir=False)
        )

    async def _rm_dir(dir_path: FS_PATH) -> None:
        tasks = []
        async with fs.iter_dir(dir_path) as dir_it:
            async for sub_path in dir_it:
                if await fs.is_dir(sub_path):
                    tasks.append(_rm_dir(sub_path))
                elif await fs.is_file(sub_path):
                    tasks.append(_rm_file(sub_path))
                else:
                    raise ValueError(
                        f"Cannot delete {sub_path}, not regular file/directory"
                    )
        await run_concurrently(tasks)
        await fs.rmdir(dir_path)
        await async_progress.delete(
            StorageProgressDelete(uri=fs.to_url(dir_path), is_dir=True)
        )

    async def _rm() -> None:
        if recursive:
            await _rm_dir(dir_path=path)
        else:
            await _rm_file(file_path=path)

    await run_progress(queue, _rm())


S_PATH = TypeVar("S_PATH")
D_PATH = TypeVar("D_PATH")


class FileTransferer(Generic[S_PATH, D_PATH]):
    def __init__(self, src_fs: FileSystem[S_PATH], dst_fs: FileSystem[D_PATH]) -> None:
        self.src_fs = src_fs
        self.dst_fs = dst_fs

    def _check_continue_possible(self, continue_: bool) -> None:
        if not continue_:
            return
        if (
            not self.src_fs.supports_offset_read
            or not self.dst_fs.supports_offset_write
        ):
            raise ValueError(
                f"Continuation is not supported when copying "
                f"from {self.src_fs.fs_name} to {self.dst_fs.fs_name}"
            )

    async def _check_transfer(
        self, src: S_PATH, dst: D_PATH, update: bool, continue_: bool
    ) -> int | None:
        src_stat = await self.src_fs.stat(src)
        dst_stat = await self.dst_fs.stat(dst)

        if src_stat.modification_time is None or dst_stat.modification_time is None:
            return 0  # Cannot check, re-transfer required
        src_diff_min, _ = await self.src_fs.get_time_diff_to_local()
        _, dst_diff_max = await self.dst_fs.get_time_diff_to_local()
        time_diff = (dst_stat.modification_time - dst_diff_max) - (
            src_stat.modification_time - src_diff_min
        )

        # Add 1 because modification_time can been truncated
        # and can be up to 1 second less than the actual value.
        if time_diff < TIME_THRESHOLD + 1.0:
            # Source is likely newer.
            return 0
        # Destination is definitely newer.
        if update:
            return None
        if continue_:
            if src_stat.size == dst_stat.size:  # complete
                return None
            if dst_stat.size < src_stat.size:  # partial
                return dst_stat.size
        return 0

    async def transfer_file(
        self,
        src: S_PATH,
        dst: D_PATH,
        *,
        continue_: bool = False,
        update: bool = False,
        progress: AbstractFileProgress | None = None,
    ) -> None:
        if not await self.src_fs.exists(src):
            raise FileNotFoundError(errno.ENOENT, "No such file", str(src))
        if await self.src_fs.is_dir(src):
            raise IsADirectoryError(
                errno.EISDIR, "Is a directory, use recursive copy", str(src)
            )
        self._check_continue_possible(continue_=continue_)

        if await self.dst_fs.exists(dst):
            if await self.dst_fs.is_dir(dst):
                raise IsADirectoryError(errno.EISDIR, "Is a directory", dst)
            offset = await self._check_transfer(
                src, dst, continue_=continue_, update=update
            )
        else:
            offset = 0
        if offset is None:
            return

        async_progress: _AsyncAbstractFileProgress
        queue, async_progress = queue_calls(progress)
        await run_progress(
            queue, self._transfer_file(src, dst, offset=offset, progress=async_progress)
        )

    async def _transfer_file(
        self,
        src: S_PATH,
        dst: D_PATH,
        *,
        offset: int = 0,
        progress: _AsyncAbstractFileProgress,
    ) -> None:
        src_url = self.src_fs.to_url(src)
        dst_url = self.dst_fs.to_url(dst)
        size = (await self.src_fs.stat(src)).size
        async with self.src_fs.read_chunks(src, offset) as chunks:
            await progress.start(StorageProgressStart(src_url, dst_url, size))
            pos = offset

            async def _progress(bytes_sent: int) -> None:
                nonlocal pos
                pos += bytes_sent
                await progress.step(StorageProgressStep(src_url, dst_url, pos, size))

            await self.dst_fs.write_chunks(dst, chunks, offset, _progress)
            await progress.complete(StorageProgressComplete(src_url, dst_url, size))

    async def transfer_dir(
        self,
        src: S_PATH,
        dst: D_PATH,
        *,
        continue_: bool = False,
        update: bool = False,
        filter: AsyncFilterFunc | None = None,
        ignore_file_names: AbstractSet[str] = frozenset(),
        progress: AbstractRecursiveFileProgress | None = None,
    ) -> None:
        if not await self.src_fs.exists(src):
            raise FileNotFoundError(errno.ENOENT, "No such file", str(src))
        if not await self.src_fs.is_dir(src):
            raise NotADirectoryError(errno.ENOTDIR, "Not a directory", str(src))
        self._check_continue_possible(continue_=continue_)

        if filter is None:
            filter = _always
        if ignore_file_names:
            filter = await load_parent_ignore_files(
                filter, ignore_file_names, self.src_fs, src
            )

        async_progress: _AsyncAbstractRecursiveFileProgress
        queue, async_progress = queue_calls(progress)
        await run_progress(
            queue,
            self._transfer_dir(
                src,
                dst,
                "",
                continue_=continue_,
                update=update,
                filter=filter,
                ignore_file_names=ignore_file_names,
                progress=async_progress,
            ),
        )

    async def _transfer_dir(
        self,
        src: S_PATH,
        dst: D_PATH,
        rel_path: str,
        *,
        continue_: bool,
        update: bool,
        filter: AsyncFilterFunc,
        ignore_file_names: AbstractSet[str],
        progress: _AsyncAbstractRecursiveFileProgress,
    ) -> None:
        src_url = self.src_fs.to_url(src)
        dst_url = self.dst_fs.to_url(dst)

        dst_files = {}
        if update or continue_:
            async with self.dst_fs.iter_dir(dst) as it:
                dst_files = {self.dst_fs.name(entry): entry async for entry in it}

        if await self.dst_fs.exists(dst):
            if not await self.dst_fs.is_dir(dst):
                raise NotADirectoryError(errno.ENOTDIR, "Not a directory", dst)
        else:
            await self.dst_fs.mkdir(dst)

        await progress.enter(StorageProgressEnterDir(src_url, dst_url))

        async with self.src_fs.iter_dir(src) as src_files_it:
            src_files = [entry async for entry in src_files_it]

        if ignore_file_names:
            for child in src_files:
                name = self.src_fs.name(child)
                if name in ignore_file_names and await self.src_fs.is_file(child):
                    logger.debug(f"Load ignore file {rel_path}{name}")
                    file_filter = FileFilter(filter)
                    data = await self.src_fs.read(child)
                    file_filter.read_from_buffer(data, prefix=rel_path)
                    filter = file_filter.match
        tasks = []
        for child in src_files:
            name = self.src_fs.name(child)
            child_rel_path = f"{rel_path}{name}"
            if await self.src_fs.is_dir(child):
                child_rel_path += "/"
            if not await filter(child_rel_path):
                logger.debug(f"Skip {child_rel_path}")
                continue
            if await self.src_fs.is_file(child):
                offset: int | None = 0
                if (update or continue_) and name in dst_files:
                    offset = await self._check_transfer(
                        child, dst_files[name], update=update, continue_=continue_
                    )
                    if offset is None:
                        continue
                assert offset is not None
                tasks.append(
                    self._transfer_file(
                        child,
                        self.dst_fs.child(dst, name),
                        offset=offset,
                        progress=progress,
                    )
                )
            elif await self.src_fs.is_dir(child):
                tasks.append(
                    self._transfer_dir(
                        child,
                        self.dst_fs.child(dst, name),
                        child_rel_path,
                        continue_=continue_,
                        update=update,
                        filter=filter,
                        ignore_file_names=ignore_file_names,
                        progress=progress,
                    )
                )
            else:
                await progress.fail(
                    StorageProgressFail(
                        src_url / name,
                        dst_url / name,
                        f"Cannot transfer {child}, not regular file/directory",
                    )
                )
        await run_concurrently(tasks)
        await progress.leave(StorageProgressLeaveDir(src_url, dst_url))


async def load_parent_ignore_files(
    filter: AsyncFilterFunc,
    ignore_file_names: AbstractSet[str],
    fs: FileSystem[FS_PATH],
    path: FS_PATH,
    rel_path: str = "",
) -> AsyncFilterFunc:
    if path == fs.parent(path):
        return filter
    rel_path = f"{fs.name(path)}/{rel_path}"
    path = fs.parent(path)
    filter = await load_parent_ignore_files(
        filter, ignore_file_names, fs, path, rel_path
    )
    for name in ignore_file_names:
        config_path = fs.child(path, name)
        if await fs.exists(config_path):
            logger.debug(f"Load ignore file {str(config_path)!r}")
            file_filter = FileFilter(filter)
            data = await fs.read(config_path)
            file_filter.read_from_buffer(data, "", rel_path)
            filter = file_filter.match
    return filter
