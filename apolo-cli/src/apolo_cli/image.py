import contextlib
import logging
import re
from collections.abc import Sequence
from dataclasses import replace

from rich.markup import escape as rich_escape
from rich.progress import Progress

from apolo_sdk import LocalImage, RemoteImage, Tag, TagOption

from .click_types import CLUSTER, ORG, PROJECT, RemoteImageType
from .formatters.images import (
    BaseImagesFormatter,
    BaseTagsFormatter,
    DockerImageProgress,
    LongImagesFormatter,
    LongTagsFormatter,
    QuietImagesFormatter,
    ShortImagesFormatter,
    ShortTagsFormatter,
)
from .formatters.utils import ImageFormatter, image_formatter, uri_formatter
from .root import Root
from .utils import argument, command, format_size, group, option

log = logging.getLogger(__name__)


@group()
def image() -> None:
    """
    Container image operations.
    """


@command()
@argument("local_image")
@argument("remote_image", required=False)
async def push(root: Root, local_image: str, remote_image: str | None) -> None:
    """
    Push an image to platform registry.

    Remote image must be URL with image:// scheme.
    Image names can contain tag. If tags not specified 'latest' will
    be used as value.

    Examples:

    apolo push myimage
    apolo push alpine:latest image:my-alpine:production
    apolo push alpine image:/other-project/alpine:shared

    """

    progress = DockerImageProgress.create(console=root.console, quiet=root.quiet)
    local_obj = root.client.parse.local_image(local_image)
    if remote_image is not None:
        remote_obj: RemoteImage | None = root.client.parse.remote_image(remote_image)
    else:
        remote_obj = None
    with contextlib.closing(progress):
        result_remote_image = await root.client.images.push(
            local_obj, remote_obj, progress=progress
        )
    root.print(result_remote_image)


@command()
@argument("remote_image")
@argument("local_image", required=False)
async def pull(root: Root, remote_image: str, local_image: str | None) -> None:
    """
    Pull an image from platform registry.

    Remote image name must be URL with image:// scheme.
    Image names can contain tag.

    Examples:

    apolo pull image:myimage
    apolo pull image:/other-project/alpine:shared
    apolo pull image:/project/my-alpine:production alpine:from-registry

    """

    progress = DockerImageProgress.create(console=root.console, quiet=root.quiet)
    remote_obj = root.client.parse.remote_image(remote_image)
    if local_image is not None:
        local_obj: LocalImage | None = root.client.parse.local_image(local_image)
    else:
        local_obj = None
    with contextlib.closing(progress):
        result_local_image = await root.client.images.pull(
            remote_obj, local_obj, progress=progress
        )
    root.print(result_local_image)


@command()
@option(
    "--cluster",
    type=CLUSTER,
    help="Show images on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    multiple=True,
    help="Filter out images by org (multiple option, the current org by default).",
)
@option("--all-orgs", is_flag=True, default=False, help="Show images in all orgs.")
@option(
    "--project",
    type=PROJECT,
    multiple=True,
    help="Filter out images by project "
    "(multiple option, the current project by default).",
)
@option(
    "--all-projects", is_flag=True, default=False, help="Show images in all projects."
)
@option("-l", "format_long", is_flag=True, help="List in long format.")
@option("--full-uri", is_flag=True, help="Output full image URI.")
@option(
    "-n",
    "--name",
    metavar="PATTERN",
    help="Filter out images by name regex.",
    secure=True,
)
async def ls(
    root: Root,
    cluster: str,
    org: Sequence[str],
    all_orgs: bool,
    project: Sequence[str],
    all_projects: bool,
    format_long: bool,
    full_uri: bool,
    name: str | None,
) -> None:
    """
    List images.
    """

    if not cluster:
        cluster = root.client.config.cluster_name
    with root.status("Fetching images"):
        images = await root.client.images.list(cluster_name=cluster)

    if all_orgs:
        org_names = None
    elif org:
        org_names = set(org)
    else:
        org_names = {root.client.config.org_name}
    if org_names:
        images = [image for image in images if image.org_name in org_names]

    if all_projects:
        project_names = None
    else:
        project_names = set(project or [root.client.config.project_name_or_raise])
    if project_names:
        images = [image for image in images if image.project_name in project_names]

    if name:
        name_re = re.compile(name)
        images = [image for image in images if name_re.fullmatch(image.name)]

    image_fmtr: ImageFormatter
    if full_uri:
        image_fmtr = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
        image_fmtr = image_formatter(uri_formatter=uri_fmtr)
    formatter: BaseImagesFormatter
    if root.quiet:
        formatter = QuietImagesFormatter(image_formatter=image_fmtr)
    elif format_long:
        formatter = LongImagesFormatter(image_formatter=image_fmtr)
    else:
        formatter = ShortImagesFormatter(image_formatter=image_fmtr)
    with root.pager():
        root.print(formatter(images))


@command()
@option(
    "-l", "format_long", is_flag=True, help="List in long format, with image sizes."
)
@argument("image", type=RemoteImageType(tag_option=TagOption.DENY))
async def tags(root: Root, format_long: bool, image: RemoteImage) -> None:
    """
    List tags for image in platform registry.

    Image name must be URL with image:// scheme.

    Examples:

    apolo image tags image:/other-project/alpine
    apolo image tags -l image:myimage
    """

    with root.status(f"Fetching tags for image [b]{image}[/b]"):
        tags_list = [
            Tag(name=str(img.tag)) for img in await root.client.images.tags(image)
        ]

    formatter: BaseTagsFormatter
    if format_long:
        with Progress() as progress:
            task = progress.add_task("Getting image sizes...", total=len(tags_list))
            tags_with_sizes = []
            for tag in tags_list:
                tag_with_size = await root.client.images.tag_info(
                    replace(image, tag=tag.name)
                )
                progress.update(task, advance=1)
                tags_with_sizes.append(tag_with_size)
        formatter = LongTagsFormatter()
        tags_list = tags_with_sizes
    else:
        formatter = ShortTagsFormatter()
    with root.pager():
        root.print(f"Tags for [bold]{rich_escape(str(image))}[/bold]", markup=True)
        root.print(formatter(image, tags_list))


@command()
@option(
    "-f",
    "force",
    is_flag=True,
    help="Force deletion of all tags referencing the image.",
)
@argument(
    "images", nargs=-1, required=True, type=RemoteImageType(tag_option=TagOption.ALLOW)
)
async def rm(root: Root, force: bool, images: Sequence[RemoteImage]) -> None:
    """
    Remove image from platform registry.

    Image name must be URL with image:// scheme.
    Image name must contain tag.

    Examples:

    apolo image rm image:/other-project/alpine:shared
    apolo image rm image:myimage:latest
    """
    for image in images:
        if image.tag is None:
            await remove_image(root, image)
        else:
            await remove_tag(root, image, force=force)


@command()
@argument("image", type=RemoteImageType())
async def size(root: Root, image: RemoteImage) -> None:
    """
    Get image size

    Image name must be URL with image:// scheme.
    Image name must contain tag.

    Examples:

    apolo image size image:/other-project/alpine:shared
    apolo image size image:myimage:latest
    """
    size = await root.client.images.size(image)
    root.print(format_size(size))


@command()
@argument("image", type=RemoteImageType())
async def digest(root: Root, image: RemoteImage) -> None:
    """
    Get digest of an image from remote registry

    Image name must be URL with image:// scheme.
    Image name must contain tag.

    Examples:

    apolo image digest image:/other-project/alpine:shared
    apolo image digest image:myimage:latest
    """
    res = await root.client.images.digest(image)
    root.print(res)


image.add_command(ls)
image.add_command(push)
image.add_command(pull)
image.add_command(rm)
image.add_command(size)
image.add_command(digest)
image.add_command(tags)


async def remove_image(root: Root, image: RemoteImage) -> None:
    assert image.tag is None
    images = await root.client.images.tags(image)
    for img in images:
        await remove_tag(root, img, force=True)


async def remove_tag(root: Root, image: RemoteImage, *, force: bool) -> None:
    assert image.tag is not None
    digest = await root.client.images.digest(image)
    root.print(
        f"Deleting {image} identified by [bold]{rich_escape(digest)}[/bold]",
        markup=True,
    )
    tags = await root.client.images.tags(replace(image, tag=None))
    # Collect all tags referencing the image to be deleted
    if not force and len(tags) > 1:
        tags_for_image = []
        for tag in tags:
            tag_digest = await root.client.images.digest(tag)
            if tag_digest == digest:
                tags_for_image.append(tag_digest)
        if len(tags_for_image) > 1:
            raise ValueError(
                f"There's more than one tag referencing this digest: "
                f"{', '.join(tags_for_image)}.\n"
                f"Please use -f to force deletion for all of them."
            )
    await root.client.images.rm(image, digest)
