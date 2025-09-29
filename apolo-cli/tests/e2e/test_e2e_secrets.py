import uuid
from pathlib import Path
from typing import Any

import pytest

from tests.e2e.conftest import Helper


@pytest.fixture
def secret_name() -> str:
    return "secret" + str(uuid.uuid4()).replace("-", "")[:10]


@pytest.mark.e2e
def test_create_list_delete(helper: Helper, secret_name: str) -> None:
    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out

    cap = helper.run_cli(["secret", "add", secret_name, "value"])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name in cap.out

    cap = helper.run_cli(["secret", "rm", secret_name])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out


@pytest.mark.e2e
def test_create_get_delete(helper: Helper, secret_name: str) -> None:
    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out

    cap = helper.run_cli(["secret", "add", secret_name, "test_value"])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "get", secret_name])
    assert cap.err == ""
    assert cap.out == "test_value"

    cap = helper.run_cli(["secret", "rm", secret_name])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out


@pytest.mark.e2e
def test_create_from_file_get_delete(
    request: Any, helper: Helper, secret_name: str
) -> None:
    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out

    secret_path = Path(f"~/test-secret-file-{uuid.uuid4()}")
    output_path = Path(f"~/test-secret-output-{uuid.uuid4()}")
    request.addfinalizer(
        lambda: (
            secret_path.expanduser().unlink()
            if secret_path.expanduser().exists()
            else None
        )
    )
    request.addfinalizer(
        lambda: (
            output_path.expanduser().unlink()
            if output_path.expanduser().exists()
            else None
        )
    )

    secret_path.expanduser().write_bytes(b"value\xff\x00")
    cap = helper.run_cli(["secret", "add", secret_name, f"@{secret_path}"])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "get", secret_name, "--file", str(output_path)])
    assert cap.err == ""
    assert output_path.expanduser().read_bytes() == b"value\xff\x00"

    cap = helper.run_cli(["secret", "rm", secret_name])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out


@pytest.mark.e2e
def test_create_from_file_list_delete(
    request: Any, helper: Helper, secret_name: str
) -> None:
    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out

    secret_path = Path(f"~/test-secret-file-{uuid.uuid4()}")
    request.addfinalizer(secret_path.expanduser().unlink)
    secret_path.expanduser().write_bytes(b"value\xff\x00")
    cap = helper.run_cli(["secret", "add", secret_name, f"@{secret_path}"])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name in cap.out

    cap = helper.run_cli(["secret", "rm", secret_name])
    assert cap.err == ""

    cap = helper.run_cli(["secret", "ls"])
    assert cap.err == ""
    assert secret_name not in cap.out
