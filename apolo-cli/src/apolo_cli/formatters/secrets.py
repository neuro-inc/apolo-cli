import abc
import operator
from collections.abc import Sequence

from rich import box
from rich.console import Group as RichGroup
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from apolo_sdk import Secret

from apolo_cli.formatters.utils import URIFormatter


class BaseSecretsFormatter:
    @abc.abstractmethod
    def __call__(self, secrets: Sequence[Secret]) -> RenderableType:
        pass


class SimpleSecretsFormatter(BaseSecretsFormatter):
    def __call__(self, secrets: Sequence[Secret]) -> RenderableType:
        return RichGroup(*(Text(secret.key) for secret in secrets))


class SecretsFormatter(BaseSecretsFormatter):
    def __init__(
        self,
        uri_formatter: URIFormatter,
    ) -> None:
        self._uri_formatter = uri_formatter

    def _secret_to_table_row(self, secret: Secret) -> Sequence[str]:
        line = [
            self._uri_formatter(secret.uri),
            secret.org_name,
            secret.project_name,
        ]
        return line

    def __call__(self, secrets: Sequence[Secret]) -> RenderableType:
        secrets = sorted(secrets, key=operator.attrgetter("key"))
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Key", style="bold")
        table.add_column("Org")
        table.add_column("Project")

        for secret in secrets:
            table.add_row(*self._secret_to_table_row(secret))
        return table
