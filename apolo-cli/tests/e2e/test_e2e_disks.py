from collections.abc import Callable
from typing import ContextManager

import pytest

from tests.e2e.conftest import Helper


@pytest.mark.e2e
def test_create_get_list_delete(
    helper: Helper, disk_factory: Callable[[str], ContextManager[str]]
) -> None:
    cap = helper.run_cli(["disk", "ls"])
    assert cap.err == ""

    with disk_factory("2GB") as disk_id:
        cap = helper.run_cli(["disk", "ls"])
        assert cap.err == ""
        assert disk_id in cap.out

        cap = helper.run_cli(["-q", "disk", "ls"])
        assert cap.err == ""
        assert disk_id in cap.out.splitlines()

        cap = helper.run_cli(["disk", "get", disk_id])
        assert cap.err == ""
        assert disk_id in cap.out
        assert "2.0 GB" in cap.out

    cap = helper.run_cli(["disk", "ls"])
    assert cap.err == ""
    assert disk_id not in cap.out


@pytest.mark.e2e
def test_delete_multiple_disks(
    helper: Helper, disk_factory: Callable[[str], ContextManager[str]]
) -> None:
    disk_id_1: str | None = None
    disk_id_2: str | None = None
    try:
        cap = helper.run_cli(["disk", "create", "1GB"])
        assert cap.err == ""
        disk_id_1 = cap.out.splitlines()[0].split()[1]

        cap = helper.run_cli(["disk", "create", "1GB"])
        assert cap.err == ""
        disk_id_2 = cap.out.splitlines()[0].split()[1]

        assert disk_id_1
        assert disk_id_2
        cap = helper.run_cli(["disk", "rm", disk_id_1, disk_id_2])
        assert cap.err == ""

        cap = helper.run_cli(["disk", "ls"])
        assert cap.err == ""
        assert disk_id_1 not in cap.out
        assert disk_id_2 not in cap.out

    except Exception as e:
        try:
            if disk_id_2 is not None:
                helper.run_cli(["disk", "rm", disk_id_2])
        finally:
            if disk_id_1 is not None:
                helper.run_cli(["disk", "rm", disk_id_1])
        raise e
