from typing import Any
from unittest.mock import ANY, AsyncMock

from click.testing import CliRunner

from apolo_sdk import LocalImage

from apolo_cli.image import pull


def test_pull_platform(root: Any) -> None:
    runner = CliRunner()
    local = LocalImage(name="alpine", tag="latest")
    root.client.images.pull = AsyncMock(return_value=local)

    result = runner.invoke(
        pull, ["--platform", "linux/amd64", "image:alpine:latest"], obj=root
    )

    assert result.exit_code == 0, result.output
    root.client.images.pull.assert_called_once_with(
        root.client.parse.remote_image("image:alpine:latest"),
        None,
        progress=ANY,
        platform="linux/amd64",
    )


def test_pull_default_platform(root: Any) -> None:
    runner = CliRunner()
    local = LocalImage(name="alpine", tag="latest")
    root.client.images.pull = AsyncMock(return_value=local)

    result = runner.invoke(pull, ["image:alpine:latest"], obj=root)

    assert result.exit_code == 0, result.output
    root.client.images.pull.assert_called_once_with(
        root.client.parse.remote_image("image:alpine:latest"),
        None,
        progress=ANY,
        platform=None,
    )
