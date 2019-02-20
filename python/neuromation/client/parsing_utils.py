from typing import Tuple

from yarl import URL

from .images import IMAGE_SCHEME, DockerImage


class ImageParser:
    default_tag = "latest"

    def __init__(self, default_user: str, registry_url: str):
        self._default_user = default_user
        self._registry = self._get_registry_hostname(registry_url)

    def parse_local(self, image: str) -> DockerImage:
        try:
            return self._parse_local(image)
        except ValueError as e:
            raise ValueError(f"Invalid local image '{image}': {e}") from e

    def parse_remote(self, image: str, require_scheme: bool = True) -> DockerImage:
        try:
            return self._parse_remote(image, require_scheme)
        except ValueError as e:
            if not require_scheme:
                try:
                    as_local = self.parse_local(image)
                    return DockerImage(name=as_local.name, tag=as_local.tag)
                except ValueError:
                    pass
            raise ValueError(f"Invalid remote image '{image}': {e}") from e

    def _parse_local(self, image: str) -> DockerImage:
        if not image:
            raise ValueError("empty image name")

        # This is hack because URL("ubuntu:v1") is parsed as scheme=ubuntu path=v1
        if image.startswith(f"{IMAGE_SCHEME}://"):
            raise ValueError(
                f"scheme '{IMAGE_SCHEME}://' is not allowed for local images"
            )

        name, tag = self._split_image_name(image.lstrip("/"))

        return DockerImage(name=name, tag=tag)

    def _parse_remote(self, image: str, require_scheme: bool) -> DockerImage:
        if not image:
            raise ValueError("empty image name")

        url = URL(image)

        self._check_allowed_uri_elements(url)

        registry, owner = None, None
        if url.scheme:
            if url.scheme != IMAGE_SCHEME:
                scheme = f"{url.scheme}://" if url.scheme else ""
                raise ValueError(
                    f"scheme '{IMAGE_SCHEME}://' expected, found: '{scheme}"
                )
            registry = self._registry
            owner = self._default_user if not url.host or url.host == "~" else url.host
        elif require_scheme:
            raise ValueError(f"scheme '{IMAGE_SCHEME}://' is required")

        name, tag = self._split_image_name(url.path.lstrip("/"))

        return DockerImage(name=name, tag=tag, registry=registry, owner=owner)

    def _split_image_name(self, image: str) -> Tuple[str, str]:
        colon_count = image.count(":")
        if colon_count == 0:
            image, tag = image, self.default_tag
        elif colon_count == 1:
            image, tag = image.split(":")
        else:
            raise ValueError(f"cannot parse image name '{image}': too many tags")
        return image, tag

    def _get_registry_hostname(self, registry_url: str) -> str:
        try:
            url = URL(registry_url)
        except ValueError as e:
            raise ValueError(f"Could not parse registry URL: {e}")
        if not url.host:
            raise ValueError(
                f"Empty hostname in registry URL '{registry_url}': "
                "please consider updating configuration"
            )
        return url.host

    def _check_allowed_uri_elements(self, url) -> None:
        if url.path == "/":
            raise ValueError("no image name specified")
        if url.query:
            raise ValueError(f"query is not allowed, found: '{url.query}'")
        if url.fragment:
            raise ValueError(f"fragment is not allowed, found: '{url.fragment}'")
        if url.user:
            raise ValueError(f"user is not allowed, found: '{url.user}'")
        if url.password:
            raise ValueError(f"password is not allowed, found: '{url.password}'")
        if url.port:
            raise ValueError(f"password is not allowed, found: '{url.port}'")
