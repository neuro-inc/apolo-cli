import datetime
from collections.abc import Callable
from typing import Protocol, overload

import humanize
from rich.console import Console, ConsoleOptions, RenderResult
from rich.progress import BarColumn, Task
from rich.progress_bar import ProgressBar
from rich.segment import Segment
from yarl import URL

from apolo_sdk import SCHEMES, Preset, RemoteImage, _ResourcePoolType

from apolo_cli.utils import format_size

NEWLINE_SEP = "\n"
GPU_MODEL_SEP = " x "

URIFormatter = Callable[[URL], str]
ImageFormatter = Callable[[RemoteImage], str]


class _NoColorProgressBar(ProgressBar):
    """Keep the uncompleted bar visible when Rich's NO_COLOR mode is active."""

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield from super().__rich_console__(console, options)

        if (
            not console.no_color
            or console.color_system is None
            or self.pulse
            or self.total is None
        ):
            return

        width = min(self.width or options.max_width, options.max_width)
        completed = min(self.total, max(0, self.completed))
        complete_halves = int(width * 2 * completed / self.total) if self.total else 0
        bar_count, half_bar_count = divmod(complete_halves, 2)
        remaining_width = width - bar_count - half_bar_count
        if remaining_width:
            ascii = options.legacy_windows or options.ascii_only
            bar = "-" if ascii else "━"
            if not half_bar_count and bar_count:
                yield Segment(" " if ascii else "╺")
                remaining_width -= 1
            yield Segment(bar * remaining_width)


class VisibleBarColumn(BarColumn):
    """A BarColumn that remains readable when color output is disabled."""

    def render(self, task: Task) -> ProgressBar:
        return _NoColorProgressBar(
            total=max(0, task.total) if task.total is not None else None,
            completed=max(0, task.completed),
            width=None if self.bar_width is None else max(1, self.bar_width),
            pulse=not task.started,
            animation_time=task.get_time(),
            style=self.style,
            complete_style=self.complete_style,
            finished_style=self.finished_style,
            pulse_style=self.pulse_style,
        )


def uri_formatter(
    project_name: str, cluster_name: str, org_name: str | None
) -> URIFormatter:
    def formatter(uri: URL) -> str:
        if uri.scheme in SCHEMES:
            if uri.host == cluster_name:
                assert uri.path[0] == "/"
                path = uri.path.lstrip("/")
                project_or_org, _, rest = path.partition("/")
                if org_name:
                    if project_or_org != org_name:
                        return str(uri)
                    path = rest
                    project, _, rest = path.partition("/")
                else:
                    project = project_or_org
                if project == project_name:
                    path = rest.lstrip("/")
                else:
                    path = "/" + path
                uri = URL.build(scheme=uri.scheme, path=path)
        return str(uri)

    return formatter


def image_formatter(uri_formatter: URIFormatter) -> ImageFormatter:
    def formatter(image: RemoteImage) -> str:
        image_str = str(image)
        if image_str.startswith("image://"):
            return uri_formatter(URL(image_str))
        else:
            return image_str

    return formatter


def format_timedelta(delta: datetime.timedelta) -> str:
    s = int(delta.total_seconds())
    if s < 0:
        raise ValueError(f"Invalid delta {delta}: expect non-negative total value")
    _sec_in_minute = 60
    _sec_in_hour = _sec_in_minute * 60
    _sec_in_day = _sec_in_hour * 24
    d, s = divmod(s, _sec_in_day)
    h, s = divmod(s, _sec_in_hour)
    m, s = divmod(s, _sec_in_minute)
    return "".join(
        [
            f"{d}d" if d else "",
            f"{h}h" if h else "",
            f"{m}m" if m else "",
            f"{s}s" if s else "",
        ]
    )


def format_datetime_iso(
    when: datetime.datetime | None, *, precise: bool = False
) -> str:
    if when is None:
        return ""
    return when.isoformat()


def format_datetime_human(
    when: datetime.datetime | None,
    *,
    precise: bool = False,
    timezone: datetime.timezone | None = None,
) -> str:
    """Humanizes the datetime

    When not in precise mode (precise=False), prints number of largest units
    for moments that are less then a day ago, and date just day otherwise:

    "32 seconds ago"
    "5 minutes ago"
    "11 hours age"
    "yesterday"
    "Jan 1"

    In precise mode (precise=True), prints two largest units for moments
    that are less then a day ago, and date with time otherwise:

    "32 seconds ago"
    "5 minutes and 22 seconds ago"
    "5 hours and 31 minutes ago"
    "yesterday at 14:22"
    "Jan 1 at 00:01"
    """
    if when is None:
        return ""
    assert when.tzinfo is not None
    delta = datetime.datetime.now(datetime.timezone.utc) - when
    if delta < datetime.timedelta(days=1):
        prefix = ""
        suffix = " ago"
        if delta != abs(delta):  # negative delta means lifespan ends in future
            prefix = "in "
            suffix = ""
        if precise:
            min_unit = "seconds"
            if abs(delta) > datetime.timedelta(hours=1):
                min_unit = "minutes"
            return (
                prefix
                + humanize.precisedelta(delta, minimum_unit=min_unit, format="%0.0f")
                + suffix
            )
        return prefix + humanize.naturaldelta(delta) + suffix
    else:
        when_local = when.astimezone(timezone)
        result = humanize.naturaldate(when_local)
        if precise:
            result = f"{result} at {when_local.strftime('%H:%M')} "
        return result


class DatetimeFormatter(Protocol):
    @overload
    def __call__(self, when: datetime.datetime | None) -> str: ...

    @overload
    def __call__(self, when: datetime.datetime | None, *, precise: bool) -> str: ...

    def __call__(
        self, when: datetime.datetime | None, *, precise: bool = True
    ) -> str: ...


def get_datetime_formatter(use_iso_format: bool) -> DatetimeFormatter:
    if use_iso_format:
        return format_datetime_iso
    return format_datetime_human


def yes() -> str:
    return "[green]√[/green]"


def no() -> str:
    return "[red]×[/red]"


def format_multiple_gpus(entity: _ResourcePoolType | Preset) -> str:
    """
    Constructs a GPU string from the provided `entity`.
    Each GPU make will be separated by a newline, e.g.:

    Nvidia: 10 x tesla
    Nvidia MIG: 2 x 1g.5gb 5GB
    AMD: 5 x instinct
    Intel: 1
    """
    gpus = []

    if nvidia_gpu := entity.nvidia_gpu:
        gpu = format_gpu_string(nvidia_gpu.count, nvidia_gpu.model, nvidia_gpu.memory)
        gpus.append(f"Nvidia: {gpu}")
    if entity.nvidia_migs:
        for key, value in entity.nvidia_migs.items():
            gpu = format_gpu_string(value.count, value.model or key, value.memory)
            gpus.append(f"Nvidia MIG: {gpu}")
    if amd_gpu := entity.amd_gpu:
        gpu = format_gpu_string(amd_gpu.count, amd_gpu.model, amd_gpu.memory)
        gpus.append(f"AMD: {gpu}")
    if intel_gpu := entity.intel_gpu:
        gpu = format_gpu_string(intel_gpu.count, intel_gpu.model, intel_gpu.memory)
        gpus.append(f"Intel: {gpu}")

    return NEWLINE_SEP.join(gpus)


def format_gpu_string(
    gpu_count: int, gpu_model: str | None, gpu_memory: int | None = None
) -> str:
    """
    Constructs a GPU string, applying a separator if a GPU model present, e.g.:
    1 x nvidia-tesla-k80
    """
    gpu = [str(gpu_count)]
    if gpu_model:
        if gpu_memory:
            gpu.append(f"{gpu_model} {format_size(gpu_memory)}")
        else:
            gpu.append(gpu_model)
    elif gpu_memory:
        gpu.append(format_size(gpu_memory))
    return GPU_MODEL_SEP.join(gpu)
