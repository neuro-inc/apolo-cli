import io
import time
from typing import Any

from rich.console import Console

from apolo_sdk import (
    ImageAttestation,
    ImageCommitFinished,
    ImageCommitStarted,
    ImageInfo,
    ImagePlatform,
    ImageProgressPull,
    ImageProgressPush,
    ImageProgressSave,
    ImageProgressStep,
    LocalImage,
    RemoteImage,
)

from apolo_cli.formatters.images import DockerImageProgress, ImageInfoFormatter

from tests.unit.conftest import NewConsole


class TestDockerImageProgress:
    def test_quiet_pull(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=True) as formatter:
            formatter.pull(
                ImageProgressPull(
                    RemoteImage.new_external_image(name="input"), LocalImage("output")
                )
            )
            rich_cmp(console, index=0)
            formatter.step(ImageProgressStep("message1", "layer1", "status", 1, 100))
            rich_cmp(console, index=1)

    def test_quiet_push(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=True) as formatter:
            formatter.push(
                ImageProgressPush(
                    LocalImage("output"), RemoteImage.new_external_image(name="input")
                )
            )
            rich_cmp(console, index=0)
            formatter.step(ImageProgressStep("message1", "layer1", "status", 1, 100))
            rich_cmp(console, index=1)

    def test_quiet_save(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=True) as formatter:
            formatter.save(
                ImageProgressSave(
                    "job-id", RemoteImage.new_external_image(name="output")
                )
            )
            rich_cmp(console)

    def test_quiet_commit_started(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=True) as formatter:
            formatter.commit_started(
                ImageCommitStarted(
                    job_id="job-id", target_image=RemoteImage.new_external_image("img")
                )
            )
            rich_cmp(console)

    def test_quiet_commit_finished(
        self, rich_cmp: Any, new_console: NewConsole
    ) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=True) as formatter:
            formatter.commit_finished(ImageCommitFinished(job_id="job-id"))
            rich_cmp(console)

    def test_no_tty_pull(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=False)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.pull(
                ImageProgressPull(
                    RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                    LocalImage("input", "latest"),
                )
            )
            rich_cmp(console, index=0)
            formatter.step(ImageProgressStep("message1", "layer1", "status1", 1, 100))
            rich_cmp(console, index=1)
            formatter.step(ImageProgressStep("message2", "layer1", "status2", 30, 100))
            rich_cmp(console, index=2)

    def test_no_tty_pull_platforms(self, new_console: NewConsole) -> None:
        console = new_console(tty=False, color=False)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.step(
                ImageProgressStep("Platform linux/amd64", "", "", None, None)
            )
            formatter.step(ImageProgressStep("message1", "layer1", "status1", 1, 100))
            formatter.step(ImageProgressStep("message2", "layer2", "status1", 1, 100))
            formatter.step(
                ImageProgressStep("Platform linux/arm64", "", "", None, None)
            )
            formatter.step(ImageProgressStep("message3", "layer3", "status1", 1, 100))
        assert console.export_text() == (
            "Platform linux/amd64\n..\nPlatform linux/arm64\n.\n"
        )

    def test_no_tty_push(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=False)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.push(
                ImageProgressPush(
                    LocalImage("input", "latest"),
                    RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                )
            )
            rich_cmp(console, index=0)
            formatter.step(ImageProgressStep("message1", "layer1", "status1", 1, 100))
            rich_cmp(console, index=1)
            formatter.step(ImageProgressStep("message2", "layer1", "status2", 30, 100))
            rich_cmp(console, index=2)

    def test_no_tty_save(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=False)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.save(
                ImageProgressSave(
                    "job-id",
                    RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                )
            )
            rich_cmp(console)

    def test_no_tty_commit_started(
        self, rich_cmp: Any, new_console: NewConsole
    ) -> None:
        console = new_console(tty=False)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.commit_started(
                ImageCommitStarted(
                    job_id="job-id",
                    target_image=RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                )
            )
            rich_cmp(console)

    def test_no_tty_commit_finished(
        self, rich_cmp: Any, new_console: NewConsole
    ) -> None:
        console = new_console(tty=False)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.commit_finished(ImageCommitFinished(job_id="job-id"))
            rich_cmp(console)

    def test_tty_pull(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.pull(
                ImageProgressPull(
                    RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                    LocalImage("input", "latest"),
                )
            )
            rich_cmp(console, index=0)
            formatter.step(ImageProgressStep("message1", "layer1", "status1", 1, 100))
            time.sleep(0.3)
            rich_cmp(console, index=1)
            formatter.step(ImageProgressStep("message2", "layer1", "status2", 30, 100))
            time.sleep(0.3)
            rich_cmp(console, index=2)

    def test_tty_push(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.push(
                ImageProgressPush(
                    LocalImage("input", "latest"),
                    RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                )
            )
            rich_cmp(console, index=0)
            formatter.step(ImageProgressStep("message1", "layer1", "status1", 1, 100))
            time.sleep(0.3)
            rich_cmp(console, index=1)
            formatter.step(ImageProgressStep("message2", "layer1", "status2", 30, 100))
            time.sleep(0.3)
            rich_cmp(console, index=2)

    def test_tty_save(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.save(
                ImageProgressSave(
                    "job-id",
                    RemoteImage.new_platform_image(
                        name="output",
                        tag="stream",
                        registry="https://registry-api.dev.apolo.us",
                        cluster_name="test-cluster",
                        org_name=None,
                        project_name="test-project",
                    ),
                )
            )
            rich_cmp(console)

    def test_tty_commit_started(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.commit_started(
                ImageCommitStarted(
                    job_id="job-id",
                    target_image=RemoteImage.new_external_image(name="img"),
                )
            )
            rich_cmp(console)

    def test_tty_commit_finished(self, rich_cmp: Any, new_console: NewConsole) -> None:
        console = new_console(tty=True)
        with DockerImageProgress.create(console, quiet=False) as formatter:
            formatter.commit_finished(ImageCommitFinished(job_id="job-id"))
            rich_cmp(console)


class TestImageInfoFormatter:
    image = RemoteImage.new_platform_image(
        name="test",
        tag="v1",
        cluster_name="default",
        registry="reg",
        org_name="org",
        project_name="project",
    )

    def test_index(self, rich_cmp: Any) -> None:
        info = ImageInfo(
            name="v1",
            digest="sha256:index",
            media_type="application/vnd.oci.image.index.v1+json",
            size=7722744,
            platforms=[
                ImagePlatform(
                    digest="sha256:amd64", platform="linux/amd64", size=3630425
                ),
                ImagePlatform(
                    digest="sha256:arm64", platform="linux/arm64", size=4092423
                ),
            ],
            attestations=[
                ImageAttestation(
                    digest="sha256:attestation-amd64",
                    type="attestation-manifest",
                    reference_digest="sha256:amd64",
                    predicate_types=[
                        "https://spdx.dev/Document",
                        "https://slsa.dev/provenance/v1",
                    ],
                    size=84783,
                ),
                ImageAttestation(
                    digest="sha256:signature",
                    type="application/vnd.dev.sigstore.bundle+json",
                    reference_digest="sha256:index",
                    predicate_types=[],
                    size=300,
                ),
                ImageAttestation(
                    digest="sha256:unknown",
                    type=None,
                    reference_digest=None,
                    predicate_types=[],
                    size=0,
                ),
            ],
        )
        rich_cmp(ImageInfoFormatter()(self.image, info))

    def test_narrow_terminal(self) -> None:
        digest = "sha256:" + "a" * 64
        info = ImageInfo(
            name="v1",
            digest=digest,
            media_type="application/vnd.oci.image.index.v1+json",
            size=1,
            platforms=[ImagePlatform(digest=digest, platform="linux/amd64", size=1)],
            attestations=[
                ImageAttestation(
                    digest=digest,
                    type="attestation-manifest",
                    reference_digest=digest,
                    predicate_types=["https://slsa.dev/provenance/v1"],
                    size=1,
                )
            ],
        )
        file = io.StringIO()
        console = Console(file=file, width=80, color_system=None)
        console.print(ImageInfoFormatter()(self.image, info))
        assert "…" not in file.getvalue()

    def test_manifest(self, rich_cmp: Any) -> None:
        info = ImageInfo(
            name="v1",
            digest="sha256:manifest",
            media_type="application/vnd.docker.distribution.manifest.v2+json",
            size=32890532,
            platforms=[
                ImagePlatform(digest="sha256:manifest", platform=None, size=32890532)
            ],
            attestations=[],
        )
        rich_cmp(ImageInfoFormatter()(self.image, info))
