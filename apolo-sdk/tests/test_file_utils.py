import errno
import os
import random
import secrets
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from yarl import URL

from apolo_sdk import (
    AbstractRecursiveFileProgress,
    StorageProgressComplete,
    StorageProgressEnterDir,
    StorageProgressFail,
    StorageProgressLeaveDir,
    StorageProgressStart,
    StorageProgressStep,
)
from apolo_sdk._file_utils import READ_SIZE, FileTransferer, LocalFS, rm


@pytest.fixture()
def src_dir(tmp_path_factory: Any) -> Path:
    return tmp_path_factory.mktemp("src_dir")


@pytest.fixture()
def dst_dir(tmp_path_factory: Any) -> Path:
    return tmp_path_factory.mktemp("dst_dir")


@pytest.fixture()
def transferer() -> FileTransferer[Path, Path]:
    return FileTransferer(LocalFS(), LocalFS())


async def test_transfer_file(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    (src_dir / "test_file").write_bytes(b"testing")
    await transferer.transfer_file(src_dir / "test_file", dst_dir / "test_file")
    res = (dst_dir / "test_file").read_bytes()
    assert res == b"testing"


async def test_transfer_file_source_not_exists(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    with pytest.raises(FileNotFoundError) as e:
        await transferer.transfer_file(src_dir / "test_file", dst_dir / "test_file")
    assert e.value.args[0] == errno.ENOENT


async def test_transfer_file_source_is_dir(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    (src_dir / "test_file").mkdir()
    with pytest.raises(IsADirectoryError) as e:
        await transferer.transfer_file(src_dir / "test_file", dst_dir / "test_file")
    assert e.value.args[0] == errno.EISDIR


async def test_transfer_file_dest_is_dir(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    (src_dir / "test_file").write_bytes(b"testing")
    (dst_dir / "test_file").mkdir()
    with pytest.raises(IsADirectoryError) as e:
        await transferer.transfer_file(src_dir / "test_file", dst_dir / "test_file")
    assert e.value.args[0] == errno.EISDIR


async def test_transfer_file_progress(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    size = 3 * READ_SIZE
    (src_dir / "test_file").write_bytes(b"0" * size)
    progress = mock.Mock()
    await transferer.transfer_file(
        src_dir / "test_file", dst_dir / "test_file", progress=progress
    )
    src_url = URL((src_dir / "test_file").as_uri())
    dst_url = URL((dst_dir / "test_file").as_uri())
    progress.start.assert_called_once_with(StorageProgressStart(src_url, dst_url, size))
    assert list(progress.step.call_args_list) == [
        ((StorageProgressStep(src_url, dst_url, READ_SIZE, size),),),
        ((StorageProgressStep(src_url, dst_url, 2 * READ_SIZE, size),),),
        ((StorageProgressStep(src_url, dst_url, 3 * READ_SIZE, size),),),
    ]
    progress.complete.assert_called_once_with(
        StorageProgressComplete(src_url, dst_url, size)
    )


async def test_transfer_file_update_dst_newer(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)

    (src_dir / "test_file").write_bytes(b"testing")
    (dst_dir / "test_file").write_bytes(b"newer data")
    os.utime(src_dir / "test_file", (hour_ago.timestamp(), hour_ago.timestamp()))
    os.utime(dst_dir / "test_file", (now.timestamp(), now.timestamp()))
    await transferer.transfer_file(
        src_dir / "test_file", dst_dir / "test_file", update=True
    )
    res = (dst_dir / "test_file").read_bytes()
    assert res == b"newer data"


async def test_transfer_file_update_src_newer(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)

    (src_dir / "test_file").write_bytes(b"newer data")
    (dst_dir / "test_file").write_bytes(b"tessting")
    os.utime(src_dir / "test_file", (now.timestamp(), now.timestamp()))
    os.utime(dst_dir / "test_file", (hour_ago.timestamp(), hour_ago.timestamp()))
    await transferer.transfer_file(
        src_dir / "test_file", dst_dir / "test_file", update=True
    )
    res = (dst_dir / "test_file").read_bytes()
    assert res == b"newer data"


async def test_transfer_file_continue_src_newer(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)

    (src_dir / "test_file").write_bytes(b"newer data")
    (dst_dir / "test_file").write_bytes(b"testing")
    os.utime(src_dir / "test_file", (now.timestamp(), now.timestamp()))
    os.utime(dst_dir / "test_file", (hour_ago.timestamp(), hour_ago.timestamp()))
    await transferer.transfer_file(
        src_dir / "test_file", dst_dir / "test_file", continue_=True
    )
    res = (dst_dir / "test_file").read_bytes()
    assert res == b"newer data"


async def test_transfer_file_continue_dst_newer(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)

    (src_dir / "test_file").write_bytes(b"testing   additional data")
    (dst_dir / "test_file").write_bytes(b"only test ")
    os.utime(src_dir / "test_file", (hour_ago.timestamp(), hour_ago.timestamp()))
    os.utime(dst_dir / "test_file", (now.timestamp(), now.timestamp()))
    await transferer.transfer_file(
        src_dir / "test_file", dst_dir / "test_file", continue_=True
    )
    res = (dst_dir / "test_file").read_bytes()
    assert res == b"only test additional data"


async def gen_file_tree(path: Path, depths: int = 2) -> None:
    if depths > 0:
        for _ in range(10):
            dir_name = secrets.token_hex(10)
            (path / dir_name).mkdir()
            await gen_file_tree(path / dir_name, depths=depths - 1)
    for _ in range(10):
        file_name = secrets.token_hex(10)
        data = bytearray(random.getrandbits(8) for _ in range(1024))
        (path / file_name).write_bytes(data)


async def cmp_dirs(path1: Path, path2: Path) -> bool:
    childs1 = {path.name for path in path1.iterdir()}
    childs2 = {path.name for path in path2.iterdir()}
    if childs1 != childs2:
        return False
    same = True
    for child in childs1:
        if (path1 / child).is_file() and (path2 / child).is_file():
            same = same and (path1 / child).read_bytes() == (path2 / child).read_bytes()
        elif (path1 / child).is_dir() and (path2 / child).is_dir():
            same = same and await cmp_dirs(path1 / child, path2 / child)
        else:
            same = False
    return same


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="pytest_asyncio 0.24 fails with "
    "'got Future <Future pending> attached to a different loop'",
)
async def test_transfer_dir(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    src = src_dir / "sub_dir"
    src.mkdir()
    await gen_file_tree(src)
    await transferer.transfer_dir(src, dst_dir / "sub_dir")
    assert await cmp_dirs(src, dst_dir / "sub_dir")


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="pytest_asyncio 0.24 fails with "
    "'got Future <Future pending> attached to a different loop'",
)
async def test_transfer_dir_dest_exists(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    src = src_dir / "sub_dir"
    src.mkdir()
    dst = dst_dir / "sub_dir"
    dst.mkdir()
    await gen_file_tree(src, depths=1)
    await transferer.transfer_dir(src, dst)
    assert await cmp_dirs(src, dst)


async def test_transfer_dir_source_not_exists(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    with pytest.raises(FileNotFoundError) as e:
        await transferer.transfer_file(src_dir / "sub_dir", dst_dir / "sub_dir")
    assert e.value.args[0] == errno.ENOENT


async def test_transfer_dir_source_not_dir(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    (src_dir / "sub_dir").write_bytes(b"bbb")
    with pytest.raises(NotADirectoryError) as e:
        await transferer.transfer_dir(src_dir / "sub_dir", dst_dir / "sub_dir")
    assert e.value.args[0] == errno.ENOTDIR


async def test_transfer_dir_dest_not_dir(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    (src_dir / "sub_dir").mkdir()
    (dst_dir / "sub_dir").write_bytes(b"bbb")
    with pytest.raises(NotADirectoryError) as e:
        await transferer.transfer_dir(src_dir / "sub_dir", dst_dir / "sub_dir")
    assert e.value.args[0] == errno.ENOTDIR


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="pytest_asyncio 0.24 fails with "
    "'got Future <Future pending> attached to a different loop'",
)
async def test_transfer_dir_progress(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    src = src_dir / "sub_dir"
    src.mkdir()
    await gen_file_tree(src, depths=1)

    class MockProgress(AbstractRecursiveFileProgress):
        def __init__(self) -> None:
            self.entered_dirs: list[StorageProgressEnterDir] = []
            self.left_dirs: list[StorageProgressLeaveDir] = []
            self.failed_dirs: list[StorageProgressFail] = []
            self.started_files: list[StorageProgressStart] = []
            self.file_steps: list[StorageProgressStep] = []
            self.completed_files: list[StorageProgressComplete] = []

        def enter(self, data: StorageProgressEnterDir) -> None:
            self.entered_dirs.append(data)

        def leave(self, data: StorageProgressLeaveDir) -> None:
            self.left_dirs.append(data)

        def fail(self, data: StorageProgressFail) -> None:
            self.failed_dirs.append(data)

        def start(self, data: StorageProgressStart) -> None:
            self.started_files.append(data)

        def complete(self, data: StorageProgressComplete) -> None:
            self.completed_files.append(data)

        def step(self, data: StorageProgressStep) -> None:
            self.file_steps.append(data)

    progress = MockProgress()
    await transferer.transfer_dir(src, dst_dir / "sub_dir", progress=progress)

    def _check_progress(path: Path) -> None:
        for subpath in path.iterdir():
            src_url = URL(subpath.as_uri())
            dst_url = URL((dst_dir / "sub_dir" / subpath.relative_to(src)).as_uri())
            if subpath.is_file():
                size = subpath.stat().st_size
                assert any(
                    start
                    == StorageProgressStart(
                        src=src_url,
                        dst=dst_url,
                        size=size,
                    )
                    for start in progress.started_files
                )
                assert any(
                    step
                    == StorageProgressStep(
                        src=src_url,
                        dst=dst_url,
                        size=size,
                        current=size,
                    )
                    for step in progress.file_steps
                )
                assert any(
                    finish
                    == StorageProgressComplete(
                        src=src_url,
                        dst=dst_url,
                        size=size,
                    )
                    for finish in progress.completed_files
                )
            if subpath.is_dir():
                assert any(
                    enter
                    == StorageProgressEnterDir(
                        src=src_url,
                        dst=dst_url,
                    )
                    for enter in progress.entered_dirs
                )
                assert any(
                    leave
                    == StorageProgressLeaveDir(
                        src=src_url,
                        dst=dst_url,
                    )
                    for leave in progress.left_dirs
                )
                _check_progress(subpath)

    _check_progress(src)


async def test_transfer_dir_update(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)

    src = src_dir / "sub_dir"
    src.mkdir()
    dst = dst_dir / "sub_dir"
    dst.mkdir()
    (src / "src_newer").write_bytes(b"newer data")
    (dst / "src_newer").write_bytes(b"testing")
    os.utime(src / "src_newer", (now.timestamp(), now.timestamp()))
    os.utime(dst / "src_newer", (hour_ago.timestamp(), hour_ago.timestamp()))

    (src / "dst_newer").write_bytes(b"testing")
    (dst / "dst_newer").write_bytes(b"newer data")
    os.utime(src / "dst_newer", (now.timestamp(), hour_ago.timestamp()))
    os.utime(dst / "dst_newer", (hour_ago.timestamp(), now.timestamp()))

    await transferer.transfer_dir(src, dst, update=True)
    assert (dst / "src_newer").read_bytes() == b"newer data"
    assert (dst / "dst_newer").read_bytes() == b"newer data"


async def test_transfer_dir_continue(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)

    src = src_dir / "sub_dir"
    src.mkdir()
    dst = dst_dir / "sub_dir"
    dst.mkdir()
    (src / "src_newer").write_bytes(b"newer data")
    (dst / "src_newer").write_bytes(b"testing")
    os.utime(src / "src_newer", (now.timestamp(), now.timestamp()))
    os.utime(dst / "src_newer", (hour_ago.timestamp(), hour_ago.timestamp()))

    (src / "dst_newer").write_bytes(b"               more data")
    (dst / "dst_newer").write_bytes(b"already copied")
    os.utime(src / "dst_newer", (now.timestamp(), hour_ago.timestamp()))
    os.utime(dst / "dst_newer", (hour_ago.timestamp(), now.timestamp()))

    await transferer.transfer_dir(src, dst, continue_=True)
    assert (dst / "src_newer").read_bytes() == b"newer data"
    assert (dst / "dst_newer").read_bytes() == b"already copied more data"


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="pytest_asyncio 0.24 fails with "
    "'got Future <Future pending> attached to a different loop'",
)
async def test_transfer_dir_filter(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    src = src_dir / "sub_dir"
    src.mkdir()
    await gen_file_tree(src, depths=1)
    skip_dirs = []
    for path in src.iterdir():
        if path.is_dir():
            skip_dirs.append(path.name)
        if len(skip_dirs) == 3:
            break

    async def _filter(path: str) -> bool:
        return not any(skip_dir in path for skip_dir in skip_dirs)

    await transferer.transfer_dir(src, dst_dir / "sub_dir", filter=_filter)
    for skip_dir in skip_dirs:
        shutil.rmtree(src / skip_dir)
    assert await cmp_dirs(src, dst_dir / "sub_dir")


@pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="pytest_asyncio 0.24 fails with "
    "'got Future <Future pending> attached to a different loop'",
)
async def test_transfer_dir_ignore_file_names(
    transferer: FileTransferer[Path, Path], src_dir: Path, dst_dir: Path
) -> None:
    src = src_dir / "sub_dir"
    src.mkdir()
    await gen_file_tree(src, depths=1)
    skip_dirs = []
    for path in src.iterdir():
        if path.is_dir():
            skip_dirs.append(path.name)
        if len(skip_dirs) == 4:
            break
    (src_dir / ".cp_ignore").write_text("\n".join(skip_dirs[:2]))
    (src_dir / "sub_dir" / ".cp_ignore").write_text("\n".join(skip_dirs[2:]))

    await transferer.transfer_dir(
        src, dst_dir / "sub_dir", ignore_file_names={".cp_ignore"}
    )
    for skip_dir in skip_dirs:
        shutil.rmtree(src / skip_dir)
    assert await cmp_dirs(src, dst_dir / "sub_dir")


async def test_rm_file(
    src_dir: Path,
) -> None:
    file_path = src_dir / "file"
    file_path.touch()
    await rm(LocalFS(), file_path, recursive=False)
    assert not file_path.exists()


async def test_rm_dir(
    src_dir: Path,
) -> None:
    dir_path = src_dir / "sub_dir"
    dir_path.mkdir()
    await gen_file_tree(dir_path, depths=1)
    await rm(LocalFS(), dir_path, recursive=True)
    assert not dir_path.exists()


async def test_rm_not_exists(
    src_dir: Path,
) -> None:
    file_path = src_dir / "file"
    with pytest.raises(FileNotFoundError) as e:
        await rm(LocalFS(), file_path, recursive=False)
    assert e.value.args[0] == errno.ENOENT


async def test_rm_dir_not_recursive(
    src_dir: Path,
) -> None:
    dir_path = src_dir / "sub_dir"
    dir_path.mkdir()
    with pytest.raises(IsADirectoryError) as e:
        await rm(LocalFS(), dir_path, recursive=False)
    assert e.value.args[0] == errno.EISDIR
