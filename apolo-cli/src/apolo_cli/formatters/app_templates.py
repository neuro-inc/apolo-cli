from typing import List

from rich.table import Table, box

from apolo_sdk import AppTemplate


class BaseAppTemplatesFormatter:
    def __call__(self, templates: List[AppTemplate]) -> Table:
        raise NotImplementedError(
            "Subclasses must implement __call__"
        )  # pragma: no cover


class SimpleAppTemplatesFormatter(BaseAppTemplatesFormatter):
    def __init__(self, is_version_list: bool = False) -> None:
        self.is_version_list = is_version_list

    def __call__(self, templates: List[AppTemplate]) -> Table:
        table = Table.grid()
        table.add_column("")
        for template in templates:
            if self.is_version_list:
                # When listing versions, only show version
                table.add_row(template.version)
            else:
                # When listing templates, only show name
                table.add_row(template.name)
        return table


class AppTemplatesFormatter(BaseAppTemplatesFormatter):
    def __call__(self, templates: List[AppTemplate]) -> Table:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Name")
        table.add_column("Title")
        table.add_column("Version")
        table.add_column("Description")
        table.add_column("Tags")

        for template in templates:
            table.add_row(
                template.name,
                template.title,
                template.version,
                template.short_description,
                ", ".join(template.tags),
            )
        return table
