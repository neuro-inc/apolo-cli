import json
from typing import List

from rich.table import Table, box

from apolo_sdk import AppValue


class BaseAppValuesFormatter:
    def __call__(self, values: List[AppValue]) -> Table:
        raise NotImplementedError(
            "Subclasses must implement __call__"
        )  # pragma: no cover


class SimpleAppValuesFormatter(BaseAppValuesFormatter):
    def __call__(self, values: List[AppValue]) -> Table:
        table = Table.grid()
        table.add_column("")
        for value in values:
            formatted_value = (
                json.dumps(value.value)
                if value.type in ("dict", "list")
                else value.value
            )
            table.add_row(
                f"{value.app_instance_id}:{value.type}:{value.path}:{formatted_value}"
            )
        return table


class AppValuesFormatter(BaseAppValuesFormatter):
    def __call__(self, values: List[AppValue]) -> Table:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("App Instance ID")
        table.add_column("Type")
        table.add_column("Path")
        table.add_column("Value")

        for value in values:
            formatted_value = (
                json.dumps(value.value)
                if value.type in ("dict", "list")
                else value.value
            )
            table.add_row(
                value.app_instance_id,
                value.type,
                value.path,
                str(formatted_value) if formatted_value is not None else "",
            )
        return table
