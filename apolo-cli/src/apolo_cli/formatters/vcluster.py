import abc
import operator
from collections.abc import Sequence

from rich import box
from rich.console import Group as RichGroup
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from apolo_sdk import KubeServiceAccount

from apolo_cli.formatters.utils import DatetimeFormatter


class BaseKubeConfigFormatter(abc.ABC):
    @abc.abstractmethod
    def __call__(
        self, service_accounts: Sequence[KubeServiceAccount]
    ) -> RenderableType:
        pass


class SimpleKubeConfigFormatter(BaseKubeConfigFormatter):
    def __call__(
        self, service_accounts: Sequence[KubeServiceAccount]
    ) -> RenderableType:
        return RichGroup(*(Text(sa.name) for sa in service_accounts))


class KubeConfigFormatter(BaseKubeConfigFormatter):
    def __init__(
        self,
        datetime_formatter: DatetimeFormatter,
        *,
        long_format: bool = False,
    ) -> None:
        self._datetime_formatter = datetime_formatter
        self._long_format = long_format

    def _sa_to_table_row(self, sa: KubeServiceAccount) -> Sequence[str]:
        line = [
            sa.name,
            self._datetime_formatter(sa.created_at),
            self._datetime_formatter(sa.expired_at),
        ]
        if self._long_format:
            line += [
                sa.user,
            ]
        return line

    def __call__(
        self, service_accounts: Sequence[KubeServiceAccount]
    ) -> RenderableType:
        service_accounts = sorted(service_accounts, key=operator.attrgetter("name"))
        table = Table(box=box.SIMPLE_HEAVY)
        # make sure that the first column is fully expanded
        table.add_column("Name", style="bold")
        table.add_column("Created at")
        table.add_column("Expired at")
        if self._long_format:
            table.add_column("User")
        for sa in service_accounts:
            table.add_row(*self._sa_to_table_row(sa))
        return table
