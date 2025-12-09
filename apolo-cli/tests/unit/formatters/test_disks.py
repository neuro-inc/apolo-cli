from datetime import timedelta
from typing import Any

import pytest
from dateutil.parser import isoparse

from apolo_sdk import Disk

from apolo_cli.formatters.disks import (
    DiskFormatter,
    DisksFormatter,
    SimpleDisksFormatter,
)
from apolo_cli.formatters.utils import format_datetime_human


def test_disk_formatter(rich_cmp: Any) -> None:
    disk = Disk(
        id="disk",
        name="test-disk",
        storage=int(11.93 * (1024**3)),
        owner="user",
        project_name="test-project",
        status=Disk.Status.READY,
        cluster_name="cluster",
        org_name="org",
        created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
        last_usage=isoparse("2017-04-04T12:28:59.759433+00:00"),
        timeout_unused=timedelta(days=1, hours=2, minutes=3, seconds=4),
    )
    fmtr = DiskFormatter(str, datetime_formatter=format_datetime_human)
    rich_cmp(fmtr(disk))


@pytest.fixture
def disks_list() -> list[Disk]:
    return [
        Disk(
            id="disk-1",
            storage=50 * (1024**3),
            owner="user",
            project_name="test-project",
            status=Disk.Status.PENDING,
            cluster_name="cluster",
            org_name="org",
            created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
            last_usage=isoparse("2017-03-08T12:28:59.759433+00:00"),
        ),
        Disk(
            id="disk-2",
            storage=50 * (1024**2),
            owner="user",
            project_name="another-project",
            status=Disk.Status.READY,
            cluster_name="cluster",
            org_name="org",
            created_at=isoparse("2017-04-04T12:28:59.759433+00:00"),
            timeout_unused=timedelta(days=2, hours=3, minutes=4, seconds=5),
        ),
        Disk(
            id="disk-3",
            storage=50 * (1024**1),
            owner="user",
            project_name="another-project",
            status=Disk.Status.READY,
            cluster_name="cluster",
            org_name="test-org",
            created_at=isoparse("2017-05-04T12:28:59.759433+00:00"),
        ),
        Disk(
            id="disk-4",
            storage=50,
            owner="user",
            project_name="test-project",
            status=Disk.Status.BROKEN,
            cluster_name="cluster",
            org_name="org",
            created_at=isoparse("2017-06-04T12:28:59.759433+00:00"),
        ),
    ]


def test_disks_formatter_simple(disks_list: list[Disk], rich_cmp: Any) -> None:
    fmtr = SimpleDisksFormatter()
    rich_cmp(fmtr(disks_list))


def test_disks_formatter_short(disks_list: list[Disk], rich_cmp: Any) -> None:
    fmtr = DisksFormatter(str, datetime_formatter=format_datetime_human)
    rich_cmp(fmtr(disks_list))


def test_disks_formatter_long(disks_list: list[Disk], rich_cmp: Any) -> None:
    fmtr = DisksFormatter(
        str, long_format=True, datetime_formatter=format_datetime_human
    )
    rich_cmp(fmtr(disks_list))
