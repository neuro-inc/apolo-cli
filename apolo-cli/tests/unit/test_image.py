from typing import Any
from unittest.mock import ANY, AsyncMock

from click.testing import CliRunner

from apolo_sdk import ImageInfo, ImagePlatform, LocalImage

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
        platform=("linux/amd64",),
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


def test_pull_several_platforms(root: Any) -> None:
    runner = CliRunner()
    local = LocalImage(name="alpine", tag="latest")
    root.client.images.pull = AsyncMock(return_value=local)

    result = runner.invoke(
        pull,
        ["--platform", "linux/amd64", "--platform", "linux/arm64", "image:alpine"],
        obj=root,
    )

    assert result.exit_code == 0, result.output
    root.client.images.pull.assert_called_once_with(
        root.client.parse.remote_image("image:alpine"),
        None,
        progress=ANY,
        platform=("linux/amd64", "linux/arm64"),
    )


def test_pull_all_platforms(root: Any) -> None:
    runner = CliRunner()
    local = LocalImage(name="alpine", tag="latest")
    root.client.images.pull = AsyncMock(return_value=local)
    root.client.images.inspect = AsyncMock(
        return_value=ImageInfo(
            name="latest",
            digest="sha256:index",
            media_type="application/vnd.oci.image.index.v1+json",
            size=3,
            platforms=[
                ImagePlatform(digest="sha256:amd64", platform="linux/amd64", size=1),
                ImagePlatform(digest="sha256:arm64", platform="linux/arm64", size=2),
            ],
            attestations=[],
        )
    )

    result = runner.invoke(pull, ["--all-platforms", "image:alpine"], obj=root)

    assert result.exit_code == 0, result.output
    remote = root.client.parse.remote_image("image:alpine")
    root.client.images.inspect.assert_called_once_with(remote)
    root.client.images.pull.assert_called_once_with(
        remote,
        None,
        progress=ANY,
        platform=["linux/amd64", "linux/arm64"],
    )


def test_pull_all_platforms_single_manifest(root: Any) -> None:
    runner = CliRunner()
    local = LocalImage(name="alpine", tag="latest")
    root.client.images.pull = AsyncMock(return_value=local)
    root.client.images.inspect = AsyncMock(
        return_value=ImageInfo(
            name="latest",
            digest="sha256:manifest",
            media_type="application/vnd.oci.image.manifest.v1+json",
            size=1,
            platforms=[ImagePlatform(digest="sha256:manifest", platform=None, size=1)],
            attestations=[],
        )
    )

    result = runner.invoke(pull, ["--all-platforms", "image:alpine"], obj=root)

    assert result.exit_code == 0, result.output
    root.client.images.pull.assert_called_once_with(
        root.client.parse.remote_image("image:alpine"),
        None,
        progress=ANY,
        platform=None,
    )


def test_pull_platform_and_all_platforms(root: Any) -> None:
    runner = CliRunner()
    root.client.images.pull = AsyncMock()

    result = runner.invoke(
        pull,
        ["--all-platforms", "--platform", "linux/amd64", "image:alpine"],
        obj=root,
    )

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output
    root.client.images.pull.assert_not_called()
