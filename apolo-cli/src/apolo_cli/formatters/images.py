import abc
from collections.abc import Iterable
from types import TracebackType

from rich import box
from rich.console import Console, Group, RenderableType
from rich.progress import DownloadColumn, Progress, TaskID, TextColumn
from rich.table import Table
from rich.text import Text

from apolo_sdk import (
    AbstractDockerImageProgress,
    ImageCommitFinished,
    ImageCommitStarted,
    ImageInfo,
    ImageProgressPull,
    ImageProgressPush,
    ImageProgressSave,
    ImageProgressStep,
    RemoteImage,
    Tag,
)

from ..utils import format_size
from .utils import ImageFormatter, VisibleBarColumn


class DockerImageProgress(AbstractDockerImageProgress):
    @classmethod
    def create(cls, console: Console, quiet: bool) -> "DockerImageProgress":
        if quiet:
            progress: DockerImageProgress = QuietDockerImageProgress()
        elif console.is_terminal:
            progress = DetailedDockerImageProgress(console)
        else:
            progress = StreamDockerImageProgress(console)
        return progress

    @abc.abstractmethod
    def close(self) -> None:  # pragma: no cover
        pass

    def __enter__(self) -> "DockerImageProgress":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.close()

    def _shorten_container_hash(self, container: str) -> str:
        return container[:12]


class QuietDockerImageProgress(DockerImageProgress):
    def pull(self, data: ImageProgressPull) -> None:
        pass

    def push(self, data: ImageProgressPush) -> None:
        pass

    def step(self, data: ImageProgressStep) -> None:
        pass

    def close(self) -> None:
        pass

    def save(self, data: ImageProgressSave) -> None:
        pass

    def commit_started(self, data: ImageCommitStarted) -> None:
        pass

    def commit_finished(self, data: ImageCommitFinished) -> None:
        pass


class DetailedDockerImageProgress(DockerImageProgress):
    def __init__(self, console: Console) -> None:
        self._mapping: dict[str, TaskID] = {}
        self._progress = Progress(
            TextColumn("[progress.description]{task.fields[layer]}"),
            TextColumn("[progress.description]{task.description}"),
            VisibleBarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            console=console,
            auto_refresh=False,
        )
        self._progress.start()

    def push(self, data: ImageProgressPush) -> None:
        self._progress.log(
            Text.assemble(
                "Pushing image ",
                Text(str(data.src), style="b"),
                " => ",
                Text(str(data.dst), style="b"),
            )
        )

    def pull(self, data: ImageProgressPull) -> None:
        self._progress.log(
            Text.assemble(
                "Pulling image ",
                Text(str(data.src), style="b"),
                " => ",
                Text(str(data.dst), style="b"),
            )
        )

    def step(self, data: ImageProgressStep) -> None:
        if data.layer_id:
            if data.status in ("Layer already exists", "Download complete"):
                current: float | None = 100.0
                total: float | None = 100.0
            else:
                current = float(data.current) if data.current is not None else None
                total = float(data.total) if data.total is not None else None

            layer = data.layer_id
            if layer in self._mapping.keys():
                task = self._mapping[layer]
                self._progress.update(
                    task,
                    description=data.status,
                    completed=current,
                    total=total,
                    refresh=True,
                )
            else:
                task = self._progress.add_task(
                    layer=layer,
                    description=data.status,
                    completed=current or 0,  # type: ignore
                    total=total or 100,
                )
                self._mapping[layer] = task

        else:
            self._progress.log(data.message)

    def save(self, data: ImageProgressSave) -> None:
        self._progress.log(
            Text.assemble(
                "Saving ",
                Text(data.job, style="b"),
                " => ",
                Text(str(data.dst), style="b"),
            )
        )

    def commit_started(self, data: ImageCommitStarted) -> None:
        self._progress.log(
            Text.assemble(
                "Creating image ",
                Text(str(data.target_image), style="b"),
                " from the job container",
            )
        )

    def commit_finished(self, data: ImageCommitFinished) -> None:
        self._progress.log("Image created")

    def close(self) -> None:
        self._progress.stop()


class StreamDockerImageProgress(DockerImageProgress):
    def __init__(self, console: Console) -> None:
        self._console = console
        self._dots = False

    def _end_dots(self) -> None:
        if self._dots:
            self._console.print()
            self._dots = False

    def push(self, data: ImageProgressPush) -> None:
        self._console.print(f"Using local image '{data.src}'")
        self._console.print(f"Using remote image '{data.dst}'")
        self._console.print("Pushing image...")

    def pull(self, data: ImageProgressPull) -> None:
        self._console.print(f"Using remote image '{data.src}'")
        self._console.print(f"Using local image '{data.dst}'")
        self._console.print("Pulling image...")

    def step(self, data: ImageProgressStep) -> None:
        if data.layer_id:
            self._console.print(".", end="")
            self._dots = True
        else:
            self._end_dots()
            self._console.print(data.message)

    def save(self, data: ImageProgressSave) -> None:
        self._console.print(f"Saving job '{data.job}' to image '{data.dst}'...")

    def commit_started(self, data: ImageCommitStarted) -> None:
        self._console.print(f"Using remote image '{data.target_image}'")
        self._console.print(f"Creating image from the job container...")

    def commit_finished(self, data: ImageCommitFinished) -> None:
        self._console.print("Image created")

    def close(self) -> None:
        self._end_dots()


class BaseImagesFormatter:
    def __init__(self, image_formatter: ImageFormatter) -> None:
        self._format_image = image_formatter

    @abc.abstractmethod
    def __call__(self, images: Iterable[RemoteImage]) -> RenderableType:
        raise NotImplementedError


class QuietImagesFormatter(BaseImagesFormatter):
    def __call__(self, images: Iterable[RemoteImage]) -> RenderableType:
        table = Table.grid()
        table.add_column("")
        for image in images:
            table.add_row(self._format_image(image))
        return table


class ShortImagesFormatter(BaseImagesFormatter):
    def __call__(self, images: Iterable[RemoteImage]) -> RenderableType:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Apolo URL", style="bold")
        for image in images:
            table.add_row(self._format_image(image))
        return table


class LongImagesFormatter(BaseImagesFormatter):
    def __call__(self, images: Iterable[RemoteImage]) -> RenderableType:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Apolo URL", style="bold")
        table.add_column("Docker URL")
        for image in images:
            table.add_row(
                self._format_image(image), image.as_docker_url(with_scheme=True)
            )
        return table


class BaseTagsFormatter:
    def _build_table_for(self) -> Table:
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Tag", style="bold")
        return table

    @abc.abstractmethod
    def __call__(self, image: RemoteImage, tags: Iterable[Tag]) -> RenderableType:
        raise NotImplementedError


class ShortTagsFormatter(BaseTagsFormatter):
    def __call__(self, image: RemoteImage, tags: Iterable[Tag]) -> RenderableType:
        table = self._build_table_for()
        for tag in tags:
            table.add_row(tag.name)
        return table


class LongTagsFormatter(BaseTagsFormatter):
    def __call__(self, image: RemoteImage, tags: Iterable[Tag]) -> RenderableType:
        table = self._build_table_for()
        table.add_column("Size")
        for tag in tags:
            assert tag.name
            assert tag.size is not None
            table.add_row(tag.name, format_size(tag.size))
        return table


class ImageInfoFormatter:
    def __call__(self, image: RemoteImage, info: ImageInfo) -> RenderableType:
        header = Table(box=None, show_header=False, show_edge=False)
        header.add_column()
        header.add_column(style="bold", overflow="fold")
        header.add_row("Image", str(image))
        header.add_row("Digest", info.digest)
        header.add_row("Media type", info.media_type)
        header.add_row("Size", format_size(info.size))

        platforms = Table(box=box.SIMPLE_HEAVY)
        platforms.add_column("Platform", style="bold", overflow="fold")
        platforms.add_column("Digest", overflow="fold")
        platforms.add_column("Size", justify="right")
        names: dict[str, str] = {}
        for item in info.platforms:
            name = item.platform or ""
            names[item.digest] = name
            platforms.add_row(name, item.digest, format_size(item.size))
        renderables: list[RenderableType] = [header, platforms]

        if info.attestations:
            attestations = Table(box=box.SIMPLE_HEAVY)
            attestations.add_column("Attestation", style="bold", overflow="fold")
            attestations.add_column("Platform", overflow="fold")
            attestations.add_column("Predicate types", overflow="fold")
            attestations.add_column("Digest", overflow="fold")
            attestations.add_column("Size", justify="right")
            for attestation in info.attestations:
                reference = attestation.reference_digest or ""
                attestations.add_row(
                    attestation.type or "",
                    names.get(reference, reference),
                    "\n".join(attestation.predicate_types),
                    attestation.digest,
                    format_size(attestation.size),
                )
            renderables.append(attestations)
        return Group(*renderables)
