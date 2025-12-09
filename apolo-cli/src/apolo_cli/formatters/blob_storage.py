import abc
from collections.abc import Sequence
from typing import Union

from rich.console import RenderableType
from rich.table import Table

from apolo_sdk import Bucket, BucketEntry, FileStatusType

from apolo_cli.formatters.utils import URIFormatter
from apolo_cli.utils import format_size

from .storage import TIME_FORMAT, get_painter

BlobListing = Union[Bucket, BucketEntry]


def get_file_type(file: BlobListing) -> FileStatusType:
    if isinstance(file, Bucket) or file.is_dir():
        return FileStatusType.DIRECTORY
    else:
        return FileStatusType.FILE


class BaseBlobFormatter:
    @abc.abstractmethod
    def __call__(self, entry: BlobListing) -> RenderableType:  # pragma: no cover
        pass


class SimpleBlobFormatter(BaseBlobFormatter):
    def __init__(self, color: bool, uri_formatter: URIFormatter):
        self.painter = get_painter(color)
        self.uri_formatter = uri_formatter

    def __call__(self, file: BlobListing) -> RenderableType:
        return self.painter.paint(self.uri_formatter(file.uri), get_file_type(file))


class LongBlobFormatter(BaseBlobFormatter):
    def __init__(self, human_readable: bool, color: bool, uri_formatter: URIFormatter):
        self.human_readable = human_readable
        self.painter = get_painter(color)
        self.uri_formatter = uri_formatter

    def to_row(self, file: BlobListing) -> Sequence[RenderableType]:
        if isinstance(file, Bucket):
            return self.to_row_bucket(file)
        elif isinstance(file, BucketEntry):
            return self.to_row_blob(file)

    def to_row_bucket(self, file: Bucket) -> Sequence[RenderableType]:
        date = file.created_at.strftime(TIME_FORMAT)
        name = self.painter.paint(self.uri_formatter(file.uri), get_file_type(file))
        return [f"bucket", f"", f"{date}", name]

    def to_row_blob(self, file: BucketEntry) -> Sequence[RenderableType]:
        if file.modified_at:
            date = file.modified_at.strftime(TIME_FORMAT)
        elif file.created_at:
            date = file.created_at.strftime(TIME_FORMAT)
        else:
            date = ""
        if self.human_readable:
            size = format_size(file.size).rstrip("B")
        else:
            size = str(file.size)
        name = self.painter.paint(self.uri_formatter(file.uri), get_file_type(file))
        if file.is_dir():
            type_ = "dir"
        else:
            type_ = "obj"
        return [type_, f"{size}", f"{date}", name]

    def __call__(self, file: BlobListing) -> RenderableType:
        table = Table.grid(padding=(0, 2))
        table.show_header = False
        table.add_column(width=7)  # Type
        table.add_column(justify="right", width=8)  # Size
        table.add_column()  # Date
        table.add_column()  # Filename
        table.add_row(*self.to_row(file))
        return table
