from typing import List

from rich.table import Table, box

from apolo_sdk import AppTemplate


class BaseAppTemplatesFormatter:
    def __call__(self, templates: List[AppTemplate]) -> Table:
        raise NotImplementedError("Subclasses must implement __call__")


class SimpleAppTemplatesFormatter(BaseAppTemplatesFormatter):
    def __call__(self, templates: List[AppTemplate]) -> Table:
        table = Table.grid()
        table.add_column("")
        for template in templates:
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
