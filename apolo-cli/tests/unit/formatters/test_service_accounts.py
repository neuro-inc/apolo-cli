from typing import Any

import pytest
from dateutil.parser import isoparse

from apolo_sdk import ServiceAccount

from apolo_cli.formatters.service_accounts import (
    ServiceAccountFormatter,
    ServiceAccountsFormatter,
    SimpleServiceAccountsFormatter,
)
from apolo_cli.formatters.utils import format_datetime_human


@pytest.mark.parametrize(
    "org",
    [None, "some-org"],
)
def test_service_account_formatter(rich_cmp: Any, org: Any) -> None:
    account = ServiceAccount(
        id="account",
        name="test1",
        role="test-role",
        owner="user",
        default_cluster="cluster",
        default_project="some-project",
        default_org=org,
        created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
    )
    fmtr = ServiceAccountFormatter(datetime_formatter=format_datetime_human)
    rich_cmp(fmtr(account))


@pytest.fixture
def service_accounts_list() -> list[ServiceAccount]:
    return [
        ServiceAccount(
            id="account-1",
            name="test1",
            role="test-role",
            owner="user",
            default_cluster="cluster",
            default_project="test-project",
            created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
        ),
        ServiceAccount(
            id="account-2",
            name="test2",
            role="test-role",
            owner="user",
            default_cluster="cluster",
            default_project="test-project",
            created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
        ),
        ServiceAccount(
            id="account-3",
            name="test3",
            role="test-role",
            owner="user",
            default_cluster="cluster",
            default_project="test-project",
            created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
        ),
        ServiceAccount(
            id="account-4",
            name="test4",
            role="test-role",
            owner="user",
            default_cluster="cluster",
            default_project="test-project",
            created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
        ),
    ]


def test_service_accounts_formatter_simple(
    service_accounts_list: list[ServiceAccount], rich_cmp: Any
) -> None:
    fmtr = SimpleServiceAccountsFormatter()
    rich_cmp(fmtr(service_accounts_list))


def test_disks_formatter(
    service_accounts_list: list[ServiceAccount], rich_cmp: Any
) -> None:
    fmtr = ServiceAccountsFormatter(datetime_formatter=format_datetime_human)
    rich_cmp(fmtr(service_accounts_list))
