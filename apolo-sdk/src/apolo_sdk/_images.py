import builtins
import contextlib
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any

import aiodocker
import aiohttp
from aiodocker.exceptions import DockerError
from yarl import URL

from ._abc import (
    AbstractDockerImageProgress,
    ImageCommitFinished,
    ImageCommitStarted,
    ImageProgressPull,
    ImageProgressPush,
    ImageProgressSave,
    ImageProgressStep,
)
from ._config import Config
from ._core import _Core
from ._errors import AuthorizationError
from ._parser import Parser
from ._parsing_utils import LocalImage, RemoteImage, Tag, TagOption
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, aclosing

REPOS_PER_PAGE = 30
TAGS_PER_PAGE = 30

DEFAULT_PUSH_TIMEOUT = 20 * 60  # 20 minutes

# the registry returns 404 for manifests whose stored media type
# is not listed in Accept, so all known types must be accepted
# (e.g. kaniko pushes OCI manifests)
MANIFEST_ACCEPT = ", ".join(
    (
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
    )
)

CONTAINERD_SNAPSHOTTER = ["driver-type", "io.containerd.snapshotter.v1"]

log = logging.getLogger(__package__)


@rewrite_module
@dataclass(frozen=True)
class ImagePlatform:
    digest: str
    platform: str | None
    size: int


@rewrite_module
@dataclass(frozen=True)
class ImageAttestation:
    digest: str
    type: str | None
    reference_digest: str | None
    predicate_types: Sequence[str]
    size: int


@rewrite_module
@dataclass(frozen=True)
class ImageInfo:
    name: str
    digest: str
    media_type: str
    size: int
    platforms: Sequence[ImagePlatform]
    attestations: Sequence[ImageAttestation]


def _make_docker_error(status: int, message: str) -> DockerError:
    """Construct DockerError across aiodocker's supported version range."""
    try:
        # aiodocker >= 0.27 accepts the human-readable message directly.
        return DockerError(status, message)
    except TypeError:
        # aiodocker < 0.27 expects the decoded Docker response payload.
        return DockerError(status, {"message": message})  # type: ignore[arg-type]


@rewrite_module
class Images(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config, parse: Parser) -> None:
        self._core = core
        self._config = config
        self._parse = parse
        self._temporary_images: set[str] = set()
        self.__docker: aiodocker.Docker | None = None

    def _get_image_url(self, remote: RemoteImage) -> URL:
        cluster_name = remote.cluster_name
        if cluster_name:
            assert remote.project_name
            registry_url = self._config.get_cluster(cluster_name).registry_url
        else:
            registry_url = self._config.registry_url
        org_prefix = ""
        if remote.org_name:
            org_prefix = f"{remote.org_name}/"
        return (
            registry_url.with_path("/v2/")
            / f"{org_prefix}{remote.project_name}/{remote.name}"
        )

    @property
    def _docker(self) -> aiodocker.Docker:
        if not self.__docker:
            try:
                self.__docker = aiodocker.Docker()
            except ValueError as error:
                if re.match(
                    r".*Either DOCKER_HOST or local sockets are not available.*",
                    f"{error}",
                ):
                    raise _make_docker_error(
                        900,
                        "Docker engine is not available. "
                        "Please specify DOCKER_HOST variable "
                        "if you are using remote docker engine",
                    )
                raise
        return self.__docker

    async def _close(self) -> None:
        for image in self._temporary_images:
            with contextlib.suppress(DockerError, aiohttp.ClientError):
                await self._docker.images.delete(image)
        if self.__docker is not None:
            await self.__docker.close()

    async def push(
        self,
        local: LocalImage,
        remote: RemoteImage | None = None,
        *,
        progress: AbstractDockerImageProgress | None = None,
    ) -> RemoteImage:
        if remote is None:
            remote = self._parse._local_to_remote_image(local)

        if progress is None:
            progress = _DummyProgress()
        progress.push(ImageProgressPush(local, remote))

        repo = remote.as_docker_url()
        try:
            await self._docker.images.tag(str(local), repo)
        except DockerError as error:
            if error.status == 404:
                raise ValueError(
                    f"Image {local} was not found " "in your local docker images"
                ) from error
        auth = await self._config._docker_auth()
        try:
            async with aclosing(  # type: ignore
                self._docker.images.push(
                    repo, auth=auth, stream=True, timeout=DEFAULT_PUSH_TIMEOUT
                )
            ) as it:
                async for obj in it:
                    step = _try_parse_image_progress_step(obj, remote.tag)
                    if step:
                        progress.step(step)
        except DockerError as error:
            # TODO check this part when registry fixed
            if error.status == 403:
                raise AuthorizationError(f"Access denied {remote}") from error
            raise  # pragma: no cover
        return remote

    async def digest(self, remote: RemoteImage) -> str:
        auth = await self._config._registry_auth()
        assert remote.tag
        url = self._get_image_url(remote) / "manifests" / remote.tag
        async with self._core.request(
            "HEAD",
            url,
            auth=auth,
            headers={"Accept": MANIFEST_ACCEPT},
        ) as resp:
            return resp.headers["Docker-Content-Digest"]

    async def size(self, remote: RemoteImage) -> int:
        tag_information = await self.tag_info(remote)
        assert tag_information.size is not None
        return tag_information.size

    async def tag_info(self, remote: RemoteImage) -> Tag:
        auth = await self._config._registry_auth()
        assert remote.tag
        url = self._get_image_url(remote) / "manifests"
        data = await self._get_manifest(url / remote.tag, auth)
        if "manifests" in data:
            children = await self._index_manifests(url, data, auth, attestations=False)
            size = _unique_layers_size(manifest for _, manifest in children)
        else:
            size = sum(layer["size"] for layer in data["layers"])
        return Tag(name=remote.tag, size=size)

    async def inspect(self, remote: RemoteImage) -> ImageInfo:
        auth = await self._config._registry_auth()
        assert remote.tag
        url = self._get_image_url(remote) / "manifests"
        async with self._core.request(
            "GET",
            url / remote.tag,
            auth=auth,
            headers={"Accept": MANIFEST_ACCEPT},
        ) as resp:
            digest = resp.headers["Docker-Content-Digest"]
            media_type = resp.content_type
            data = await resp.json()
        if "manifests" in data:
            children = await self._index_manifests(url, data, auth, attestations=True)
            size = _unique_layers_size(
                manifest for entry, manifest in children if not _is_attestation(entry)
            )
        else:
            children = [({"digest": digest}, data)]
            size = sum(layer["size"] for layer in data.get("layers", []))
        platforms = []
        attestations = []
        for entry, manifest in children:
            layers = manifest.get("layers", [])
            layers_size = sum(layer["size"] for layer in layers)
            if _is_attestation(entry):
                annotations = entry.get("annotations", {})
                attestations.append(
                    ImageAttestation(
                        digest=entry["digest"],
                        type=annotations.get("vnd.docker.reference.type")
                        or entry.get("artifactType"),
                        reference_digest=annotations.get("vnd.docker.reference.digest")
                        or manifest.get("subject", {}).get("digest"),
                        predicate_types=[
                            layer["annotations"]["in-toto.io/predicate-type"]
                            for layer in layers
                            if "in-toto.io/predicate-type"
                            in layer.get("annotations", {})
                        ],
                        size=layers_size,
                    )
                )
            else:
                platforms.append(
                    ImagePlatform(
                        digest=entry["digest"],
                        platform=_format_platform(entry.get("platform")),
                        size=layers_size,
                    )
                )
        return ImageInfo(
            name=remote.tag,
            digest=digest,
            media_type=media_type,
            size=size,
            platforms=platforms,
            attestations=attestations,
        )

    async def _get_manifest(self, url: URL, auth: str) -> dict[str, Any]:
        async with self._core.request(
            "GET",
            url,
            auth=auth,
            headers={"Accept": MANIFEST_ACCEPT},
        ) as resp:
            return await resp.json()

    async def _index_manifests(
        self, url: URL, index: dict[str, Any], auth: str, *, attestations: bool
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        result = []
        for entry in index["manifests"]:
            if not attestations and _is_attestation(entry):
                continue
            data = await self._get_manifest(url / entry["digest"], auth)
            if "manifests" in data:
                result.extend(
                    await self._index_manifests(
                        url, data, auth, attestations=attestations
                    )
                )
            else:
                result.append((entry, data))
        return result

    async def rm(self, remote: RemoteImage, digest: str) -> None:
        auth = await self._config._registry_auth()
        url = self._get_image_url(remote) / "manifests" / digest
        async with self._core.request("DELETE", url, auth=auth) as resp:
            assert resp

    async def pull(
        self,
        remote: RemoteImage,
        local: LocalImage | None = None,
        *,
        progress: AbstractDockerImageProgress | None = None,
        platform: str | Sequence[str] | None = None,
    ) -> LocalImage:
        if local is None:
            local = self._parse._remote_to_local_image(remote)

        platforms: list[str | None]
        if platform is None or isinstance(platform, str):
            platforms = [platform]
        else:
            platforms = list(dict.fromkeys(platform)) or [None]
        if len(platforms) > 1:
            info = await self._docker.system.info()
            if CONTAINERD_SNAPSHOTTER not in (info.get("DriverStatus") or []):
                raise ValueError(
                    "Pulling several platforms of an image requires "
                    "the containerd image store in the docker engine, "
                    "see https://docs.docker.com/engine/storage/containerd/"
                )

        if progress is None:
            progress = _DummyProgress()
        progress.pull(ImageProgressPull(remote, local))

        repo = remote.as_docker_url()
        auth = await self._config._docker_auth()
        try:
            for item in platforms:
                if len(platforms) > 1:
                    progress.step(
                        ImageProgressStep(f"Platform {item}", "", "", None, None)
                    )
                async with aclosing(  # type: ignore
                    self._docker.pull(
                        repo, auth=auth, repo=repo, platform=item, stream=True
                    )
                ) as it:
                    async for obj in it:
                        self._temporary_images.add(repo)
                        step = _try_parse_image_progress_step(obj, remote.tag)
                        if step:
                            progress.step(step)
        except DockerError as error:
            if error.status == 404:
                if (
                    "no matching manifest" in error.message
                    or "no match for platform" in error.message
                ):
                    raise ValueError(
                        f"Cannot pull image {remote}: {error.message}"
                    ) from error
                raise ValueError(
                    f"Image {remote} was not found " "in registry"
                ) from error
            # TODO check this part when registry fixed
            elif error.status == 403:
                raise AuthorizationError(f"Access denied {remote}") from error
            raise  # pragma: no cover

        await self._docker.images.tag(repo, str(local))

        return local

    async def list(self, cluster_name: str | None = None) -> list[RemoteImage]:
        auth = await self._config._registry_auth()
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        prefix = f"image://{cluster_name}/"
        url = self._config.get_cluster(cluster_name).registry_url
        url = url.with_path("/v2/") / "_catalog"
        result: list[RemoteImage] = []
        while True:
            url = url.update_query(n=str(REPOS_PER_PAGE))
            async with self._core.request("GET", url, auth=auth) as resp:
                ret = await resp.json()
                repos = ret["repositories"]
                for repo in repos:
                    try:
                        result.append(
                            self._parse.remote_image(
                                prefix + repo, tag_option=TagOption.DENY
                            )
                        )
                    except ValueError as err:
                        log.warning(str(err))
                if not repos or "next" not in resp.links:
                    break
                url = URL(resp.links["next"]["url"])
        return result

    def _validate_image_for_tags(self, image: RemoteImage) -> None:
        err = f"Invalid image `{image}`: "
        if image.tag is not None:
            raise ValueError(err + "tag is not allowed")
        if not image.project_name:
            raise ValueError(err + "missing image project")
        if not image.name:
            raise ValueError(err + "missing image name")

    async def tags(self, image: RemoteImage) -> builtins.list[RemoteImage]:
        self._validate_image_for_tags(image)
        auth = await self._config._registry_auth()
        url = self._get_image_url(image) / "tags" / "list"
        result: list[RemoteImage] = []
        while True:
            url = url.update_query(n=str(TAGS_PER_PAGE))
            async with self._core.request("GET", url, auth=auth) as resp:
                ret = await resp.json()
                tags = ret.get("tags", [])
                for tag in tags:
                    result.append(replace(image, tag=tag))
                if not tags or "next" not in resp.links:
                    break
                url = URL(resp.links["next"]["url"])
        return result


def _is_attestation(entry: dict[str, Any]) -> bool:
    annotations = entry.get("annotations", {})
    if annotations.get("vnd.docker.reference.type") == "attestation-manifest":
        return True
    if "artifactType" in entry:
        return True
    platform = entry.get("platform", {})
    return platform.get("os") == platform.get("architecture") == "unknown"


def _unique_layers_size(manifests: Iterable[dict[str, Any]]) -> int:
    layers = {
        layer["digest"]: layer["size"]
        for manifest in manifests
        for layer in manifest.get("layers", [])
    }
    return sum(layers.values())


def _format_platform(platform: dict[str, Any] | None) -> str | None:
    if not platform:
        return None
    parts = (platform.get("os"), platform.get("architecture"), platform.get("variant"))
    return "/".join(part for part in parts if part)


def _try_parse_image_progress_step(
    obj: dict[str, Any], target_image_tag: str | None
) -> ImageProgressStep | None:
    _raise_on_error_chunk(obj)
    if "id" in obj and obj["id"] != target_image_tag:
        progress = obj.get("progress")
        detail = obj.get("progressDetail")

        if progress is not None:
            message = f"{obj['id']}: {obj['status']} {obj['progress']}"
        else:
            message = f"{obj['id']}: {obj['status']}"

        if detail is not None:
            current = detail.get("current")
            total = detail.get("total")
        else:
            current = total = None

        return ImageProgressStep(message, obj["id"], obj["status"], current, total)
    return None


def _raise_on_error_chunk(obj: dict[str, Any]) -> None:
    if "error" in obj.keys():
        error_details = obj.get("errorDetail", {"message": "Unknown error"})
        message = error_details.get("message", "Unknown error")
        raise _make_docker_error(900, str(message))


class _DummyProgress(AbstractDockerImageProgress):
    def pull(self, data: ImageProgressPull) -> None:
        pass

    def push(self, data: ImageProgressPush) -> None:
        pass

    def step(self, data: ImageProgressStep) -> None:
        pass

    def save(self, data: ImageProgressSave) -> None:
        pass

    def commit_started(self, data: ImageCommitStarted) -> None:
        pass

    def commit_finished(self, data: ImageCommitFinished) -> None:
        pass
