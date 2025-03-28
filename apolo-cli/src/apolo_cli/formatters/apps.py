from typing import List

from rich.table import Table, box

from apolo_sdk import App


class BaseAppsFormatter:
    def __call__(self, apps: List[App]) -> Table:
        raise NotImplementedError("Subclasses must implement __call__")


class SimpleAppsFormatter(BaseAppsFormatter):
    def __call__(self, apps: List[App]) -> Table:
        table = Table.grid()
        table.add_column("")
        for app in apps:
            table.add_row(app.id)
        return table


class AppsFormatter(BaseAppsFormatter):
    def __call__(self, apps: List[App]) -> Table:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Display Name")
        table.add_column("Template")
        table.add_column("Version")
        table.add_column("State")

        for app in apps:
            table.add_row(
                app.id,
                app.name,
                app.display_name,
                app.template_name,
                app.template_version,
                app.state,
            )
        return table
