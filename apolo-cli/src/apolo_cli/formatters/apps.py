from collections import defaultdict
from typing import Any

from rich.console import Group, RenderableType
from rich.table import Table, box
from rich.text import Text

from apolo_sdk import App, AppConfigurationRevision, AppEvent, AppEventResource


class BaseAppsFormatter:
    def __call__(self, apps: list[App]) -> Table:
        raise NotImplementedError("Subclasses must implement __call__")


class SimpleAppsFormatter(BaseAppsFormatter):
    def __call__(self, apps: list[App]) -> Table:
        table = Table.grid()
        table.add_column("")
        for app in apps:
            table.add_row(app.id)
        return table


class AppsFormatter(BaseAppsFormatter):
    def __call__(self, apps: list[App]) -> Table:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("ID", no_wrap=True)
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
    def __call__(self, events: list[AppEvent]) -> RenderableType:
        raise NotImplementedError("Subclasses must implement __call__")


class SimpleAppEventsFormatter(BaseAppEventsFormatter):
    def __call__(self, events: list[AppEvent]) -> Table:
        table = Table.grid(padding=(0, 2))
        table.add_column("")  # created_at
        table.add_column("")  # state
        table.add_column("")  # reason
        for event in events:
            table.add_row(str(event.created_at), event.state, event.reason)
        return table


class AppEventsFormatter(BaseAppEventsFormatter):
    SEPARATOR = "=" * 80
    SUB_SEPARATOR = "-" * 40

    def __call__(self, events: list[AppEvent]) -> Group:
        renderables: list[Any] = []

        for i, event in enumerate(events):
            if i > 0:
                renderables.append(Text(""))  # Blank line between events

            # Event separator
            renderables.append(Text(self.SEPARATOR))

            # Event header
            header = Text()
            header.append("Event @ ", style="bold")
            header.append(str(event.created_at))
            renderables.append(header)

            # STATE line
            state_line = Text()
            state_line.append("STATE: ", style="bold")
            state_line.append(event.state, style=self._get_state_style(event.state))
            renderables.append(state_line)

            # REASON line
            reason_line = Text()
            reason_line.append("REASON: ", style="bold")
            reason_line.append(event.reason or "")
            renderables.append(reason_line)

            # Message (if present)
            if event.message:
                renderables.append(Text(""))
                renderables.append(Text("Message:", style="bold"))
                renderables.append(Text(f"  {event.message}"))

            # Resources (if present)
            if event.resources:
                renderables.append(Text(""))
                renderables.append(Text("Resources", style="bold"))
                renderables.append(Text(self.SUB_SEPARATOR))

                # Group resources by kind
                resources_by_kind: dict[str, list[AppEventResource]] = defaultdict(list)
                for res in event.resources:
                    kind = res.kind or "Unknown"
                    resources_by_kind[kind].append(res)

                # Display each resource type
                for kind, resources in resources_by_kind.items():
                    renderables.append(Text(f" {kind}:", style="bold"))
                    for res in resources:
                        self._format_resource(res, renderables)
                    renderables.append(Text(""))

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

    def _format_resource(self, res: AppEventResource, renderables: list[Any]) -> None:
        line = Text()
        line.append("   - ")
        if res.name:
            line.append(res.name)
        if res.health_status:
            line.append("  (")
            line.append(
                res.health_status, style=self._get_state_style(res.health_status)
            )
            line.append(")")
        renderables.append(line)


class BaseAppRevisionsFormatter:
    def __call__(self, revisions: list[AppConfigurationRevision]) -> Table:
        raise NotImplementedError("Subclasses must implement __call__")


class SimpleAppRevisionsFormatter(BaseAppRevisionsFormatter):
    def __call__(self, revisions: list[AppConfigurationRevision]) -> Table:
        table = Table.grid()
        table.add_column("")
        for revision in revisions:
            table.add_row(str(revision.revision_number))
        return table


class AppRevisionsFormatter(BaseAppRevisionsFormatter):
    def __call__(self, revisions: list[AppConfigurationRevision]) -> Table:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Revision Number")
        table.add_column("Creator")
        table.add_column("Comment")
        table.add_column("Created At")
        table.add_column("End At")

        for revision in revisions:
            is_current = revision.end_at is None
            style = "bold" if is_current else None
            table.add_row(
                str(revision.revision_number),
                revision.creator,
                revision.comment or "",
                str(revision.created_at),
                str(revision.end_at) if revision.end_at else "~",
                style=style,
            )
        return table
