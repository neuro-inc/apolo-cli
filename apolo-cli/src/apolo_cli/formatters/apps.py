from collections import defaultdict
from typing import Any, Dict, List, Union

from rich.console import Group
from rich.table import Table, box
from rich.text import Text

from apolo_sdk import App, AppEvent, AppEventResource


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
        table.add_column("Creator")
        table.add_column("Version")
        table.add_column("State")

        for app in apps:
            table.add_row(
                app.id,
                app.name,
                app.display_name,
                app.template_name,
                app.creator,
                app.template_version,
                app.state,
            )
        return table


class BaseAppEventsFormatter:
    def __call__(self, events: List[AppEvent]) -> Union[Table, Group, str]:
        raise NotImplementedError("Subclasses must implement __call__")


class SimpleAppEventsFormatter(BaseAppEventsFormatter):
    def __call__(self, events: List[AppEvent]) -> Table:
        table = Table.grid()
        table.add_column("")
        for event in events:
            table.add_row(f"{event.created_at}|{event.state}|{event.reason}")
        return table


class AppEventsFormatter(BaseAppEventsFormatter):
    def __call__(self, events: List[AppEvent]) -> Group:
        renderables = []

        for i, event in enumerate(events):
            if i > 0:
                renderables.append(Text(""))  # Blank line between events

            # Event header
            header = Text()
            header.append("Event: ", style="bold")
            header.append(str(event.created_at))
            header.append("   STATE: ", style="bold")
            header.append(event.state, style=self._get_state_style(event.state))
            header.append("   REASON: ", style="bold")
            header.append(event.reason)
            renderables.append(header)

            # Message
            if event.message:
                msg_text = Text()
                msg_text.append("Message: ", style="bold")
                msg_text.append(event.message)
                renderables.append(msg_text)

            # Resources
            if event.resources:
                renderables.append(Text(""))
                renderables.append(Text("Resources", style="bold underline"))
                renderables.append(Text("=" * 40))

                # Group resources by kind
                resources_by_kind: Dict[str, List[AppEventResource]] = defaultdict(list)
                for res in event.resources:
                    resources_by_kind[res.kind.lower()].append(res)

                # Display each resource type
                for kind, resources in resources_by_kind.items():
                    renderables.append(Text(""))
                    kind_title = f"{kind.capitalize()} resources"
                    renderables.append(Text(kind_title, style="bold"))
                    renderables.append(Text("-" * len(kind_title)))

                    for res in resources:
                        self._format_resource(res, renderables)

        return Group(*renderables)

    def _get_state_style(self, state: str) -> str:
        state_lower = state.lower()
        if state_lower in ("healthy", "running"):
            return "green"
        elif state_lower in ("degraded", "errored", "error"):
            return "red"
        elif state_lower in ("progressing", "pending", "queued"):
            return "yellow"
        return ""

    def _format_resource(
        self, res: AppEventResource, renderables: List[Any]
    ) -> None:
        # Resource name line
        name_line = Text()
        name_line.append("└─ ")
        if res.kind:
            name_line.append(res.kind.lower(), style="cyan")
            name_line.append("  ")
        if res.name:
            name_line.append(res.name)
        renderables.append(name_line)

        # Health status line
        if res.health_status:
            status_line = Text()
            status_line.append("   STATUS: ")
            status_line.append(
                res.health_status, style=self._get_state_style(res.health_status)
            )
            renderables.append(status_line)

        # Health message line if present
        if res.health_message:
            msg_line = Text()
            msg_line.append("   MSG:   ", style="dim")
            msg_line.append(res.health_message)
            renderables.append(msg_line)
