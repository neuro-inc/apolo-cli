import abc
import operator
from collections.abc import Sequence
from datetime import timedelta

from rich import box
from rich.console import Group as RichGroup
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from apolo_sdk import Disk

from apolo_cli import utils
from apolo_cli.formatters.utils import DatetimeFormatter, URIFormatter, format_timedelta


class BaseDisksFormatter:
    @abc.abstractmethod
    def __call__(self, jobs: Sequence[Disk]) -> RenderableType:
        pass


class SimpleDisksFormatter(BaseDisksFormatter):
    def __call__(self, disks: Sequence[Disk]) -> RenderableType:
        return RichGroup(*(Text(disk.id) for disk in disks))


class DisksFormatter(BaseDisksFormatter):
    def __init__(
        self,
        uri_formatter: URIFormatter,
        datetime_formatter: DatetimeFormatter,
        *,
        long_format: bool = False,
    ) -> None:
        self._uri_formatter = uri_formatter
        self._datetime_formatter = datetime_formatter
        self._long_format = long_format

    def _disk_to_table_row(self, disk: Disk) -> Sequence[str]:
        storage_str = utils.format_size(disk.storage)

        used_str = utils.format_size(disk.used_bytes)
        line = [
            disk.id,
            disk.name or "",
            storage_str,
            used_str,
            self._uri_formatter(disk.uri),
            disk.status.value,
        ]
        if self._long_format:
            line += [
                disk.org_name,
                disk.project_name,
                self._datetime_formatter(disk.created_at),
                self._datetime_formatter(disk.last_usage),
                format_disk_timeout_unused(disk.timeout_unused),
            ]
        return line

    def __call__(self, disks: Sequence[Disk]) -> RenderableType:
        disks = sorted(disks, key=operator.attrgetter("id"))
        table = Table(box=box.SIMPLE_HEAVY)
        # make sure that the first column is fully expanded
        width = len("disk-06bed296-8b27-4aa8-9e2a-f3c47b41c807")
        table.add_column("Id", style="bold", width=width)
        table.add_column("Name")
        table.add_column("Storage")
        table.add_column("Used")
        table.add_column("Uri")
        table.add_column("Status")
        if self._long_format:
            table.add_column("Org name")
            table.add_column("Project name")
            table.add_column("Created at")
            table.add_column("Last used")
            table.add_column("Timeout unused")
        for disk in disks:
            table.add_row(*self._disk_to_table_row(disk))
        return table


class DiskFormatter:
    def __init__(
        self, uri_formatter: URIFormatter, datetime_formatter: DatetimeFormatter
    ) -> None:
        self._datetime_formatter = datetime_formatter
        self._uri_formatter = uri_formatter

    def __call__(self, disk: Disk) -> RenderableType:
        table = Table(
            box=None,
            show_header=False,
            show_edge=False,
        )
        table.add_column()
        table.add_column(style="bold")
        table.add_row("Id", disk.id)
        table.add_row("Storage", utils.format_size(disk.storage))
        table.add_row("Used", utils.format_size(disk.used_bytes))
        table.add_row("Uri", self._uri_formatter(disk.uri))
        if disk.name:
            table.add_row("Name", disk.name)
        table.add_row("Org name", disk.org_name)
        table.add_row("Project name", disk.project_name)
        table.add_row("Owner", disk.owner)
        table.add_row("Status", disk.status.value)
        table.add_row("Created at", self._datetime_formatter(disk.created_at))
        table.add_row("Last used", self._datetime_formatter(disk.last_usage))
        table.add_row("Timeout unused", format_disk_timeout_unused(disk.timeout_unused))
        return table


def format_disk_timeout_unused(timeout_unused: timedelta | None) -> str:
    if timeout_unused is not None:
        return format_timedelta(timeout_unused)
    else:
        return "no limit"
