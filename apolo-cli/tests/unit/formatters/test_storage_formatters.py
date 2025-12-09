import time
from typing import Any

import pytest
from yarl import URL

from apolo_sdk import Action, DiskUsageInfo, FileStatus, FileStatusType

from apolo_cli.formatters.storage import (
    BaseFilesFormatter,
    BSDAttributes,
    BSDPainter,
    DiskUsageFormatter,
    FilesSorter,
    GnuIndicators,
    GnuPainter,
    LongFilesFormatter,
    NonePainter,
    SimpleFilesFormatter,
    VerticalColumnsFilesFormatter,
    get_painter,
)


class TestNonePainter:
    def test_simple(self, rich_cmp: Any) -> None:
        painter = NonePainter()
        file = FileStatus(
            "File1",
            2048,
            FileStatusType.FILE,
            int(time.mktime(time.strptime("2018-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            uri=URL("storage://default/user/File1"),
        )
        rich_cmp(painter.paint(file.name, file.type))


class TestGnuPainter:
    def test_color_parsing_simple(self) -> None:
        painter = GnuPainter("rs=1;0;1")
        assert painter.color_indicator[GnuIndicators.RESET] == "1;0;1"

        painter = GnuPainter(":rs=1;0;1")
        assert painter.color_indicator[GnuIndicators.RESET] == "1;0;1"

        painter = GnuPainter("rs=1;0;1:")
        assert painter.color_indicator[GnuIndicators.RESET] == "1;0;1"

        painter = GnuPainter("rs=1;0;1:fi=32;42")
        assert painter.color_indicator[GnuIndicators.RESET] == "1;0;1"
        assert painter.color_indicator[GnuIndicators.FILE] == "32;42"

        painter = GnuPainter("rs=1;0;1:fi")
        assert painter.color_indicator[GnuIndicators.RESET] == "1;0;1"
        assert painter.color_indicator[GnuIndicators.FILE] == ""

        painter = GnuPainter("rs=1;0;1:fi=")
        assert painter.color_indicator[GnuIndicators.RESET] == "1;0;1"
        assert painter.color_indicator[GnuIndicators.FILE] == ""

    @pytest.mark.parametrize(
        "escaped,result",
        [
            ("\\a", "\a"),
            ("\\b", "\b"),
            ("\\e", chr(27)),
            ("\\f", "\f"),
            ("\\n", "\n"),
            ("\\r", "\r"),
            ("\\t", "\t"),
            ("\\v", "\v"),
            ("\\?", chr(127)),
            ("\\_", " "),
            ("a\\n", "a\n"),
            ("a\\tb", "a\tb"),
            ("a\\t\\rb", "a\t\rb"),
            ("a\\=b", "a=b"),
        ],
    )
    def test_color_parsing_escaped_simple(self, escaped: str, result: str) -> None:
        painter = GnuPainter("rs=" + escaped)
        assert painter.color_indicator[GnuIndicators.RESET] == result

        painter = GnuPainter(escaped + "=1;2")
        assert painter.color_ext_type[result] == "1;2"

        painter = GnuPainter(escaped + "=" + escaped)
        assert painter.color_ext_type[result] == result

    @pytest.mark.parametrize(
        "escaped,result",
        [
            ("\\7", chr(7)),
            ("\\8", "8"),
            ("\\10", chr(8)),
            ("a\\2", "a" + chr(2)),
            ("a\\2b", "a" + chr(2) + "b"),
        ],
    )
    def test_color_parsing_escaped_octal(self, escaped: str, result: str) -> None:
        painter = GnuPainter("rs=" + escaped)
        assert painter.color_indicator[GnuIndicators.RESET] == result

        painter = GnuPainter(escaped + "=1;2")
        assert painter.color_ext_type[result] == "1;2"

        painter = GnuPainter(escaped + "=" + escaped)
        assert painter.color_ext_type[result] == result

    @pytest.mark.parametrize(
        "escaped,result",
        [
            ("\\x7", chr(0x7)),
            ("\\x8", chr(0x8)),
            ("\\x10", chr(0x10)),
            ("\\XaA", chr(0xAA)),
            ("a\\x222", "a" + chr(0x22) + "2"),
            ("a\\x2z", "a" + chr(0x2) + "z"),
        ],
    )
    def test_color_parsing_escaped_hex(self, escaped: str, result: str) -> None:
        painter = GnuPainter("rs=" + escaped)
        assert painter.color_indicator[GnuIndicators.RESET] == result

        painter = GnuPainter(escaped + "=1;2")
        assert painter.color_ext_type[result] == "1;2"

        painter = GnuPainter(escaped + "=" + escaped)
        assert painter.color_ext_type[result] == result

    @pytest.mark.parametrize(
        "escaped,result",
        [
            ("^a", chr(1)),
            ("^?", chr(127)),
            ("^z", chr(26)),
            ("a^Z", "a" + chr(26)),
            ("a^Zb", "a" + chr(26) + "b"),
        ],
    )
    def test_color_parsing_carret(self, escaped: str, result: str) -> None:
        painter = GnuPainter("rs=" + escaped)
        assert painter.color_indicator[GnuIndicators.RESET] == result

        painter = GnuPainter(escaped + "=1;2")
        assert painter.color_ext_type[result] == "1;2"

        painter = GnuPainter(escaped + "=" + escaped)
        assert painter.color_ext_type[result] == result

    @pytest.mark.parametrize("escaped", [("^1"), ("^"), ("^" + chr(130))])
    def test_color_parsing_carret_incorrect(self, escaped: str) -> None:
        with pytest.raises(EnvironmentError):
            GnuPainter("rs=" + escaped)

        with pytest.raises(EnvironmentError):
            GnuPainter(escaped + "=1;2")

    @pytest.mark.parametrize(
        "ls_colors",
        [
            "di=32;41:fi=0;44:no=0;46",
            "di=32;41:no=0;46",
            "no=0;46",
            "*.text=0;46",
            "*.txt=0;46",
        ],
    )
    def test_coloring(self, rich_cmp: Any, ls_colors: str) -> None:
        file = FileStatus(
            "test.txt",
            1024,
            FileStatusType.FILE,
            int(time.mktime(time.strptime("2018-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            uri=URL("storage://default/usertest.txt"),
        )
        folder = FileStatus(
            "tmp",
            0,
            FileStatusType.DIRECTORY,
            int(time.mktime(time.strptime("2018-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.WRITE,
            uri=URL("storage://default/usertmp"),
        )
        link = FileStatus(
            "link",
            1,
            FileStatusType.SYMLINK,
            int(time.mktime(time.strptime("2018-12-31 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.MANAGE,
            target="test.txt",
            uri=URL("storage://default/link"),
        )
        unknown = FileStatus(
            "spam",
            123,
            FileStatusType.UNKNOWN,
            int(time.mktime(time.strptime("2019-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.WRITE,
            uri=URL("storage://default/spam"),
        )
        painter = GnuPainter(ls_colors)
        rich_cmp(painter.paint(file.name, file.type), index=0)
        rich_cmp(painter.paint(folder.name, folder.type), index=1)
        rich_cmp(painter.paint(link.name, link.type), index=2)
        rich_cmp(painter.paint(unknown.name, unknown.type), index=3)


class TestBSDPainter:
    def test_color_parsing(self) -> None:
        painter = BSDPainter("exfxcxdxbxegedabagacad")
        assert painter._colors[BSDAttributes.DIRECTORY] == "ex"

    @pytest.mark.parametrize(
        "ls_colors", ["exfxcxdxbxegedabagacad", "Eafxcxdxbxegedabagacad"]
    )
    def test_coloring(self, ls_colors: str, rich_cmp: Any) -> None:
        file = FileStatus(
            "test.txt",
            1024,
            FileStatusType.FILE,
            int(time.mktime(time.strptime("2018-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            uri=URL("storage://default/usertest.txt"),
        )
        folder = FileStatus(
            "tmp",
            0,
            FileStatusType.DIRECTORY,
            int(time.mktime(time.strptime("2018-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.WRITE,
            uri=URL("storage://default/usertmp"),
        )
        link = FileStatus(
            "link",
            1,
            FileStatusType.SYMLINK,
            int(time.mktime(time.strptime("2018-12-31 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.MANAGE,
            target="test.txt",
            uri=URL("storage://default/link"),
        )
        unknown = FileStatus(
            "spam",
            123,
            FileStatusType.UNKNOWN,
            int(time.mktime(time.strptime("2019-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.WRITE,
            uri=URL("storage://default/spam"),
        )
        painter = BSDPainter(ls_colors)
        rich_cmp(painter.paint(file.name, file.type), index=0)
        rich_cmp(painter.paint(folder.name, folder.type), index=1)
        rich_cmp(painter.paint(link.name, link.type), index=2)
        rich_cmp(painter.paint(unknown.name, unknown.type), index=3)


class TestPainterFactory:
    def test_detection(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("LS_COLORS", "")
        monkeypatch.setenv("LSCOLORS", "")
        painter = get_painter(True)
        assert isinstance(painter, NonePainter)

        monkeypatch.setenv("LSCOLORS", "exfxcxdxbxegedabagacad")
        monkeypatch.setenv("LS_COLORS", "di=32;41:fi=0;44:no=0;46")
        painter_without_color = get_painter(False)
        painter_with_color = get_painter(True)
        assert isinstance(painter_without_color, NonePainter)
        assert not isinstance(painter_with_color, NonePainter)

        monkeypatch.setenv("LSCOLORS", "")
        monkeypatch.setenv("LS_COLORS", "di=32;41:fi=0;44:no=0;46")
        painter = get_painter(True)
        assert isinstance(painter, GnuPainter)

        monkeypatch.setenv("LSCOLORS", "exfxcxdxbxegedabagacad")
        monkeypatch.setenv("LS_COLORS", "")
        painter = get_painter(True)
        assert isinstance(painter, BSDPainter)


class TestFilesFormatter:

    files = [
        FileStatus(
            "File1",
            2048,
            FileStatusType.FILE,
            int(time.mktime(time.strptime("2018-01-01 03:00:00", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            uri=URL("storage://default/userFile1"),
        ),
        FileStatus(
            "File2",
            1024,
            FileStatusType.FILE,
            int(time.mktime(time.strptime("2018-10-10 13:10:10", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            uri=URL("storage://default/userFile2"),
        ),
        FileStatus(
            "File3 with space",
            1_024_001,
            FileStatusType.FILE,
            int(time.mktime(time.strptime("2019-02-02 05:02:02", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            uri=URL("storage://default/userFile 3 with space"),
        ),
    ]
    folders = [
        FileStatus(
            "Folder1",
            0,
            FileStatusType.DIRECTORY,
            int(time.mktime(time.strptime("2017-03-03 06:03:03", "%Y-%m-%d %H:%M:%S"))),
            Action.MANAGE,
            uri=URL("storage://default/userFolder11"),
        ),
        FileStatus(
            "1Folder with space",
            0,
            FileStatusType.DIRECTORY,
            int(time.mktime(time.strptime("2017-03-03 06:03:02", "%Y-%m-%d %H:%M:%S"))),
            Action.MANAGE,
            uri=URL("storage://default/user1Folder with space"),
        ),
    ]
    links = [
        FileStatus(
            "Link1",
            1,
            FileStatusType.SYMLINK,
            int(time.mktime(time.strptime("2020-01-02 03:04:05", "%Y-%m-%d %H:%M:%S"))),
            Action.WRITE,
            target="File1",
            uri=URL("storage://default/Link1"),
        ),
        FileStatus(
            "Link2",
            1,
            FileStatusType.SYMLINK,
            int(time.mktime(time.strptime("2020-02-03 04:05:06", "%Y-%m-%d %H:%M:%S"))),
            Action.READ,
            target="Folder1",
            uri=URL("storage://default/Link2"),
        ),
    ]
    others = [
        FileStatus(
            "Spam1",
            1,
            FileStatusType.UNKNOWN,
            int(time.mktime(time.strptime("2020-01-02 03:04:05", "%Y-%m-%d %H:%M:%S"))),
            Action.WRITE,
            uri=URL("storage://default/Spam1"),
        ),
    ]
    files_and_folders = files + folders
    all_entities = files_and_folders + links + others

    @pytest.mark.parametrize(
        "formatter",
        [
            SimpleFilesFormatter(color=False),
            VerticalColumnsFilesFormatter(width=100, color=False),
            LongFilesFormatter(human_readable=False, color=False),
        ],
    )
    def test_formatter_with_all_entities(
        self, formatter: BaseFilesFormatter, rich_cmp: Any
    ) -> None:
        rich_cmp(formatter(self.all_entities))

    @pytest.mark.parametrize(
        "formatter",
        [
            SimpleFilesFormatter(color=False),
            VerticalColumnsFilesFormatter(width=100, color=False),
            LongFilesFormatter(human_readable=False, color=False),
        ],
    )
    def test_formatter_with_empty_files(
        self, formatter: BaseFilesFormatter, rich_cmp: Any
    ) -> None:
        files: list[FileStatus] = []
        rich_cmp(formatter(files))

    def test_sorter(self) -> None:
        sorter = FilesSorter.NAME
        files = sorted(self.files_and_folders, key=sorter.key())
        assert files == [
            self.folders[1],
            self.files[0],
            self.files[1],
            self.files[2],
            self.folders[0],
        ]

        sorter = FilesSorter.SIZE
        files = sorted(self.files_and_folders, key=sorter.key())
        assert files[2:5] == [self.files[1], self.files[0], self.files[2]]

        sorter = FilesSorter.TIME
        files = sorted(self.files_and_folders, key=sorter.key())
        assert files == [
            self.folders[1],
            self.folders[0],
            self.files[0],
            self.files[1],
            self.files[2],
        ]


class TestUsageFormatter:
    def test_formatter(self, rich_cmp: Any) -> None:
        usage = DiskUsageInfo(
            total=100000,
            used=80000,
            free=20000,
            cluster_name="default",
            org_name="test-org",
        )
        formatter = DiskUsageFormatter()
        rich_cmp(formatter(usage))

    def test_path_formatter(self, rich_cmp: Any) -> None:
        usage = DiskUsageInfo(
            total=100000,
            used=80000,
            free=20000,
            cluster_name="default",
            org_name="org",
            uri=URL("storage://cluster/org"),
        )
        formatter = DiskUsageFormatter()
        rich_cmp(formatter(usage))

    def test_org_formatter(self, rich_cmp: Any) -> None:
        usage = DiskUsageInfo(
            total=100000, used=80000, free=20000, cluster_name="default", org_name="org"
        )
        formatter = DiskUsageFormatter()
        rich_cmp(formatter(usage))
