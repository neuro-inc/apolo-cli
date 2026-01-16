from typing import Any

from dateutil.parser import isoparse

from apolo_sdk import KubeServiceAccount

from apolo_cli.formatters.utils import format_datetime_iso
from apolo_cli.formatters.vcluster import (
    KubeConfigFormatter,
    SimpleKubeConfigFormatter,
)


def test_simple_kube_formatter(rich_cmp: Any) -> None:
    sa1 = KubeServiceAccount(
        user="user",
        name="name-1",
        created_at=isoparse("2026-01-08T12:28:59.759433+00:00"),
        expired_at=isoparse("2027-01-08T12:28:59.759433+00:00"),
    )
    sa2 = KubeServiceAccount(
        user="user",
        name="name-2",
        created_at=isoparse("2026-01-08T18:28:59.123456+00:00"),
        expired_at=isoparse("2027-01-08T18:28:59.123456+00:00"),
    )
    fmtr = SimpleKubeConfigFormatter()
    rich_cmp(fmtr([sa1, sa2]))


def test_kube_formatter(rich_cmp: Any) -> None:
    sa1 = KubeServiceAccount(
        user="user",
        name="name-1",
        created_at=isoparse("2026-01-08T12:28:59.759433+00:00"),
        expired_at=isoparse("2027-01-08T12:28:59.759433+00:00"),
    )
    sa2 = KubeServiceAccount(
        user="user",
        name="name-2",
        created_at=isoparse("2026-01-08T18:28:59.123456+00:00"),
        expired_at=isoparse("2027-01-08T18:28:59.123456+00:00"),
    )
    fmtr = KubeConfigFormatter(datetime_formatter=format_datetime_iso)
    rich_cmp(fmtr([sa1, sa2]))
