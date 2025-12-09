import dataclasses
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import (
    Any,
    TypeVar,
)

import click
from rich.console import JustifyMethod

from apolo_sdk import JobDescription, JobStatus, JobTelemetry

_T = TypeVar("_T")


def parse_memory(memory: str) -> int:
    """Parse string expression i.e. 16M, 16MB, etc
    M = 1024 * 1024, MB = 1000 * 1000

    returns value in bytes"""

    # Mega, Giga, Tera, etc

    prefix_to_factor = {
        "": 1,
        # Binary
        "Ki": 2**10,
        "Mi": 2**20,
        "Gi": 2**30,
        "Ti": 2**40,
        "Pi": 2**50,
        # Decimal
        "k": 10**3,
        "M": 10**6,
        "G": 10**9,
        "T": 10**12,
        "P": 10**15,
    }

    value_error = ValueError(f"Unable parse value: {memory}")

    if not memory:
        raise value_error

    pattern = rf"""^
                   (?P<value>\d+)
                   (?P<prefix>{"|".join(prefix_to_factor.keys())})?
                   [bB]?
                $"""
    regex = re.compile(pattern, re.VERBOSE)
    match = regex.fullmatch(memory)

    if not match:
        raise value_error

    groups = match.groupdict()

    value = int(groups["value"])
    prefix = groups["prefix"] or ""

    return value * prefix_to_factor[prefix]


@dataclasses.dataclass(frozen=True)
class JobColumnInfo:
    id: str
    title: str
    justify: JustifyMethod = "default"
    width: int | None = None
    min_width: int | None = None
    max_width: int | None = None


JobTableFormat = list[JobColumnInfo]


# Note: please keep the help for format specs in sync with the following data
# structures.

PS_COLUMNS = [
    JobColumnInfo(
        "id", "ID", "left", width=len("job-28040560-2a21-428e-a7c0-44c809490b53")
    ),
    JobColumnInfo("name", "NAME", "left", max_width=40),
    JobColumnInfo("tags", "TAGS", "left", max_width=40),
    JobColumnInfo("status", "STATUS", "left", max_width=10),
    JobColumnInfo("when", "WHEN", "left", max_width=32),
    JobColumnInfo("created", "CREATED", "left", max_width=15),
    JobColumnInfo("started", "STARTED", "left", max_width=15),
    JobColumnInfo("finished", "FINISHED", "left", max_width=15),
    JobColumnInfo("image", "IMAGE", "left", max_width=40),
    JobColumnInfo("owner", "OWNER", "left", max_width=25),
    JobColumnInfo("cluster_name", "CLUSTER", "left", max_width=15),
    JobColumnInfo("org_name", "ORG", "left", max_width=15),
    JobColumnInfo("description", "DESCRIPTION", "left", max_width=50),
    JobColumnInfo("command", "COMMAND", "left", max_width=100),
    JobColumnInfo("life_span", "LIFE-SPAN", "left"),
    JobColumnInfo("workdir", "WORKDIR", "left"),
    JobColumnInfo("preset", "PRESET", "left"),
    JobColumnInfo("project_name", "PROJECT", "left", max_width=25),
]

PS_COLUMNS_DEFAULT_FORMAT = "id/name status/when image org_name/project_name command"

TOP_COLUMNS = PS_COLUMNS + [
    JobColumnInfo("cpu", "CPU", "right", width=15),
    JobColumnInfo("memory", "MEMORY (MB)", "right", width=15),
    JobColumnInfo("gpu", "GPU (%)", "right", width=15),
    JobColumnInfo("gpu_memory", "GPU_MEMORY (MB)", "right", width=15),
]

TOP_COLUMNS_DEFAULT_FORMAT = "id/name when cpu memory gpu gpu_memory"

PS_COLUMNS_MAP = {column.id: column for column in PS_COLUMNS}
TOP_COLUMNS_MAP = {column.id: column for column in TOP_COLUMNS}

COLUMNS_RE = re.compile(
    r"""
    (?P<id>\w+(?:/\w+)*)|
    (?:\{(?P<col>[^}]+)\})|
    (?P<sep>\s*(?:,\s*|\s))|
    (?P<miss>.)
    """,
    re.VERBOSE,
)
COLUMN_RE = re.compile(
    r"""
    (?P<id>\w+(?:/\w+)*)
    (?:
      (?:;align=(?P<align>\w+))|
      (?:;min=(?P<min>\w+))|
      (?:;max=(?P<max>\w+))|
      (?:;width=(?P<width>\w+))
    )*
    (?:;(?P<title>.+))?
    """,
    re.VERBOSE,
)


def _get_column(
    id: str, columns_map: dict[str, JobColumnInfo], fmt: str
) -> JobColumnInfo:
    column = columns_map.get(id)
    if column is None:
        for name in columns_map:
            if name.startswith(id):
                if column is not None:
                    variants = ", ".join(
                        name for name in columns_map if name.startswith(id)
                    )
                    raise ValueError(
                        f"Ambiguous column {id!r} in format {fmt!r};"
                        f" available variants: {variants}"
                    )
                column = columns_map[name]
        if column is None:
            raise ValueError(f"Unknown column {id!r} in format {fmt!r}")
    return column


def _get(
    dct: Mapping[str, str | None],
    name: str,
    fmt: str,
    converter: Callable[[str], _T],
    default: _T | None,
) -> _T | None:
    val = dct[name]
    if val is None:
        return default
    else:
        try:
            return converter(val)
        except ValueError:
            raise ValueError(f"Invalid property {name}: {val!r} of format {fmt!r}")


def _justify(arg: str) -> JustifyMethod:
    ALLOWED = ("left", "right", "center", "full")
    if arg not in ALLOWED:
        raise ValueError(f"Unknown align {arg}, allowed {ALLOWED}")
    return arg  # type: ignore


def _max_width(widths: Iterable[int | None], indent: int = 1) -> int | None:
    max_width: int | None = None
    for i, width in enumerate(widths):
        if width is not None:
            if i:
                width += indent
            if max_width is not None:
                max_width = max(max_width, width)
            else:
                max_width = width
    return max_width


def _parse_columns(
    fmt: str | None, columns_map: dict[str, JobColumnInfo], default_fmt: str
) -> JobTableFormat:
    # Column format is "{id[;field=val][;title]}",
    # columns are separated by commas or spaces
    # spaces in title are forbidden
    if not fmt:
        fmt = default_fmt
    ret = []
    for m1 in COLUMNS_RE.finditer(fmt):
        if m1.lastgroup == "sep":
            continue
        elif m1.lastgroup == "miss":
            raise ValueError(f"Invalid format {fmt!r}")
        elif m1.lastgroup == "col":
            column = m1.group("col")
        elif m1.lastgroup == "id":
            column = m1.group("id")
        else:
            continue
        m2 = COLUMN_RE.fullmatch(column)
        if m2 is None:
            raise ValueError(f"Invalid format {fmt!r}")
        groups = m2.groupdict()
        ids = groups["id"].lower()
        defaults = [_get_column(id, columns_map, fmt) for id in ids.split("/")]

        title = "/".join(column.title for column in defaults)
        title = _get(groups, "title", fmt, str, title)  # type: ignore
        assert title is not None

        justify: JustifyMethod = _get(
            groups,
            "align",
            fmt,
            _justify,
            defaults[0].justify,
        )  # type: ignore

        min_width = _max_width(column.min_width for column in defaults)
        max_width = _max_width(column.max_width for column in defaults)
        width = _max_width(column.width for column in defaults)

        min_width = _get(groups, "min", fmt, int, min_width)
        max_width = _get(groups, "max", fmt, int, max_width)
        width = _get(groups, "width", fmt, int, width)

        info = JobColumnInfo(
            id=ids,
            title=title,
            justify=justify,
            width=width,
            min_width=min_width,
            max_width=max_width,
        )
        ret.append(info)
    if not ret:
        raise ValueError(f"Invalid format {fmt!r}")
    return ret


def get_default_ps_columns() -> JobTableFormat:
    return parse_ps_columns(None)


def get_default_top_columns() -> JobTableFormat:
    return parse_top_columns(None)


def parse_ps_columns(fmt: str | None) -> JobTableFormat:
    return _parse_columns(fmt, PS_COLUMNS_MAP, PS_COLUMNS_DEFAULT_FORMAT)


def parse_top_columns(fmt: str | None) -> JobTableFormat:
    return _parse_columns(fmt, TOP_COLUMNS_MAP, TOP_COLUMNS_DEFAULT_FORMAT)


class InvertKey:
    def __init__(self, value: Any) -> None:
        self.value = Any

    def __lt__(self, other: Any) -> Any:
        return self.value > other.value

    def __gt__(self, other: Any) -> Any:
        return self.value < other.value

    def __le__(self, other: Any) -> Any:
        return self.value >= other.value

    def __ge__(self, other: Any) -> Any:
        return self.value <= other.value

    def __eq__(self, other: Any) -> Any:
        return self.value == other.value

    def __ne__(self, other: Any) -> Any:
        return self.value != other.value


JobTelemetryKeyFunc = Callable[[tuple[JobDescription, JobTelemetry]], Any]

JOB_STATUS_PRIORITIES = {status: i for i, status in enumerate(JobStatus)}
DATETIME_MIN = datetime.min.replace(tzinfo=timezone.utc)
INF = float("inf")

SORT_KEY_FUNCS: dict[str, JobTelemetryKeyFunc] = {
    # JobDescriptor attibutes
    "id": lambda item: item[0].id,
    "name": lambda item: item[0].name or "",
    "status": lambda item: JOB_STATUS_PRIORITIES[item[0].status],
    "created": lambda item: item[0].history.created_at or DATETIME_MIN,
    "started": lambda item: item[0].history.started_at or DATETIME_MIN,
    "finished": lambda item: item[0].history.finished_at or DATETIME_MIN,
    "when": lambda item: item[0].history.changed_at,
    "image": lambda item: str(item[0].container.image),
    "owner": lambda item: item[0].owner,
    "description": lambda item: item[0].description or "",
    "cluster_name": lambda item: item[0].cluster_name,
    "command": lambda item: item[0].container.command,
    "life_span": lambda item: item[0].life_span or INF,
    "workdir": lambda item: item[0].container.working_dir or "",
    "preset": lambda item: item[0].preset_name or "",
    "project_name": lambda item: item[0].project_name or "",
    # JobTelemetry attibutes
    "cpu": lambda item: -item[1].cpu,
    "memory": lambda item: -item[1].memory,
    "gpu": lambda item: -(item[1].gpu_duty_cycle or 0),
    "gpu_memory": lambda item: -(item[1].gpu_memory or 0),
}

SORT_KEY_NAMES = tuple(SORT_KEY_FUNCS)


def parse_sort_keys(fmt: str) -> list[tuple[JobTelemetryKeyFunc, bool]]:
    sort_keys: list[tuple[JobTelemetryKeyFunc, bool]] = []
    for keyname in fmt.split(","):
        keyname = keyname.strip()
        if keyname[:1] == "-":
            reverse = True
            keyname = keyname[1:]
        else:
            reverse = False

        try:
            keyfunc = SORT_KEY_FUNCS[keyname]
        except KeyError:
            raise ValueError(f"invalid sort key {keyname!r}") from None
        sort_keys.append((keyfunc, reverse))

    return sort_keys


REGEX_TIME_DELTA = re.compile(
    r"^((?P<d>\d+)d)?((?P<h>\d+)h)?((?P<m>\d+)m)?((?P<s>\d+)s)?$"
)


def parse_timedelta(value: str) -> timedelta:
    value = value.strip()
    err = f"Could not parse time delta '{value}'"
    if value == "":
        raise click.UsageError(f"{err}: Empty string not allowed")
    if value == "0":
        return timedelta(0)
    match = REGEX_TIME_DELTA.search(value)
    if match is None:
        raise click.UsageError(
            f"{err}: Should be like '1d2h3m4s' (some parts may be missing)."
        )
    return timedelta(
        days=int(match.group("d") or 0),
        hours=int(match.group("h") or 0),
        minutes=int(match.group("m") or 0),
        seconds=int(match.group("s") or 0),
    )


# Opposite to function above
def serialize_timedelta(value: timedelta) -> str:
    res = ""
    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600 % 24
    minutes = total_seconds // 60 % 60
    seconds = total_seconds % 60
    if value.days:
        res += f"{value.days}d"
    if hours:
        res += f"{hours}h"
    if minutes:
        res += f"{minutes}m"
    if seconds:
        res += f"{seconds}s"
    if res == "":
        res = "0"
    return res
