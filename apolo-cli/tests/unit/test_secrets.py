import pathlib
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from apolo_cli.secrets import get, read_data


def test_read_data_str() -> None:
    assert b"value" == read_data("value")


def test_read_data_file(tmp_path: pathlib.Path) -> None:
    fname = tmp_path / "secret.txt"
    fname.write_bytes(b"file content")
    assert b"file content" == read_data("@" + str(fname))


def test_secret_get_text_output(root: Any) -> None:
    runner = CliRunner()
    root.client.secrets.get = AsyncMock(return_value=b"secret_value")

    result = runner.invoke(get, ["test_key"], obj=root)

    assert result.exit_code == 0
    assert result.output == "secret_value"
    root.client.secrets.get.assert_called_once_with(
        "test_key", cluster_name=None, org_name=None, project_name=None
    )


def test_secret_get_binary_output_to_file(root: Any, tmp_path: pathlib.Path) -> None:
    runner = CliRunner()
    root.client.secrets.get = AsyncMock(return_value=b"\xff\x00binary_data")

    output_file = tmp_path / "output.bin"
    result = runner.invoke(get, ["test_key", "--file", str(output_file)], obj=root)

    assert result.exit_code == 0
    assert output_file.read_bytes() == b"\xff\x00binary_data"
    assert "Secret 'test_key' saved to" in result.output
    root.client.secrets.get.assert_called_once_with(
        "test_key", cluster_name=None, org_name=None, project_name=None
    )


def test_secret_get_binary_output_to_stdout_quiet(root: Any) -> None:
    runner = CliRunner()
    root.verbosity = -1
    root.client.secrets.get = AsyncMock(return_value=b"\xff\x00binary_data")

    with pytest.raises(UnicodeDecodeError):
        runner.invoke(get, ["test_key"], obj=root, catch_exceptions=False)


def test_secret_get_basic(root: Any) -> None:
    runner = CliRunner()
    root.client.secrets.get = AsyncMock(return_value=b"secret_value")

    result = runner.invoke(get, ["test_key"], obj=root)

    assert result.exit_code == 0
    assert result.output == "secret_value"
    root.client.secrets.get.assert_called_once_with(
        "test_key",
        cluster_name=None,
        org_name=None,
        project_name=None,
    )
