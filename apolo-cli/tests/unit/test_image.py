from dataclasses import replace
from typing import Any
from unittest.mock import ANY, AsyncMock

from click.testing import CliRunner

from apolo_sdk import (
    ImageAttestation,
    ImageInfo,
    ImagePlatform,
    LocalImage,
    Tag,
    TagOption,
)

from apolo_cli.image import inspect, pull, tags


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
        all_platforms=False,
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
        all_platforms=False,
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
        all_platforms=False,
    )


def test_pull_all_platforms(root: Any) -> None:
    runner = CliRunner()
    local = LocalImage(name="alpine", tag="latest")
    root.client.images.pull = AsyncMock(return_value=local)

    result = runner.invoke(pull, ["--all-platforms", "image:alpine"], obj=root)

    assert result.exit_code == 0, result.output
    root.client.images.pull.assert_called_once_with(
        root.client.parse.remote_image("image:alpine"),
        None,
        progress=ANY,
        platform=None,
        all_platforms=True,
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


def test_inspect(root: Any) -> None:
    runner = CliRunner()
    root.client.images.inspect = AsyncMock(
        return_value=ImageInfo(
            name="v1",
            digest="sha256:index",
            media_type="application/vnd.oci.image.index.v1+json",
            size=3000,
            platforms=[
                ImagePlatform(digest="sha256:amd64", platform="linux/amd64", size=1000),
                ImagePlatform(digest="sha256:arm64", platform="linux/arm64", size=2000),
            ],
            attestations=[
                ImageAttestation(
                    digest="sha256:attestation",
                    type="attestation-manifest",
                    reference_digest="sha256:arm64",
                    predicate_types=["https://slsa.dev/provenance/v1"],
                    size=500,
                )
            ],
        )
    )

    result = runner.invoke(inspect, ["image:alpine:v1"], obj=root)

    assert result.exit_code == 0, result.output
    root.client.images.inspect.assert_called_once_with(
        root.client.parse.remote_image("image:alpine:v1")
    )
    rows = [line.split() for line in result.output.splitlines()]
    assert ["Digest", "sha256:index"] in rows
    assert ["linux/amd64", "sha256:amd64", "1.0", "kB"] in rows
    assert [
        "attestation-manifest",
        "linux/arm64",
        "https://slsa.dev/provenance/v1",
        "sha256:attestation",
        "500",
        "Bytes",
    ] in rows


def test_tags_long_zero_size(root: Any) -> None:
    runner = CliRunner()
    image = root.client.parse.remote_image("image:alpine", tag_option=TagOption.DENY)
    root.client.images.tags = AsyncMock(return_value=[replace(image, tag="sha256-abc")])
    root.client.images.tag_info = AsyncMock(return_value=Tag(name="sha256-abc", size=0))

    result = runner.invoke(tags, ["-l", "image:alpine"], obj=root)

    assert result.exit_code == 0, result.output
    assert ["sha256-abc", "0", "Bytes"] in [
        line.split() for line in result.output.splitlines()
    ]
