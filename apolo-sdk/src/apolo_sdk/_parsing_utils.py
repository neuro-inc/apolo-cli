import enum
import re
from dataclasses import dataclass

from yarl import URL

from ._rewrite import rewrite_module
from ._url_utils import _check_uri, _check_uri_str
from ._utils import RELOGIN_TEXT


@rewrite_module
class TagOption(enum.Enum):
    ALLOW = enum.auto()
    DENY = enum.auto()
    DEFAULT = enum.auto()


@rewrite_module
@dataclass(frozen=True)
class RemoteImage:
    name: str
    tag: str | None = None
    registry: str | None = None
    cluster_name: str | None = None
    org_name: str | None = None
    project_name: str | None = None

    @property
    def _is_in_apolo_registry(self) -> bool:
        return bool(self.registry and self.cluster_name and self.project_name)

    @classmethod
    def new_platform_image(
        cls,
        name: str,
        registry: str,
        *,
        cluster_name: str,
        org_name: str | None,
        project_name: str,
        tag: str | None = None,
    ) -> "RemoteImage":
        return RemoteImage(
            name=name,
            tag=tag,
            registry=registry,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        )

    @classmethod
    def new_external_image(
        cls, name: str, registry: str | None = None, *, tag: str | None = None
    ) -> "RemoteImage":
        return RemoteImage(name=name, tag=tag, registry=registry)

    def __post_init__(self) -> None:
        if self.registry:
            if self.project_name:
                if not self.cluster_name:
                    raise ValueError("required cluster name")
            else:
                if self.cluster_name:
                    raise ValueError("required project")
        else:
            if self.project_name or self.cluster_name:
                raise ValueError("required registry")

    def as_docker_url(self, with_scheme: bool = False) -> str:
        if self._is_in_apolo_registry:
            if self.org_name:
                prefix = f"{self.registry}/{self.org_name}/{self.project_name}/"
            else:
                prefix = f"{self.registry}/{self.project_name}/"
            prefix = "https://" + prefix if with_scheme else prefix
        else:
            prefix = ""
        suffix = f":{self.tag}" if self.tag else ""
        return f"{prefix}{self.name}{suffix}"

    def __str__(self) -> str:
        result = self.name
        if self.tag:
            result = f"{result}:{self.tag}"
        if self._is_in_apolo_registry:
            assert self.cluster_name is not None
            base = ""
            if self.org_name:
                base = f"/{self.org_name}"
            result = str(
                URL.build(
                    scheme="image",
                    host=self.cluster_name,
                    path=f"{base}/{self.project_name}/{result}",
                )
            )
        return result

    def __rich__(self) -> str:
        return str(self)


@rewrite_module
@dataclass(frozen=True)
class LocalImage:
    name: str
    tag: str | None = None

    def __str__(self) -> str:
        post = f":{self.tag}" if self.tag else ""
        return self.name + post

    def __rich__(self) -> str:
        return str(self)


class _ImageNameParser:
    def __init__(
        self,
        default_cluster: str,
        default_org: str,
        default_project: str,
        registry_urls: dict[str, URL],
    ):
        self._default_cluster = default_cluster
        self._default_org_name = default_org
        self._default_project_name = default_project
        self._registries = {}
        for cluster_name, registry_url in registry_urls.items():
            if not registry_url.host:
                raise ValueError(
                    f"Empty hostname in registry URL '{registry_url}': "
                    f"please consider updating configuration"
                )
            self._registries[cluster_name] = _get_url_authority(registry_url)

    def parse_as_local_image(self, image: str) -> LocalImage:
        try:
            self._validate_image_name(image)
            return self._parse_as_local_image(image)
        except ValueError as e:
            raise ValueError(f"Invalid local image '{image}': {e}") from e

    def parse_as_platform_image(
        self, image: str, *, tag_option: TagOption = TagOption.DEFAULT
    ) -> RemoteImage:
        try:
            self._validate_image_name(image)
            tag: str | None
            if tag_option == TagOption.DEFAULT:
                tag = "latest"
            else:
                if tag_option == TagOption.DENY and self.has_tag(image):
                    raise ValueError("tag is not allowed")
                tag = None
            return self._parse_as_platform_image(image, default_tag=tag)
        except ValueError as e:
            raise ValueError(f"Invalid remote image '{image}': {e}") from e

    def parse_remote(
        self, value: str, *, tag_option: TagOption = TagOption.DEFAULT
    ) -> RemoteImage:
        if value.startswith("image:") or self._find_by_registry(value):
            return self.parse_as_platform_image(value, tag_option=tag_option)

        img = self.parse_as_local_image(value)
        name = img.name
        registry = None
        if ":" in name:
            msg = "here name must contain slash(es). checked by _split_image_name()"
            assert "/" in name, msg
            registry, name = name.split("/", 1)

        return RemoteImage.new_external_image(name=name, tag=img.tag, registry=registry)

    def convert_to_platform_image(self, image: LocalImage) -> RemoteImage:
        cluster_name = self._default_cluster
        org_name = self._default_org_name
        project_name = self._default_project_name
        name = image.name
        res = self._find_by_registry(name)
        if res:
            cluster_name, path = res
            if path:
                project_name, _, name = path.partition("/")
                if not name:
                    project_name = self._default_project_name
                    name = path

        return RemoteImage.new_platform_image(
            name=name,
            tag=image.tag,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
            registry=self._registries[cluster_name],
        )

    def convert_to_local_image(self, image: RemoteImage) -> LocalImage:
        return LocalImage(name=image.name, tag=image.tag)

    def has_tag(self, image: str) -> bool:
        prefix = "image:"
        if image.startswith(prefix):
            url = URL(image)
            image = url.path
            if image.startswith("/"):
                image = image[1:]
        _, tag = self._split_image_name(image)
        return bool(tag)

    def _validate_image_name(self, image: str) -> None:
        if not image:
            raise ValueError("empty image name")
        if image.startswith("-"):
            raise ValueError("image cannot start with dash")
        if image == "image:latest":
            raise ValueError(
                "ambiguous value: valid as both local and remote image name"
            )

    def _parse_as_local_image(self, image: str) -> LocalImage:
        if image.startswith("image:"):
            raise ValueError("scheme 'image://' is not allowed for local images")
        name, tag = self._split_image_name(image, "latest")
        return LocalImage(name=name, tag=tag)

    def _parse_as_platform_image(
        self, image: str, default_tag: str | None
    ) -> RemoteImage:
        if image.startswith("image:"):
            # Check string representation to detect also trailing "?" and "#".
            _check_uri_str(image, "image")
            url = URL(image)
            if not url.scheme and url.path.startswith("image:"):
                prefix = ""
                if self._default_org_name:
                    prefix = f"/{self._default_org_name}"
                url = URL.build(
                    scheme="image",
                    host=self._default_cluster,
                    path=(
                        f"{prefix}/{self._default_project_name}"
                        f"/{url.path[len('image:') :]}"
                    ),
                )
        else:
            res = self._find_by_registry(image)
            if not res:
                raise ValueError("scheme 'image:' is required for remote images")
            cluster_name, path = res
            url = URL(f"image://{cluster_name}/{path}")

        if not url.path or url.path == "/":
            raise ValueError("no image name specified")
        _check_uri(url)

        name, tag = self._split_image_name(url.path.lstrip("/"), default_tag)
        if url.host is None:
            # This is short url, either image:name or image:/project/name
            cluster_name = self._default_cluster
            org_name = self._default_org_name
        else:
            cluster_name = url.host
            org_name = self._default_org_name
        if url.path.startswith("/"):
            project_name, _, name = name.partition("/")
            if project_name == self._default_org_name and url.host:
                # Long form with explicit org name (image://cluster/org/project/image)
                org_name = project_name
                project_name, _, name = name.partition("/")
            if not name:
                raise ValueError("no image name specified")
        else:
            project_name = self._default_project_name
        if cluster_name not in self._registries:
            tip = RELOGIN_TEXT
            raise RuntimeError(
                f"Cluster {cluster_name} doesn't exist in "
                f"a list of available clusters "
                f"{list(self._registries)}. {tip}"
            )
        return RemoteImage.new_platform_image(
            name=name,
            tag=tag,
            registry=self._registries[cluster_name],
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        )

    def _find_by_registry(self, image: str) -> tuple[str, str] | None:
        for cluster_name, registry in self._registries.items():
            if image.startswith(f"{registry}/"):
                path = image[len(registry) :].lstrip("/")
                return cluster_name, path
        return None

    def _split_image_name(
        self, image: str, default_tag: str | None = None
    ) -> tuple[str, str | None]:
        if image.endswith(":") or image.startswith(":"):
            # case `ubuntu:`, `:latest`
            raise ValueError("empty name or empty tag")
        colon_count = image.count(":")
        if colon_count == 0:
            # case `ubuntu`
            name, tag = image, default_tag
        elif colon_count == 1:
            # case `ubuntu:latest`
            name, tag = image.split(":")
            if "/" in tag:
                # case `localhost:5000/ubuntu`
                name, tag = image, default_tag
        elif colon_count == 2:
            # case `localhost:9000/owner/ubuntu:latest`
            if "/" not in image:
                # case `localhost:9000:latest`
                raise ValueError("too many tags")
            name, tag = image.rsplit(":", 1)
        else:
            raise ValueError("too many tags")
        if "/" in name:
            _, name_no_repo = name.split("/", 1)
        else:
            name_no_repo = name
        if not name_no_repo:
            raise ValueError("no image name specified")
        if not re.fullmatch(
            r"(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*",
            name_no_repo,
        ):
            raise ValueError(
                "invalid image name. Docker specifies it to be the following:\n"
                "Name components may contain lowercase letters, digits and "
                "separators. A separator is defined as a period, one or two "
                "underscores, or one or more dashes. A name component may not "
                "start or end with a separator."
            )
        if tag:
            if len(tag) > 128:
                raise ValueError("tag is to long")
            if not re.fullmatch(r"[a-zA-Z0-9_]+[a-zA-Z0-9_.-]*", tag):
                raise ValueError(
                    "invalid tag. Docker specifies it to be the following:\n"
                    "A tag name must be valid ASCII and may contain lowercase "
                    "and uppercase letters, digits, underscores, periods and "
                    "dashes. A tag name may not start with a period or a dash "
                    "and may contain a maximum of 128 characters."
                )
        return name, tag


@rewrite_module
@dataclass(frozen=True)
class Tag:
    name: str
    size: int | None = None


def _get_url_authority(url: URL) -> str:
    assert url.host is not None
    port = url.explicit_port
    suffix = f":{port}" if port is not None else ""
    return url.host + suffix
