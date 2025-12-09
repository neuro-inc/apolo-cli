import abc
import contextlib
import enum
import operator
import os
import sys
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from fnmatch import fnmatch
from time import monotonic
from types import TracebackType
from typing import Any

from rich.ansi import AnsiDecoder
from rich.columns import Columns
from rich.console import RenderableType
from rich.progress import (
    BarColumn,
    DownloadColumn,
    GetTimeCallable,
    Progress,
    TaskID,
    TextColumn,
    TransferSpeedColumn,
)
from rich.style import Style
from rich.table import Table
from rich.text import Text
from yarl import URL

from apolo_sdk import (
    AbstractDeleteProgress,
    AbstractRecursiveFileProgress,
    Action,
    DiskUsageInfo,
    FileStatus,
    FileStatusType,
    StorageProgressComplete,
    StorageProgressDelete,
    StorageProgressEnterDir,
    StorageProgressFail,
    StorageProgressLeaveDir,
    StorageProgressStart,
    StorageProgressStep,
)

from apolo_cli.root import Root
from apolo_cli.utils import format_size

RECENT_TIME_DELTA = 365 * 24 * 60 * 60 / 2
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def chunks(list: Sequence[Any], size: int) -> Sequence[Any]:
    result = []
    for i in range(0, len(list), size):
        result.append(list[i : i + size])
    return result


def transpose(columns: Sequence[Sequence[Any]]) -> Sequence[Sequence[Any]]:
    height = len(columns)
    width = len(columns[0])
    result: Sequence[list[Any]] = [[] for _ in range(width)]
    for i in range(width):
        for j in range(height):
            if i < len(columns[j]):
                result[i].append(columns[j][i])
    return result


class GnuIndicators(str, enum.Enum):
    LEFT = "lc"
    RIGHT = "rc"
    END = "ec"
    RESET = "rs"
    NORM = "no"
    FILE = "fi"
    DIR = "di"
    LINK = "ln"
    FIFO = "pi"
    SOCKET = "so"
    BLK = "bd"
    CHR = "cd"
    MISSING = "mi"
    ORPHAN = "or"
    EXEC = "ex"
    DOOR = "do"
    SETUID = "su"
    SETGID = "sg"
    STICKY = "st"
    OTHER_WRITABLE = "ow"
    STICKY_OTHER_WRITABLE = "tw"
    CAP = "ca"
    MULTI_HARD_LINK = "mh"
    CLR_TO_EOL = "cl"


class ParseState(enum.Enum):
    PS_START = enum.auto()
    PS_LEFT = enum.auto()
    PS_ESCAPED = enum.auto()
    PS_ESCAPED_END = enum.auto()
    PS_RIGHT = enum.auto()
    PS_OCTAL = enum.auto()
    PS_HEX = enum.auto()
    PS_CARRET = enum.auto()


class BasePainter(abc.ABC):
    @abc.abstractmethod
    def paint(self, label: str, type: FileStatusType) -> Text:  # pragma: no cover
        pass


class NonePainter(BasePainter):
    def paint(self, label: str, type: FileStatusType) -> Text:
        return Text(label)


class GnuPainter(BasePainter):
    def __init__(self, ls_colors: str):
        self._defaults()
        self._parse_ls_colors(ls_colors)

    def _defaults(self) -> None:
        self.color_indicator: dict[GnuIndicators, str] = {
            GnuIndicators.LEFT: "\033[",
            GnuIndicators.RIGHT: "m",
            GnuIndicators.END: "",
            GnuIndicators.RESET: "0",
            GnuIndicators.NORM: "",
            GnuIndicators.FILE: "",
            GnuIndicators.DIR: "01;34",
            GnuIndicators.LINK: "01;36",
            GnuIndicators.FIFO: "33",
            GnuIndicators.SOCKET: "01;35",
            GnuIndicators.BLK: "01;33",
            GnuIndicators.CHR: "01;33",
            GnuIndicators.MISSING: "",
            GnuIndicators.ORPHAN: "",
            GnuIndicators.EXEC: "01;32",
            GnuIndicators.DOOR: "01;35",
            GnuIndicators.SETUID: "37;41",
            GnuIndicators.SETGID: "30;43",
            GnuIndicators.STICKY: "37;44",
            GnuIndicators.OTHER_WRITABLE: "34;42",
            GnuIndicators.STICKY_OTHER_WRITABLE: "30;42",
            GnuIndicators.CAP: "30;41",
            GnuIndicators.MULTI_HARD_LINK: "",
            GnuIndicators.CLR_TO_EOL: "\033[K",
        }
        self.color_ext_type: dict[str, str] = {}

    def _parse_ls_colors(self, ls_colors: str) -> None:
        def process(left: str, right: str) -> None:
            try:
                self.color_indicator[GnuIndicators(left)] = right
            except ValueError:
                self.color_ext_type[left] = right

        pos = 0
        left = right = escaped = ""
        num = 0
        state = ParseState.PS_START
        stack: list[ParseState] = []
        while pos < len(ls_colors):
            char = ls_colors[pos]
            if state == ParseState.PS_START:
                if char == ":":  # ignore colon
                    pos += 1
                else:
                    left = ""
                    state = ParseState.PS_LEFT
            elif state == ParseState.PS_OCTAL:
                if char in ["0", "1", "2", "3", "4", "5", "6", "7"]:
                    num = num * 8 + ord(char) - ord("0")
                    if num > 7:
                        state = ParseState.PS_ESCAPED_END
                        escaped = chr(num)
                    pos += 1
                else:
                    state = ParseState.PS_ESCAPED_END
                    escaped = chr(num)
            elif state == ParseState.PS_HEX:
                if char in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                    num = num * 16 + ord(char) - ord("0")
                    if num > 15:
                        state = ParseState.PS_ESCAPED_END
                        escaped = chr(num)
                    pos += 1
                elif char.upper() in ["A", "B", "C", "D", "E", "F"]:
                    num = num * 16 + 10 + ord(char.upper()) - ord("A")
                    if num > 15:
                        state = ParseState.PS_ESCAPED_END
                        escaped = chr(num)
                    pos += 1
                else:
                    state = ParseState.PS_ESCAPED_END
                    escaped = chr(num)

            elif state == ParseState.PS_ESCAPED_END:
                stack.pop()
                state = stack.pop()
                if state == ParseState.PS_LEFT:
                    left += escaped
                else:
                    right += escaped
                escaped = ""
            elif state == ParseState.PS_ESCAPED:
                if char in ["0", "1", "2", "3", "4", "5", "6", "7"]:
                    stack.append(state)
                    state = ParseState.PS_OCTAL
                    num = 0
                elif char.upper() == "X":
                    stack.append(state)
                    state = ParseState.PS_HEX
                    num = 0
                    pos += 1

                elif char == "a":
                    escaped = "\a"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "b":
                    escaped = "\b"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "e":
                    escaped = chr(27)
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "f":
                    escaped = "\f"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "n":
                    escaped = "\n"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "r":
                    escaped = "\r"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "t":
                    escaped = "\t"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "v":
                    escaped = "\v"
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "?":
                    escaped = chr(127)
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == "_":
                    escaped = " "
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
                elif char == chr(0):  # pragma: no cover
                    raise OSError("Cannot parse coloring scheme")
                else:
                    escaped = char
                    stack.append(state)
                    state = ParseState.PS_ESCAPED_END
                    pos += 1
            elif state == ParseState.PS_CARRET:
                if "@" <= char <= "~":
                    escaped = chr(ord(char) & 0o37)
                elif char == "?":
                    escaped = chr(127)
                else:
                    raise OSError("Cannot parse coloring scheme")
                stack.append(state)
                state = ParseState.PS_ESCAPED_END
                pos += 1

            elif state == ParseState.PS_LEFT:
                if char == "\\":
                    stack.append(state)
                    state = ParseState.PS_ESCAPED
                    pos += 1
                    escaped = ""
                elif char == "=":
                    right = ""
                    state = ParseState.PS_RIGHT
                    pos += 1
                elif char == "^":
                    stack.append(state)
                    state = ParseState.PS_CARRET
                    pos += 1
                    escaped = ""
                else:
                    left += char
                    pos = pos + 1
            elif state == ParseState.PS_RIGHT:
                if char == "\\":
                    stack.append(state)
                    state = ParseState.PS_ESCAPED
                    pos += 1
                    escaped = ""
                elif char == ":":
                    if right:
                        process(left, right)
                    state = ParseState.PS_START
                    pos += 1
                elif char == "^":
                    stack.append(state)
                    state = ParseState.PS_CARRET
                    pos += 1
                    escaped = ""
                else:
                    right += char
                    pos += 1

        if state == ParseState.PS_CARRET:
            raise OSError("Cannot parse coloring scheme")
        if state in [ParseState.PS_HEX, ParseState.PS_OCTAL]:
            escaped = chr(num)
            state = stack.pop()
        if state == ParseState.PS_ESCAPED:
            stack.append(ParseState.PS_ESCAPED)
            state = ParseState.PS_ESCAPED_END
        if state == ParseState.PS_ESCAPED_END:
            stack.pop()
            state = stack.pop()
            if state == ParseState.PS_RIGHT:  # pragma no branch
                right += escaped
        if state == ParseState.PS_RIGHT and right:
            process(left, right)

    def paint(self, label: str, type: FileStatusType) -> Text:
        mapping = {
            FileStatusType.FILE: self.color_indicator[GnuIndicators.FILE],
            FileStatusType.DIRECTORY: self.color_indicator[GnuIndicators.DIR],
            FileStatusType.SYMLINK: self.color_indicator[GnuIndicators.LINK],
            FileStatusType.UNKNOWN: self.color_indicator[GnuIndicators.MISSING],
        }
        color = mapping[type]
        if not color:
            color = self.color_indicator[GnuIndicators.NORM]
        if type == FileStatusType.FILE:
            for pattern, value in self.color_ext_type.items():
                if fnmatch(label, pattern):
                    color = value
                    break
        if color:
            # If formatted text contains newlines for some reason,
            # painter should escape them
            return Text("\\n").join(
                AnsiDecoder().decode(
                    self.color_indicator[GnuIndicators.LEFT]
                    + color
                    + self.color_indicator[GnuIndicators.RIGHT]
                    + label
                    + self.color_indicator[GnuIndicators.LEFT]
                    + self.color_indicator[GnuIndicators.RESET]
                    + self.color_indicator[GnuIndicators.RIGHT]
                )
            )
        else:
            return Text(label)


class BSDAttributes(enum.Enum):
    DIRECTORY = 1
    LINK = 2
    SOCKET = 3
    PIPE = 4
    EXECUTABLE = 5
    BLOCK = 6
    CHARACTER = 7
    EXECUTABLE_SETUID = 8
    EXECUTABLE_SETGID = 9
    DIRECTORY_WRITABLE_OTHERS_WITH_STICKY = 10
    DIRECTORY_WRITABLE_OTHERS_WITHOUT_STICKY = 11


class BSDPainter(BasePainter):
    def __init__(self, lscolors: str):
        self._parse_lscolors(lscolors)

    def _parse_lscolors(self, lscolors: str) -> None:
        parts = chunks(lscolors, 2)
        self._colors: dict[BSDAttributes, str] = {}
        num = 0
        for attr in BSDAttributes:
            self._colors[attr] = parts[num]
            num += 1

    def paint(self, label: str, type: FileStatusType) -> Text:
        color = ""
        if type == FileStatusType.DIRECTORY:
            color = self._colors[BSDAttributes.DIRECTORY]
        if color:
            char_to_color = {
                "a": "black",
                "b": "red",
                "c": "green",
                "d": "brown",
                "e": "blue",
                "f": "magenta",
                "g": "cyan",
                "h": "white",
            }
            bold = None
            fg = bg = None
            if color[0].lower() in char_to_color.keys():
                fg = char_to_color[color[0].lower()]
                if color[0].isupper():
                    bold = True
            if color[1] in char_to_color.keys():
                bg = char_to_color[color[1]]
            if fg or bg or bold:
                return Text(
                    label,
                    style=Style(color=fg, bgcolor=bg, bold=bold),
                )
        return Text(label)


def get_painter(color: bool) -> BasePainter:
    if color:
        ls_colors = os.getenv("LS_COLORS")
        if ls_colors:
            return GnuPainter(ls_colors)
        lscolors = os.getenv("LSCOLORS")
        if lscolors:
            return BSDPainter(lscolors)
    return NonePainter()


class BaseFilesFormatter:
    @abc.abstractmethod
    def __call__(
        self, files: Sequence[FileStatus]
    ) -> RenderableType:  # pragma: no cover
        pass


class LongFilesFormatter(BaseFilesFormatter):
    permissions_mapping = {Action.MANAGE: "m", Action.WRITE: "w", Action.READ: "r"}

    file_types_mapping = {
        FileStatusType.FILE: "-",
        FileStatusType.DIRECTORY: "d",
        FileStatusType.SYMLINK: "l",
        FileStatusType.UNKNOWN: "?",
    }

    def __init__(self, human_readable: bool, color: bool):
        self.human_readable = human_readable
        self.painter = get_painter(color)

    def _columns_for_file(self, file: FileStatus) -> Sequence[RenderableType]:

        type = self.file_types_mapping[file.type]
        permission = self.permissions_mapping[file.permission]

        date = time.strftime(TIME_FORMAT, time.localtime(file.modification_time))

        if self.human_readable:
            size = format_size(file.size).rstrip("B")
        else:
            size = str(file.size)

        name = self.painter.paint(file.name, file.type)
        if file.target is not None:
            name += f" -> {file.target}"

        return [f"{type}{permission}", f"{size}", f"{date}", name]

    def __call__(self, files: Sequence[FileStatus]) -> RenderableType:
        table = Table.grid(padding=(0, 2))
        table.add_column()  # Type/Permissions
        table.add_column(justify="right")  # Size
        table.add_column()  # Date
        table.add_column()  # Filename

        for file in files:
            table.add_row(*self._columns_for_file(file))
        return table


class SimpleFilesFormatter(BaseFilesFormatter):
    def __init__(self, color: bool):
        self.painter = get_painter(color)

    def __call__(self, files: Sequence[FileStatus]) -> RenderableType:
        return Text("\n").join(
            self.painter.paint(file.name, file.type) for file in files
        )


class VerticalColumnsFilesFormatter(BaseFilesFormatter):
    def __init__(self, width: int, color: bool):
        self.width = width
        self.painter = get_painter(color)

    def __call__(self, files: Sequence[FileStatus]) -> RenderableType:
        if not files:
            return ""
        items = [self.painter.paint(file.name, file.type) for file in files]
        column_width = max(len(item) for item in items) + 1
        return Columns(
            [self.painter.paint(file.name, file.type) for file in files],
            align="left",
            column_first=True,
            width=column_width,
            padding=0,
        )


class FilesSorter(str, enum.Enum):
    NAME = "name"
    SIZE = "size"
    TIME = "time"

    def key(self) -> Any:
        field = None
        cls = type(self)
        if self == cls.NAME:
            field = "name"
        elif self == cls.SIZE:
            field = "size"
        elif self == cls.TIME:
            field = "modification_time"
        assert field
        return operator.attrgetter(field)


# progress indicator


class DeleteProgress(AbstractDeleteProgress):
    def __init__(self, root: Root) -> None:
        self._root = root
        self.painter = get_painter(root.color)

    def fmt_url(self, url: URL, type: FileStatusType) -> Text:
        return self.painter.paint(str(url), type)

    def delete(self, data: StorageProgressDelete) -> None:
        url_label = self.fmt_url(
            data.uri,
            FileStatusType.DIRECTORY if data.is_dir else FileStatusType.FILE,
        )
        self._root.print(f"Removed: {url_label}")


class StorageProgressContextManager:
    def __init__(self, progress: "BaseStorageProgress"):
        self._progress = progress

    def begin(self, src: URL, dst: URL) -> "BaseStorageProgress":
        self._progress.begin(src, dst)
        return self._progress

    def __enter__(self) -> "BaseStorageProgress":
        return self._progress

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._progress.end()


class BaseStorageProgress(AbstractRecursiveFileProgress, abc.ABC):
    def begin(
        self, src: URL, dst: URL
    ) -> StorageProgressContextManager:  # pragma: no cover
        return StorageProgressContextManager(self)

    def end(self) -> None:  # pragma: no cover
        pass


def create_storage_progress(
    root: Root,
    show_progress: bool,
    *,
    get_time: GetTimeCallable = time.monotonic,
    auto_refresh: bool = True,  # only disabled in test
) -> BaseStorageProgress:
    if show_progress:
        return TTYProgress(root, get_time=get_time, auto_refresh=auto_refresh)
    else:
        return StreamProgress(root)


def format_url(root: Root, url: URL) -> str:
    if url.scheme == "file":
        path = root.client.parse.uri_to_path(url)
        return str(path)
    else:
        return str(url)


class StreamProgress(BaseStorageProgress):
    def __init__(self, root: Root) -> None:
        self.painter = get_painter(root.color)
        self.verbose = root.verbosity > 0
        self._root = root

    def fmt_url(self, url: URL, type: FileStatusType) -> Text:
        label = format_url(self._root, url)
        return self.painter.paint(label, type)

    def begin(self, src: URL, dst: URL) -> StorageProgressContextManager:
        if self.verbose:
            src_label = self.fmt_url(src, FileStatusType.DIRECTORY)
            dst_label = self.fmt_url(dst, FileStatusType.DIRECTORY)
            self._root.print(f"Copy {src_label} -> {dst_label}")
        return super().begin(src, dst)

    def start(self, data: StorageProgressStart) -> None:
        pass

    def complete(self, data: StorageProgressComplete) -> None:
        if not self.verbose:
            return
        src = self.fmt_url(data.src, FileStatusType.FILE)
        dst = self.fmt_url(data.dst, FileStatusType.FILE)
        self._root.print(f"{src} -> {dst}")

    def step(self, data: StorageProgressStep) -> None:
        pass

    def enter(self, data: StorageProgressEnterDir) -> None:
        if not self.verbose:
            return
        src = self.fmt_url(data.src, FileStatusType.FILE)
        dst = self.fmt_url(data.dst, FileStatusType.FILE)
        self._root.print(f"{src} -> {dst}")

    def leave(self, data: StorageProgressLeaveDir) -> None:
        pass

    def fail(self, data: StorageProgressFail) -> None:
        src = self.fmt_url(data.src, FileStatusType.FILE)
        dst = self.fmt_url(data.dst, FileStatusType.FILE)
        self._root.print(
            Text.assemble(
                Text("Failure:", style="red"), f" {src} -> {dst} [{data.message}]"
            ),
            err=True,
        )


class TTYProgress(BaseStorageProgress):
    HEIGHT = 25
    FLUSH_INTERVAL = 0.2
    time_factory = staticmethod(monotonic)

    def __init__(
        self,
        root: Root,
        *,
        get_time: GetTimeCallable = time.monotonic,
        auto_refresh: bool = True,
    ) -> None:
        self.painter = get_painter(root.color)
        self._root = root
        self._mapping: dict[URL, TaskID] = {}
        self._progress = Progress(
            TextColumn("[progress.description]{task.fields[filename]}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=root.console,
            auto_refresh=auto_refresh,
            get_time=get_time,
        )
        self._progress.start()

    def _refresh(self) -> None:
        height = self._root.terminal_size[1]
        # If terminal is to small, we cannot show all tasks.
        # Moreover, scroll will be also broken, so the
        # only solution is just to hide some tasks.
        to_hide = len(self._progress.task_ids) - height + 2
        hidden = sum(1 for task in self._progress.tasks if not task.visible)
        for task in self._progress.tasks:
            if to_hide < hidden and not task.visible:
                self._progress.update(task.id, visible=True)
                hidden -= 1
            if to_hide > hidden and task.visible:
                self._progress.update(task.id, visible=False)
                hidden += 1
            if to_hide == hidden:
                break
        self._progress.refresh()

    def fmt_url(self, url: URL, type: FileStatusType) -> Text:
        return self.fmt_str(format_url(self._root, url), type)

    def fmt_str(self, label: str, type: FileStatusType) -> Text:
        return self.painter.paint(label, type)

    def begin(self, src: URL, dst: URL) -> StorageProgressContextManager:
        src_label = self.fmt_url(src, FileStatusType.DIRECTORY)
        dst_label = self.fmt_url(dst, FileStatusType.DIRECTORY)
        self._progress.log(Text.assemble("Copying ", src_label, " => ", dst_label))
        return super().begin(src, dst)

    def end(self) -> None:
        # Clean terminal if there is no files in progress
        self._progress.live.transient = not self._progress.task_ids
        self._progress.stop()

    def enter(self, data: StorageProgressEnterDir) -> None:
        fmt_src = self.fmt_url(data.src, FileStatusType.DIRECTORY)
        self._progress.log(Text.assemble("Starting copying directory ", fmt_src))

    def leave(self, data: StorageProgressLeaveDir) -> None:
        fmt_src = self.fmt_url(data.src, FileStatusType.DIRECTORY)
        self._progress.log(Text.assemble("Finished copying directory ", fmt_src))

    def start(self, data: StorageProgressStart) -> None:
        fmt_src = self.fmt_url(data.src, FileStatusType.FILE)
        fmt_name = self.fmt_str(data.src.name, FileStatusType.FILE)
        self._progress.log(Text.assemble("Copying: ", fmt_src))
        task_id = self._progress.add_task(
            description=data.src.name,
            total=data.size,
            filename=fmt_name,
        )
        self._mapping[data.src] = task_id
        self._refresh()

    def step(self, data: StorageProgressStep) -> None:
        task_id = self._mapping[data.src]
        self._progress.update(task_id, completed=data.current)
        self._refresh()

    def complete(self, data: StorageProgressComplete) -> None:
        fmt_src = self.fmt_url(data.src, FileStatusType.FILE)
        self._progress.log(Text.assemble("Copied: ", fmt_src))
        task_id = self._mapping[data.src]
        self._progress.remove_task(task_id)
        self._refresh()

    def fail(self, data: StorageProgressFail) -> None:
        src = self.fmt_str(str(data.src), FileStatusType.FILE)
        dst = self.fmt_str(str(data.dst), FileStatusType.FILE)
        self._root.print(
            Text.assemble(
                Text("Failure:", style="red"), f" {src} -> {dst} [{data.message}]"
            ),
            err=True,
        )


@dataclass(frozen=True)
class Tree:
    name: str
    size: int
    folders: Sequence["Tree"]
    files: Sequence[FileStatus]


class TreeFormatter:
    ANSI_DELIMS = ["├", "└", "─", "│"]
    SIMPLE_DELIMS = ["+", "+", "-", "|"]

    def __init__(
        self, *, color: bool, size: bool, human_readable: bool, sort: str
    ) -> None:
        self._ident: list[bool] = []
        self._numdirs = 0
        self._numfiles = 0
        self._painter = get_painter(color)
        if sys.platform != "win32":
            self._delims = self.ANSI_DELIMS
        else:
            self._delims = self.SIMPLE_DELIMS
        if human_readable:
            self._size_func = self._human_readable
        elif size:
            self._size_func = self._size
        else:
            self._size_func = self._none
        self._key = FilesSorter(sort).key()

    def __call__(self, tree: Tree) -> Text:
        ret = self.listdir(tree)
        ret.append(f"\n{self._numdirs} directories, {self._numfiles} files")
        return ret

    def listdir(self, tree: Tree) -> Text:
        ret = Text()
        items = sorted(tree.folders + tree.files, key=self._key)  # type: ignore
        ret.append(
            Text.assemble(
                self.pre(),
                self._size_func(tree.size),
                self._painter.paint(tree.name, FileStatusType.DIRECTORY),
                "\n",
            )
        )
        for num, item in enumerate(items):
            if isinstance(item, Tree):
                self._numdirs += 1
                with self.ident(num == len(items) - 1):
                    ret.append(self.listdir(item))
            else:
                self._numfiles += 1
                with self.ident(num == len(items) - 1):
                    ret.append(
                        Text.assemble(
                            self.pre(),
                            self._size_func(item.size),
                            self._painter.paint(item.name, FileStatusType.FILE),
                            "\n",
                        )
                    )
        return ret

    def pre(self) -> str:
        ret = []
        for last in self._ident[:-1]:
            if last:
                ret.append(" " * 4)
            else:
                ret.append(self._delims[3] + " " * 3)
        if self._ident:
            last = self._ident[-1]
            ret.append(self._delims[1] if last else self._delims[0])
            ret.append(self._delims[2] * 2)
            ret.append(" ")
        return "".join(ret)

    @contextlib.contextmanager
    def ident(self, last: bool) -> Iterator[None]:
        self._ident.append(last)
        try:
            yield
        finally:
            self._ident.pop()

    def _size(self, size: int) -> str:
        return f"[{size:>11}]  "

    def _human_readable(self, size: int) -> str:
        return f"[{format_size(size):>7}]  "

    def _none(self, size: int) -> str:
        return ""


class DiskUsageFormatter:
    def __call__(self, usage: DiskUsageInfo) -> Text:
        if usage.uri:
            ret = Text.from_markup(
                f"Disk usage for path [b]{usage.uri.path}[/] "
                f"in cluster [b]{usage.cluster_name}[/]:\n"
            )
        elif usage.org_name:
            ret = Text.from_markup(
                f"Disk usage for organization [b]{usage.org_name}[/] "
                f"in cluster [b]{usage.cluster_name}[/]:\n"
            )
        else:
            ret = Text.from_markup(
                f"Disk usage for cluster [b]{usage.cluster_name}[/]:\n"
            )
        ret.append(f"Total: {format_size(usage.total)}\n")
        ret.append(f"Used:  {format_size(usage.used)}\n")
        ret.append(f"Free:  {format_size(usage.free)}")
        return ret
