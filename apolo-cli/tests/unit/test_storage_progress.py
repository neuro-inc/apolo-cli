import sys
from collections.abc import Callable, Iterator
from itertools import product
from pathlib import Path
from typing import Any

import pytest
from yarl import URL

from apolo_sdk import (
    StorageProgressComplete,
    StorageProgressDelete,
    StorageProgressEnterDir,
    StorageProgressFail,
    StorageProgressLeaveDir,
    StorageProgressStart,
    StorageProgressStep,
)

from apolo_cli.formatters.storage import (
    DeleteProgress,
    StreamProgress,
    TTYProgress,
    create_storage_progress,
    format_url,
)
from apolo_cli.root import Root
from apolo_cli.utils import Command, Context

from tests.unit.conftest import NewConsole


class TimeCtl:
    def __init__(self) -> None:
        self._current: float = 0

    def tick(self, delta: float = 1.0) -> None:
        self._current += delta

    def get_time(self) -> float:
        return self._current


@pytest.fixture()
def time_ctl() -> TimeCtl:
    return TimeCtl()


def test_format_url_storage(root: Root) -> None:
    u = URL("storage://asvetlov/folder")
    assert format_url(root, u) == "storage://asvetlov/folder"


def test_format_url_file(root: Root) -> None:
    u = URL("file:///asvetlov/folder")
    if sys.platform == "win32":
        expected = "\\asvetlov\\folder"
    else:
        expected = "/asvetlov/folder"
    assert format_url(root, u) == expected


_MakeRoot = Callable[[bool, bool, bool], Root]


@pytest.fixture
def make_root(new_console: NewConsole, nmrc_path: Path) -> Iterator[_MakeRoot]:
    root = None

    async def cmd() -> None:
        pass

    def make(color: bool, tty: bool, verbose: bool) -> Root:
        nonlocal root
        root = Root(
            color,
            tty,
            True,
            60,
            config_path=nmrc_path,
            verbosity=int(verbose),
            trace=False,
            trace_hide_token=True,
            force_trace_all=False,
            command_path="",
            command_params=[],
            skip_gmp_stats=True,
            show_traceback=False,
            iso_datetime_format=False,
            ctx=Context(Command(cmd, name="")),
        )
        root.console = new_console(tty=tty, color=color)
        root.err_console = new_console(tty=tty, color=color)
        root.run(root.init_client())
        return root

    yield make
    if root is not None:
        root.close()


def test_progress_factory_none(make_root: _MakeRoot) -> None:
    progress = create_storage_progress(make_root(False, False, False), False)
    assert isinstance(progress, StreamProgress)
    progress.end()


def test_progress_factory_verbose(make_root: _MakeRoot) -> None:
    progress = create_storage_progress(make_root(False, False, False), False)
    assert isinstance(progress, StreamProgress)
    progress.end()


def test_progress_factory_percent(make_root: _MakeRoot) -> None:
    progress = create_storage_progress(make_root(False, False, False), True)
    assert isinstance(progress, TTYProgress)
    progress.end()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows does not supports UNIX-like permissions",
)
@pytest.mark.parametrize(
    "color,tty,verbose,show_progress",
    product((False, True), repeat=4),
)
def test_progress(
    color: bool,
    tty: bool,
    verbose: bool,
    show_progress: bool,
    make_root: _MakeRoot,
    rich_cmp: Any,
    time_ctl: TimeCtl,
) -> None:
    root = make_root(color, tty, verbose)
    report = create_storage_progress(
        root, show_progress, get_time=time_ctl.get_time, auto_refresh=False
    )
    src = URL("file:///abc")
    dst = URL("storage:xyz")

    with report.begin(src, dst):
        rich_cmp(root.console, index=0)

        time_ctl.tick()
        report.enter(StorageProgressEnterDir(src, dst))
        rich_cmp(root.console, index=1)

        time_ctl.tick()
        report.start(StorageProgressStart(src, dst, 600))
        rich_cmp(root.console, index=2)

        time_ctl.tick()
        report.step(StorageProgressStep(src, dst, 300, 600))
        rich_cmp(root.console, index=3)

        time_ctl.tick()
        report.step(StorageProgressStep(src, dst, 400, 600))
        rich_cmp(root.console, index=4)

        time_ctl.tick()
        report.complete(StorageProgressComplete(src, dst, 600))
        rich_cmp(root.console, index=5)

        time_ctl.tick()
        report.leave(StorageProgressLeaveDir(src, dst))
        rich_cmp(root.console, index=6)
    rich_cmp(root.console, index=7)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows does not supports UNIX-like permissions",
)
@pytest.mark.parametrize(
    "color,tty,verbose,show_progress",
    product((False, True), repeat=4),
)
def test_fail(
    color: bool,
    tty: bool,
    verbose: bool,
    show_progress: bool,
    rich_cmp: Any,
    make_root: _MakeRoot,
    time_ctl: TimeCtl,
) -> None:
    root = make_root(color, tty, verbose)
    report = create_storage_progress(
        root, show_progress, get_time=time_ctl.get_time, auto_refresh=False
    )
    src = URL("file:///abc")
    dst = URL("storage:xyz")
    with report.begin(src, dst):
        rich_cmp(root.console, index=0)

        report.fail(StorageProgressFail(src, dst, "error"))
        rich_cmp(root.err_console, index=1)
    rich_cmp(root.console, index=2)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows does not supports UNIX-like permissions",
)
@pytest.mark.parametrize(
    "color,tty,verbose,show_progress",
    product((False, True), repeat=4),
)
def test_nested(
    color: bool,
    tty: bool,
    verbose: bool,
    show_progress: bool,
    rich_cmp: Any,
    make_root: _MakeRoot,
    time_ctl: TimeCtl,
) -> None:
    root = make_root(color, tty, verbose)
    report = create_storage_progress(
        root, show_progress, get_time=time_ctl.get_time, auto_refresh=False
    )
    src = URL("file:///abc")
    dst = URL("storage:xyz")
    src_f = URL("file:///abc/file.txt")
    dst_f = URL("storage:xyz/file.txt")
    src2 = URL("file:///abc/cde")
    dst2 = URL("storage:xyz/cde")
    src2_f = URL("file:///abc/cde/file.txt")
    dst2_f = URL("storage:xyz/cde/file.txt")

    with report.begin(src, dst):
        rich_cmp(root.console, index=0)

        report.enter(StorageProgressEnterDir(src, dst))
        rich_cmp(root.console, index=1)

        time_ctl.tick()
        report.start(StorageProgressStart(src_f, dst_f, 600))
        rich_cmp(root.console, index=2)

        time_ctl.tick()
        report.step(StorageProgressStep(src_f, dst_f, 300, 600))
        rich_cmp(root.console, index=3)

        time_ctl.tick()
        report.step(StorageProgressStep(src_f, dst_f, 400, 600))
        rich_cmp(root.console, index=4)

        time_ctl.tick()
        report.complete(StorageProgressComplete(src_f, dst_f, 600))
        rich_cmp(root.console, index=5)

        time_ctl.tick()
        report.enter(StorageProgressEnterDir(src2, dst2))
        rich_cmp(root.console, index=6)

        time_ctl.tick()
        report.start(StorageProgressStart(src2_f, dst2_f, 800))
        rich_cmp(root.console, index=7)

        time_ctl.tick()
        report.step(StorageProgressStep(src2_f, dst2_f, 300, 800))
        rich_cmp(root.console, index=8)

        time_ctl.tick()
        report.complete(StorageProgressComplete(src2_f, dst_f, 800))
        rich_cmp(root.console, index=9)

        time_ctl.tick()
        report.leave(StorageProgressLeaveDir(src2, dst2))
        rich_cmp(root.console, index=10)

        time_ctl.tick()
        report.leave(StorageProgressLeaveDir(src, dst))
        rich_cmp(root.console, index=11)
    rich_cmp(root.console, index=12)


@pytest.mark.parametrize(
    "color,tty,verbose",
    product((False, True), repeat=3),
)
def test_delete_progress(
    color: bool,
    tty: bool,
    verbose: bool,
    rich_cmp: Any,
    make_root: _MakeRoot,
    time_ctl: TimeCtl,
) -> None:
    root = make_root(color, tty, verbose)
    report = DeleteProgress(root)
    url_file = URL("storage:/abc/foo")
    url_dir = URL("storage:/abc")

    report.delete(StorageProgressDelete(url_file, is_dir=False))
    rich_cmp(root.console, index=0)

    report.delete(StorageProgressDelete(url_dir, is_dir=True))
    rich_cmp(root.console, index=1)
