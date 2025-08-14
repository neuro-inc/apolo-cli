import datetime
from typing import Callable, Optional, Protocol, Union, overload

import humanize
from yarl import URL

from apolo_sdk import SCHEMES, Preset, RemoteImage, _ResourcePoolType

from apolo_cli.utils import format_size

NEWLINE_SEP = "\n"
GPU_MODEL_SEP = " x "

URIFormatter = Callable[[URL], str]
ImageFormatter = Callable[[RemoteImage], str]


def uri_formatter(
    project_name: str, cluster_name: str, org_name: Optional[str]
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
    when: Optional[datetime.datetime], *, precise: bool = False
) -> str:
    if when is None:
        return ""
    return when.isoformat()


def format_datetime_human(
    when: Optional[datetime.datetime],
    *,
    precise: bool = False,
    timezone: Optional[datetime.timezone] = None,
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
    def __call__(self, when: Optional[datetime.datetime]) -> str: ...

    @overload
    def __call__(self, when: Optional[datetime.datetime], *, precise: bool) -> str: ...

    def __call__(
        self, when: Optional[datetime.datetime], *, precise: bool = True
    ) -> str: ...


def get_datetime_formatter(use_iso_format: bool) -> DatetimeFormatter:
    if use_iso_format:
        return format_datetime_iso
    return format_datetime_human


def yes() -> str:
    return "[green]√[/green]"


def no() -> str:
    return "[red]×[/red]"


def format_multiple_gpus(entity: Union[_ResourcePoolType, Preset]) -> str:
    """
    Constructs a GPU string from the provided `entity`.
    Each GPU make will be separated by a newline, e.g.:

    Nvidia: 10 x tesla
    AMD: 5 x instinct
    Intel: 1
    """
    gpus = []
    for gpu_make, gpu in (
        ("Nvidia", entity.nvidia_gpu),
        ("AMD", entity.amd_gpu),
        ("Intel", entity.intel_gpu),
    ):
        if not gpu:
            continue
        gpus.append(
            f"{gpu_make}: {format_gpu_string(gpu.count, gpu.model, gpu.memory)}"
        )

    return NEWLINE_SEP.join(gpus)


def format_gpu_string(
    gpu_count: int, gpu_model: Optional[str], gpu_memory: Optional[int] = None
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
