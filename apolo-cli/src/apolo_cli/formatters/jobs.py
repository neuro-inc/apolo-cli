import abc
import datetime
import itertools
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from types import TracebackType

import humanize
from rich import box
from rich.console import Console, ConsoleRenderable, RenderableType, RenderHook
from rich.control import Control
from rich.live_render import LiveRender
from rich.markup import escape as rich_escape
from rich.styled import Styled
from rich.table import Table
from rich.text import Text, TextType

from apolo_sdk import JobDescription, JobRestartPolicy, JobStatus, JobTelemetry

from apolo_cli.formatters.utils import DatetimeFormatter, format_gpu_string
from apolo_cli.parse_utils import JobTableFormat, JobTelemetryKeyFunc
from apolo_cli.utils import format_size

from .utils import (
    ImageFormatter,
    URIFormatter,
    format_timedelta,
    image_formatter,
    no,
    yes,
)

COLORS = {
    JobStatus.PENDING: "cyan",
    JobStatus.SUSPENDED: "magenta",
    JobStatus.RUNNING: "blue",
    JobStatus.SUCCEEDED: "green",
    JobStatus.CANCELLED: "yellow",
    JobStatus.FAILED: "red",
    JobStatus.UNKNOWN: "bright_red",
}


if sys.platform == "win32":
    SPINNER = itertools.cycle(r"-\|/")
else:
    SPINNER = itertools.cycle("◢◣◤◥")


def fmt_status(status: JobStatus) -> Text:
    color = COLORS.get(status, "none")
    return Text(status.value, style=color)


def get_lifespan_ends(job: JobDescription) -> datetime.datetime | None:
    if (
        job.status
        in [
            JobStatus.PENDING,
            JobStatus.RUNNING,
            JobStatus.SUSPENDED,
        ]
        and job.life_span
    ):
        life_span = datetime.timedelta(seconds=job.life_span)
        run_time = datetime.timedelta(seconds=job.history.run_time_seconds or 0)
        runtime_left = life_span - run_time
        runtime_ends = datetime.datetime.now(datetime.timezone.utc) + runtime_left
        return runtime_ends
    return None


class JobStatusFormatter:
    def __init__(
        self, uri_formatter: URIFormatter, datetime_formatter: DatetimeFormatter
    ) -> None:
        self._format_uri = uri_formatter
        self._datetime_formatter = datetime_formatter
        self._format_image = image_formatter(uri_formatter=uri_formatter)

    def __call__(self, job_status: JobDescription) -> RenderableType:
        assert job_status.history is not None

        table = Table(box=None, show_header=False, show_edge=False)
        table.add_column()
        table.add_column(style="bold")
        table.add_row("Job", job_status.id)
        if job_status.name:
            table.add_row("Name", job_status.name)
        if job_status.tags:
            text = ", ".join(job_status.tags)
            table.add_row("Tags", text)
        table.add_row("Owner", job_status.owner or "")
        table.add_row("Project", job_status.project_name or "")
        table.add_row("Cluster", job_status.cluster_name)
        if job_status.org_name:
            table.add_row("Organization", job_status.org_name)
        if job_status.description:
            table.add_row("Description", job_status.description)
        status_text = fmt_status(job_status.status)
        if job_status.history.reason:
            status_text = Text.assemble(status_text, f" ({job_status.history.reason})")
        table.add_row("Status", status_text)
        table.add_row("Image", self._format_image(job_status.container.image))

        if job_status.container.entrypoint:
            table.add_row("Entrypoint", job_status.container.entrypoint)
        if job_status.container.command:
            table.add_row("Command", job_status.container.command)
        if job_status.container.working_dir:
            table.add_row("Working dir", job_status.container.working_dir)
        if job_status.preset_name:
            table.add_row("Preset", job_status.preset_name)
        if job_status.energy_schedule_name:
            table.add_row("Energy schedule", job_status.energy_schedule_name)
        table.add_row("Priority", f"{job_status.priority.name.capitalize()}")
        table.add_row(
            "Price (credits / hour)", f"{job_status.price_credits_per_hour:.4f}"
        )
        table.add_row("Current cost", f"{job_status.total_price_credits:.4f}")

        resources = Table(box=None, show_header=False, show_edge=False)
        resources.add_column()
        resources.add_column(style="bold", justify="right")
        resources.add_row("Memory", format_size(job_status.container.resources.memory))
        resources.add_row("CPU", f"{job_status.container.resources.cpu:0.1f}")
        if job_status.container.resources.nvidia_gpu:
            resources.add_row(
                "Nvidia GPU",
                format_gpu_string(
                    job_status.container.resources.nvidia_gpu,
                    job_status.container.resources.nvidia_gpu_model,
                ),
            )
        if job_status.container.resources.amd_gpu:
            resources.add_row(
                "AMD GPU",
                format_gpu_string(
                    job_status.container.resources.amd_gpu,
                    job_status.container.resources.amd_gpu_model,
                ),
            )
        if job_status.container.resources.intel_gpu:
            resources.add_row(
                "Intel GPU",
                format_gpu_string(
                    job_status.container.resources.intel_gpu,
                    job_status.container.resources.intel_gpu_model,
                ),
            )

        if job_status.container.resources.tpu_type:
            resources.add_row(
                "TPU",
                f"{job_status.container.resources.tpu_type}/"
                f"{job_status.container.resources.tpu_software_version}",
            )

        if job_status.container.resources.shm:
            resources.add_row("Extended SHM space", "True")

        table.add_row("Resources", Styled(resources, style="reset"))

        if job_status.scheduler_enabled:
            table.add_row("Round Robin", "True")
        if job_status.preemptible_node:
            table.add_row("Preemptible Node", "True")
        if job_status.restart_policy != JobRestartPolicy.NEVER:
            table.add_row("Restart policy", job_status.restart_policy.value)
        if job_status.history.restarts != 0:
            table.add_row("Restarts", str(job_status.history.restarts))
        if job_status.life_span is not None:
            table.add_row("Life span", format_life_span(job_status.life_span))

        table.add_row("TTY", str(job_status.container.tty))

        if job_status.container.volumes:
            volumes = Table(box=None, show_header=False, show_edge=False)
            volumes.add_column("")
            volumes.add_column("")
            volumes.add_column("")
            for volume in job_status.container.volumes:
                volumes.add_row(
                    volume.container_path,
                    self._format_uri(volume.storage_uri),
                    "READONLY" if volume.read_only else " ",
                )
            table.add_row("Volumes", Styled(volumes, style="reset"))

        if job_status.container.secret_files:
            secret_files = Table(box=None, show_header=False, show_edge=False)
            secret_files.add_column("")
            secret_files.add_column("")
            for secret_file in job_status.container.secret_files:
                secret_files.add_row(
                    secret_file.container_path, self._format_uri(secret_file.secret_uri)
                )
            table.add_row("Secret files", Styled(secret_files, style="reset"))

        if job_status.container.disk_volumes:
            disk_volumes = Table(box=None, show_header=False, show_edge=False)
            disk_volumes.add_column("")
            disk_volumes.add_column("")
            disk_volumes.add_column("")
            for disk_volume in job_status.container.disk_volumes:
                disk_volumes.add_row(
                    disk_volume.container_path,
                    self._format_uri(disk_volume.disk_uri),
                    "READONLY" if disk_volume.read_only else " ",
                )
            table.add_row("Disk volumes", Styled(disk_volumes, style="reset"))

        if job_status.internal_hostname:
            table.add_row("Internal Hostname", job_status.internal_hostname)
        if job_status.internal_hostname_named:
            table.add_row("Internal Hostname Named", job_status.internal_hostname_named)
        if job_status.http_url:
            table.add_row("Http URL", str(job_status.http_url))
        if job_status.container.http:
            table.add_row("Http port", str(job_status.container.http.port))
            table.add_row(
                "Http authentication", str(job_status.container.http.requires_auth)
            )
        if job_status.container.env:
            environment = Table(box=None, show_header=False, show_edge=False)
            environment.add_column("")
            environment.add_column("")
            for key, value in job_status.container.env.items():
                environment.add_row(key, value)
            table.add_row("Environment", Styled(environment, style="reset"))
        if job_status.container.secret_env:
            secret_env = Table(box=None, show_header=False, show_edge=False)
            secret_env.add_column("")
            secret_env.add_column("")
            for key, uri in job_status.container.secret_env.items():
                secret_env.add_row(key, self._format_uri(uri))
            table.add_row("Secret environment", Styled(secret_env, style="reset"))

        assert job_status.history.created_at is not None
        table.add_row(
            "Created",
            self._datetime_formatter(job_status.history.created_at, precise=True),
        )
        if job_status.status in [
            JobStatus.RUNNING,
            JobStatus.SUSPENDED,
            JobStatus.FAILED,
            JobStatus.SUCCEEDED,
            JobStatus.CANCELLED,
        ]:
            assert job_status.history.started_at is not None
            table.add_row(
                "Started",
                self._datetime_formatter(job_status.history.started_at, precise=True),
            )
        lifespan_ends = get_lifespan_ends(job_status)
        if lifespan_ends:
            table.add_row(
                "Life span ends (approx)", self._datetime_formatter(lifespan_ends)
            )
        if job_status.status in [
            JobStatus.CANCELLED,
            JobStatus.FAILED,
            JobStatus.SUCCEEDED,
        ]:
            assert job_status.history.finished_at is not None
            table.add_row(
                "Finished",
                self._datetime_formatter(job_status.history.finished_at, precise=True),
            )
            table.add_row("Exit code", str(job_status.history.exit_code))
        if job_status.status == JobStatus.FAILED and job_status.history.description:
            table.add_row("Description", job_status.history.description)
        if job_status.history.transitions:
            status_transitions = Table(box=None, show_header=True, show_edge=False)
            status_transitions.add_column("Status")
            status_transitions.add_column("Time")
            for status_item in job_status.history.transitions:
                status_text = fmt_status(status_item.status)
                if status_item.reason:
                    status_text = Text.assemble(status_text, f" ({status_item.reason})")
                status_transitions.add_row(
                    status_text,
                    self._datetime_formatter(status_item.transition_time, precise=True),
                )
            table.add_row(
                "Status transitions", Styled(status_transitions, style="reset")
            )
        return table


class LifeSpanUpdateFormatter:
    def __init__(self, datetime_formatter: DatetimeFormatter) -> None:
        self._datetime_formatter = datetime_formatter

    def __call__(self, job_status: JobDescription) -> RenderableType:
        res = (
            f"Updated job {job_status.id} life span to "
            f"be {format_life_span(job_status.life_span)}"
        )
        life_span_ends = get_lifespan_ends(job_status)
        if life_span_ends is not None:
            res += (
                f"\nLife span ends (approx): {self._datetime_formatter(life_span_ends)}"
            )
        return res


def format_life_span(life_span: float | None) -> str:
    if life_span is None:
        return ""
    if life_span == 0:
        return "no limit"
    return format_timedelta(datetime.timedelta(seconds=life_span))


class JobTelemetryFormatter(RenderHook):
    def __init__(
        self,
        console: Console,
        username: str,
        sort_keys: list[tuple[JobTelemetryKeyFunc, bool]],
        columns: JobTableFormat,
        image_formatter: ImageFormatter,
        datetime_formatter: DatetimeFormatter,
        maxrows: int | None = None,
    ) -> None:
        self._console = console
        self._username = username
        self.sort_keys = sort_keys
        self._columns = columns
        self._image_formatter = image_formatter
        self._datetime_formatter = datetime_formatter
        self._maxrows = maxrows
        self._live_render = LiveRender(Table.grid())
        self._data: dict[str, tuple[JobDescription, JobTelemetry]] = {}
        self.changed = True

    def update(self, job: JobDescription, info: JobTelemetry) -> None:
        self._data[job.id] = job, info
        self.changed = True

    def remove(self, job_id: str) -> None:
        self._data.pop(job_id, None)
        self.changed = True

    def render(self) -> None:
        table = Table(box=box.SIMPLE_HEAVY)
        _add_columns(table, self._columns)

        items = list(self._data.values())
        for keyfunc, reverse in reversed(self.sort_keys):
            items.sort(key=keyfunc, reverse=reverse)
        maxrows = self._console.size.height - 4
        if self._maxrows is not None and self._maxrows < maxrows:
            maxrows = self._maxrows
        del items[max(maxrows, 1) :]

        for job, info in items:
            job_data = TabularJobRow.from_job(
                job,
                self._username,
                image_formatter=self._image_formatter,
                datetime_formatter=self._datetime_formatter,
            )
            telemetry_data = {
                "cpu": f"{info.cpu:.3f}",
                "memory": f"{info.memory:.3f}",
                "gpu": f"{info.gpu_duty_cycle}" if info.gpu_duty_cycle else "0",
                "gpu_memory": f"{info.gpu_memory:.3f}" if info.gpu_memory else "0",
            }

            def get(id: str) -> TextType:
                if id in telemetry_data:
                    return telemetry_data[id]
                else:
                    return getattr(job_data, id)

            table.add_row(*_format_row(self._columns, get))

        if self._console.is_terminal:
            self._live_render.set_renderable(table)
            with self._console:
                self._console.print(Control())
        else:
            self._console.print(table)
        self.changed = False

    def process_renderables(
        self, renderables: list[ConsoleRenderable]
    ) -> list[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        if self._console.is_terminal:
            renderables = [
                self._live_render.position_cursor(),
                *renderables,
                self._live_render,
            ]
        return renderables

    def __enter__(self) -> "JobTelemetryFormatter":
        self._console.show_cursor(False)
        self._console.push_render_hook(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._console.line()
        self._console.show_cursor(True)
        self._console.pop_render_hook()


class BaseJobsFormatter:
    @abc.abstractmethod
    def __call__(self, jobs: Iterable[JobDescription]) -> RenderableType:
        pass


class SimpleJobsFormatter(BaseJobsFormatter):
    def __call__(self, jobs: Iterable[JobDescription]) -> RenderableType:
        table = Table.grid()
        table.add_column("")
        for job in jobs:
            table.add_row(job.id)
        return table


@dataclass(frozen=True)
class TabularJobRow:
    id: str
    name: str
    tags: str
    status: Text
    when: str
    created: str
    started: str
    finished: str
    image: str
    owner: str
    description: str
    cluster_name: str
    org_name: str
    command: str
    life_span: str
    workdir: str
    preset: str
    project_name: str

    @classmethod
    def from_job(
        cls,
        job: JobDescription,
        username: str,
        image_formatter: ImageFormatter,
        datetime_formatter: DatetimeFormatter,
    ) -> "TabularJobRow":
        return cls(
            id=job.id,
            name=job.name if job.name else "",
            tags=",".join(job.tags),
            status=fmt_status(job.status),
            when=datetime_formatter(job.history.changed_at),
            created=datetime_formatter(job.history.created_at),
            started=datetime_formatter(job.history.started_at),
            finished=datetime_formatter(job.history.finished_at),
            image=image_formatter(job.container.image),
            owner=("YOU" if job.owner == username else job.owner),
            description=job.description if job.description else "",
            cluster_name=job.cluster_name,
            org_name=job.org_name or "",
            command=job.container.command if job.container.command else "",
            life_span=format_life_span(job.life_span),
            workdir=job.container.working_dir or "",
            preset=job.preset_name or "",
            project_name=job.project_name or "",
        )

    def to_list(self, columns: JobTableFormat) -> list[TextType]:
        return _format_row(columns, lambda id: getattr(self, id))


def _format_row(
    columns: JobTableFormat, get: Callable[[str], TextType]
) -> list[TextType]:
    result: list[TextType] = []
    for column in columns:
        if "/" in column.id:
            cell: list[TextType] = []
            for id in column.id.split("/"):
                value = get(id)
                if cell:
                    cell.append("\n ")  # new line and indentation
                    if isinstance(value, Text):
                        value.stylize("italic")
                    else:
                        value = Text(value, style="italic")
                cell.append(value)
            result.append(Text.assemble(*cell))
        else:
            result.append(get(column.id))
    return result


class TabularJobsFormatter(BaseJobsFormatter):
    def __init__(
        self,
        username: str,
        columns: JobTableFormat,
        image_formatter: ImageFormatter,
        datetime_formatter: DatetimeFormatter,
    ) -> None:
        self._username = username
        self._columns = columns
        self._image_formatter = image_formatter
        self._datetime_formatter = datetime_formatter

    def __call__(self, jobs: Iterable[JobDescription]) -> RenderableType:
        table = Table(box=box.SIMPLE_HEAVY)
        _add_columns(table, self._columns)

        for job in jobs:
            table.add_row(
                *TabularJobRow.from_job(
                    job,
                    self._username,
                    image_formatter=self._image_formatter,
                    datetime_formatter=self._datetime_formatter,
                ).to_list(self._columns)
            )
        return table


class JobStartProgress:
    time_factory = staticmethod(time.monotonic)

    @classmethod
    def create(cls, console: Console, quiet: bool) -> "JobStartProgress":
        if quiet:
            return JobStartProgress()
        elif console.is_terminal:
            return DetailedJobStartProgress(console)
        return StreamJobStartProgress(console)

    def begin(self, job: JobDescription) -> None:
        # Quiet mode
        print(job.id)

    def step(self, job: JobDescription) -> None:
        pass

    def end(self, job: JobDescription) -> None:
        pass

    def _get_status_reason_message(self, job: JobDescription) -> str:
        if job.history.reason:
            return job.history.reason
        elif job.status == JobStatus.PENDING:
            return "Initializing"
        return ""

    def _get_status_description_message(self, job: JobDescription) -> str:
        description = job.history.description
        if description:
            return f"({description})"
        return ""

    def __enter__(self) -> "JobStartProgress":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        pass


def _add_columns(table: Table, columns: JobTableFormat) -> None:
    column = columns[0]
    table.add_column(
        column.title,
        style="bold",
        justify=column.justify,
        width=column.width,
        min_width=column.min_width,
        max_width=column.max_width,
    )
    for column in columns[1:]:
        table.add_column(
            column.title,
            justify=column.justify,
            width=column.width,
            min_width=column.min_width,
            max_width=column.max_width,
        )


class DetailedJobStartProgress(JobStartProgress, RenderHook):
    def __init__(self, console: Console) -> None:
        self._time = self.time_factory()
        self._prev = Text("")
        self._console = console
        self._spinner = SPINNER
        self._live_render = LiveRender(Text())

    def begin(self, job: JobDescription) -> None:
        self._console.print(
            f"{yes()} [b]Job ID[/b]: {rich_escape(job.id)}", markup=True
        )
        if job.name:
            self._console.print(
                f"{yes()} [b]Name[/b]: {rich_escape(job.name)}", markup=True
            )

    def step(self, job: JobDescription) -> None:
        new_time = self.time_factory()
        dt = new_time - self._time
        if job.status.is_pending:
            msg = Text("-", "yellow")
        elif job.status in (JobStatus.RUNNING, JobStatus.SUCCEEDED):
            msg = Text("√", "green")
        else:
            # FAILED or CANCELLED or UNKNOWN
            msg = Text("×", "red")

        msg = Text.assemble(msg, " Status: ", fmt_status(job.status))
        reason = self._get_status_reason_message(job)
        if reason:
            msg = Text.assemble(msg, " ", (reason, "b"))
        description = self._get_status_description_message(job)
        if description:
            msg = Text.assemble(msg, " " + description)

        if msg != self._prev:
            if self._prev:
                self._console.print(self._prev)
            self._prev = msg
        else:
            msg = Text.assemble(msg, f" {next(self._spinner)} [{dt:.1f} sec]")

        self._live_render.set_renderable(msg)
        with self._console:
            self._console.print(Control())

    def end(self, job: JobDescription) -> None:
        out = []

        if self._prev:
            self._console.print(self._prev)
            empty = Text("")
            self._prev = empty
            self._live_render.set_renderable(empty)

        if not job.status.is_finished:
            http_url = job.http_url
            if http_url:
                out.append(f"{yes()} [b]Http URL[/b]: {rich_escape(str(http_url))}")
            if job.life_span:
                limit = humanize.naturaldelta(datetime.timedelta(seconds=job.life_span))
                out.append(
                    f"{yes()} [yellow]The job will die in {limit}.[/yellow] "
                    "See --life-span option documentation for details.",
                )
            self._console.print("\n".join(out), markup=True)

    def process_renderables(
        self, renderables: list[ConsoleRenderable]
    ) -> list[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        if self._console.is_terminal:
            renderables = [
                self._live_render.position_cursor(),
                *renderables,
                self._live_render,
            ]
        return renderables

    def __enter__(self) -> "JobStartProgress":
        self._console.show_cursor(False)
        self._console.push_render_hook(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._console.pop_render_hook()
        self._console.line()
        self._console.show_cursor(True)


class StreamJobStartProgress(JobStartProgress):
    def __init__(self, console: Console) -> None:
        self._console = console
        self._prev = ""

    def begin(self, job: JobDescription) -> None:
        self._console.print(f"Job ID: {job.id}")
        if job.name:
            self._console.print(f"Name: {job.name}")

    def step(self, job: JobDescription) -> None:
        msg = f"Status: {job.status}"
        reason = self._get_status_reason_message(job)
        if reason:
            msg += " " + reason
        description = self._get_status_description_message(job)
        if description:
            msg += " " + description

        if job.status != JobStatus.PENDING:
            msg += "\n"

        if msg != self._prev:
            self._console.print(msg)
            self._prev = msg

    def end(self, job: JobDescription) -> None:
        pass


class JobStopProgress:
    TIMEOUT = 15 * 60
    time_factory = staticmethod(time.monotonic)

    @classmethod
    def create(cls, console: Console, quiet: bool) -> "JobStopProgress":
        if quiet:
            return JobStopProgress()
        elif console.is_terminal:
            return DetailedJobStopProgress(console)
        return StreamJobStopProgress(console)

    def __init__(self) -> None:
        self._time = self.time_factory()

    def kill(self, job: JobDescription) -> None:
        pass

    def detach(self, job: JobDescription) -> None:
        pass

    def step(self, job: JobDescription) -> bool:
        # return False if timeout, True otherwise
        new_time = self.time_factory()
        if new_time - self._time > self.TIMEOUT:
            self.timeout(job)
            return False
        else:
            self.tick(job)
            return True

    def tick(self, job: JobDescription) -> None:
        pass

    def end(self, job: JobDescription) -> None:
        pass

    def timeout(self, job: JobDescription) -> None:
        pass

    def __enter__(self) -> "JobStopProgress":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        pass


class DetailedJobStopProgress(JobStopProgress, RenderHook):
    def __init__(self, console: Console) -> None:
        super().__init__()
        self._console = console
        self._spinner = SPINNER
        self._live_render = LiveRender(Text())
        self._restarting = False

    def _hint(self, hints: Iterable[tuple[str, str]]) -> None:
        for title, hint in hints:
            self._console.print(f"{title}:", style="dim yellow")
            self._console.print(f"  {hint}", style="dim")

    def detach(self, job: JobDescription) -> None:
        self._console.line()
        self._console.print(
            f"{no()} [red]Terminal was detached but job is still running", markup=True
        )
        self._hint(
            [
                ("Re-attach to job", f"apolo attach {job.id}"),
                ("Check job status", f"apolo status {job.id}"),
                ("Kill job", f"apolo kill {job.id}"),
                ("Fetch job logs", f"apolo logs {job.id}"),
            ]
        )

    def kill(self, job: JobDescription) -> None:
        self._console.line()
        self._console.print(f"{no()} [red]Job was killed", markup=True)
        self._hint(
            [
                ("Get job status", f"apolo status {job.id}"),
                ("Fetch job logs", f"apolo logs {job.id}"),
            ]
        )

    def end(self, job: JobDescription) -> None:
        if job.status == JobStatus.RUNNING:
            msg = yes() + f" Job [b]{job.id}[/b] restarted"
        elif job.status == JobStatus.SUCCEEDED:
            msg = yes() + f" Job [b]{job.id}[/b] finished successfully"
        elif job.status == JobStatus.CANCELLED:
            msg = yes() + f" Job [b]{job.id}[/b] was cancelled"
            if job.history.reason:
                msg += f" ({rich_escape(job.history.reason)})"
        else:
            msg = no() + f" Job [b]{job.id}[/b] failed"
            if job.history.reason:
                msg += f" ({rich_escape(job.history.reason)})"

        self._live_render.set_renderable(Text.from_markup(msg))
        with self._console:
            self._console.print(Control())

    def tick(self, job: JobDescription) -> None:
        if job.history.reason == "Restarting":
            self._restarting = True
        new_time = self.time_factory()
        dt = new_time - self._time
        msg = (
            "[yellow]-[/yellow] "
            f"Wait for {'restart' if self._restarting else 'stop'}"
            f" {next(self._spinner)} [{dt:.1f} sec]"
        )
        self._live_render.set_renderable(Text.from_markup(msg))
        with self._console:
            self._console.print(Control())

    def timeout(self, job: JobDescription) -> None:
        self._console.line()
        self._console.print("[red]× Warning !!!", markup=True)
        self._console.print(
            f"{no()} [red]"
            "The attached session was disconnected but the job is still alive.",
            markup=True,
        )
        self._hint(
            [
                ("Reconnect to the job", f"apolo attach {job.id}"),
                ("Terminate the job", f"apolo kill {job.id}"),
            ]
        )

    def process_renderables(
        self, renderables: list[ConsoleRenderable]
    ) -> list[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        if self._console.is_terminal:
            renderables = [
                self._live_render.position_cursor(),
                *renderables,
                self._live_render,
            ]
        return renderables

    def __enter__(self) -> "JobStopProgress":
        self._console.show_cursor(False)
        self._console.push_render_hook(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._console.pop_render_hook()
        self._console.line()
        self._console.show_cursor(True)


class StreamJobStopProgress(JobStopProgress):
    def __init__(self, console: Console) -> None:
        super().__init__()
        self._console = console
        self._first = True
        self._restarting = False

    def detach(self, job: JobDescription) -> None:
        pass

    def kill(self, job: JobDescription) -> None:
        self._console.print("Job was killed")

    def end(self, job: JobDescription) -> None:
        if job.status == JobStatus.RUNNING:
            msg = "Job restarted"
            self._console.print(msg)
        elif job.status == JobStatus.CANCELLED:
            msg = "Job was cancelled"
            if job.history.reason:
                msg += f" ({job.history.reason})"
            self._console.print(msg)
        elif job.status == JobStatus.FAILED:
            msg = "Job failed"
            if job.history.reason:
                msg += f" ({job.history.reason})"
            self._console.print(msg)

    def tick(self, job: JobDescription) -> None:
        if not self._restarting and job.history.reason == "Restarting":
            self._restarting = True
            self._first = False
        if self._first:
            if self._restarting:
                self._console.print("Wait for restarting")
            else:
                self._console.print("Wait for stopping")
            self._first = False

    def timeout(self, job: JobDescription) -> None:
        self._console.print("")
        self._console.print("Warning !!!")
        self._console.print(
            "The attached session was disconnected but the job is still alive."
        )


class ExecStopProgress:
    TIMEOUT = 15
    time_factory = staticmethod(time.monotonic)

    @classmethod
    def create(cls, console: Console, quiet: bool, job_id: str) -> "ExecStopProgress":
        if quiet:
            return ExecStopProgress(job_id)
        elif console.is_terminal:
            return DetailedExecStopProgress(console, job_id)
        return StreamExecStopProgress(console, job_id)

    def __init__(self, job_id: str) -> None:
        self._time = self.time_factory()
        self._job_id = job_id

    def __call__(self, running: bool) -> bool:
        # return False if timeout, True otherwise
        new_time = self.time_factory()
        if new_time - self._time > self.TIMEOUT:
            self.timeout()
            return False
        else:
            self.tick(running)
            return True

    def tick(self, running: bool) -> None:
        pass

    def timeout(self) -> None:
        pass

    def __enter__(self) -> "ExecStopProgress":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        pass


class DetailedExecStopProgress(ExecStopProgress, RenderHook):
    def __init__(self, console: Console, job_id: str) -> None:
        super().__init__(job_id)
        self._console = console
        self._spinner = SPINNER
        self._live_render = LiveRender(Text())

    def tick(self, running: bool) -> None:
        new_time = self.time_factory()
        dt = new_time - self._time

        if running:
            msg = (
                "[yellow]-[/yellow]"
                + f"Wait for stopping {next(self._spinner)} [{dt:.1f} sec]"
            )
        else:
            msg = yes() + f" Job [b]{self._job_id}[/b] stopped"

        self._live_render.set_renderable(Text.from_markup(msg))
        with self._console:
            self._console.print(Control())

    def timeout(self) -> None:
        self._console.line()
        self._console.print(f"{no()} [red]Warning !!!", markup=True)
        self._console.print(
            f"{no()} [red]The attached session was disconnected "
            "but the exec process is still alive.",
            markup=True,
        )

    def process_renderables(
        self, renderables: list[ConsoleRenderable]
    ) -> list[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        if self._console.is_terminal:
            renderables = [
                self._live_render.position_cursor(),
                *renderables,
                self._live_render,
            ]
        return renderables

    def __enter__(self) -> "ExecStopProgress":
        self._console.show_cursor(False)
        self._console.push_render_hook(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._console.line()
        self._console.show_cursor(True)
        self._console.pop_render_hook()


class StreamExecStopProgress(ExecStopProgress):
    def __init__(self, console: Console, job_id: str) -> None:
        super().__init__(job_id)
        self._console = console
        self._console.print("Wait for stopping")

    def tick(self, running: bool) -> None:
        pass

    def timeout(self) -> None:
        self._console.print()
        self._console.print("Warning !!!")
        self._console.print(
            "The attached session was disconnected "
            "but the exec process is still alive."
        )
