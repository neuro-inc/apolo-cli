import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from yarl import URL

from ._config import Config
from ._parsing_utils import LocalImage, RemoteImage, TagOption, _ImageNameParser
from ._rewrite import rewrite_module
from ._url_utils import _check_scheme, _extract_path, _normalize_uri, uri_from_cli
from ._utils import NoPublicConstructor


@rewrite_module
@dataclass(frozen=True)
class SecretFile:
    secret_uri: URL
    container_path: str


@rewrite_module
@dataclass(frozen=True)
class Volume:
    storage_uri: URL
    container_path: str
    read_only: bool = False


@rewrite_module
@dataclass(frozen=True)
class DiskVolume:
    disk_uri: URL
    container_path: str
    read_only: bool = False


@rewrite_module
@dataclass(frozen=True)
class VolumeParseResult:
    volumes: Sequence[Volume]
    secret_files: Sequence[SecretFile]
    disk_volumes: Sequence[DiskVolume]


@rewrite_module
@dataclass(frozen=True)
class EnvParseResult:
    env: dict[str, str]
    secret_env: dict[str, URL]


class _Unset:
    pass


@rewrite_module
class Parser(metaclass=NoPublicConstructor):
    def __init__(self, config: Config) -> None:
        self._config = config

    def _parse_generic_volume(
        self, volume: str, allow_rw_spec: bool = True, resource_name: str = "volume"
    ) -> tuple[str, str, bool]:
        parts = volume.split(":")
        read_only = False
        if allow_rw_spec and len(parts) == 4:
            if parts[-1] not in ["ro", "rw"]:
                raise ValueError(f"Wrong ReadWrite/ReadOnly mode spec for '{volume}'")
            read_only = parts.pop() == "ro"
        elif len(parts) != 3:
            raise ValueError(f"Invalid {resource_name} specification '{volume}'")
        container_path = parts.pop()
        raw_uri = ":".join(parts)
        return raw_uri, container_path, read_only

    def volume(
        self,
        volume: str,
        cluster_name: str | None = None,
        org_name: str | _Unset | None = _Unset(),
    ) -> Volume:
        raw_uri, container_path, read_only = self._parse_generic_volume(volume)
        storage_uri = uri_from_cli(
            raw_uri,
            self._config.project_name_or_raise,
            cluster_name or self._config.cluster_name,
            org_name if not isinstance(org_name, _Unset) else self._config.org_name,
            allowed_schemes=("storage",),
        )
        return Volume(
            storage_uri=storage_uri, container_path=container_path, read_only=read_only
        )

    def _build_volumes(
        self, input_volumes: list[str], cluster_name: str | None = None
    ) -> list[Volume]:
        if "HOME" in input_volumes:
            raise ValueError("--volume=HOME no longer supported")
        if "ALL" in input_volumes:
            raise ValueError("--volume=ALL no longer supported")

        return [self.volume(vol, cluster_name) for vol in input_volumes]

    def _build_secret_files(
        self, input_volumes: list[str], cluster_name: str | None = None
    ) -> list[SecretFile]:
        secret_files: list[SecretFile] = []
        for volume in input_volumes:
            raw_uri, container_path, _ = self._parse_generic_volume(
                volume, allow_rw_spec=False, resource_name="secret file"
            )
            secret_uri = self._parse_secret_resource(raw_uri, cluster_name)
            secret_files.append(SecretFile(secret_uri, container_path))
        return secret_files

    def _parse_secret_resource(
        self,
        uri: str,
        cluster_name: str | None = None,
        org_name: str | _Unset | None = _Unset(),
    ) -> URL:
        return uri_from_cli(
            uri,
            self._config.project_name_or_raise,
            cluster_name or self._config.cluster_name,
            org_name if not isinstance(org_name, _Unset) else self._config.org_name,
            allowed_schemes=("secret",),
        )

    def _build_disk_volumes(
        self, input_volumes: list[str], cluster_name: str | None = None
    ) -> list[DiskVolume]:
        disk_volumes: list[DiskVolume] = []
        for volume in input_volumes:
            raw_uri, container_path, read_only = self._parse_generic_volume(
                volume, allow_rw_spec=True, resource_name="disk volume"
            )
            disk_uri = self._parse_disk_resource(raw_uri, cluster_name)
            disk_volumes.append(DiskVolume(disk_uri, container_path, read_only))
        return disk_volumes

    def _parse_disk_resource(
        self,
        uri: str,
        cluster_name: str | None = None,
        org_name: str | _Unset | None = _Unset(),
    ) -> URL:
        return uri_from_cli(
            uri,
            self._config.project_name_or_raise,
            cluster_name or self._config.cluster_name,
            org_name if not isinstance(org_name, _Unset) else self._config.org_name,
            allowed_schemes=("disk",),
        )

    def _get_image_parser(self, cluster_name: str | None = None) -> _ImageNameParser:
        registry = {
            cluster.name: cluster.registry_url
            for cluster in self._config.clusters.values()
        }
        return _ImageNameParser(
            default_cluster=cluster_name or self._config.cluster_name,
            default_org=self._config.org_name,
            default_project=self._config.project_name_or_raise,
            registry_urls=registry,
        )

    def local_image(self, image: str) -> LocalImage:
        return self._get_image_parser().parse_as_local_image(image)

    def remote_image(
        self,
        image: str,
        *,
        tag_option: TagOption = TagOption.DEFAULT,
        cluster_name: str | None = None,
    ) -> RemoteImage:
        return self._get_image_parser(cluster_name).parse_remote(
            image, tag_option=tag_option
        )

    def _local_to_remote_image(
        self, image: LocalImage, cluster_name: str | None = None
    ) -> RemoteImage:
        return self._get_image_parser(cluster_name).convert_to_platform_image(image)

    def _remote_to_local_image(self, image: RemoteImage) -> LocalImage:
        return self._get_image_parser().convert_to_local_image(image)

    def envs(
        self,
        env: Sequence[str],
        env_file: Sequence[str] = (),
        cluster_name: str | None = None,
    ) -> EnvParseResult:
        env_dict = self._build_env(env, env_file)
        secret_env_dict = self._extract_secret_env(env_dict, cluster_name)
        return EnvParseResult(
            env=env_dict,
            secret_env=secret_env_dict,
        )

    def _build_env(
        self, env: Sequence[str], env_file: Sequence[str] = ()
    ) -> dict[str, str]:
        lines: list[str] = []
        for filename in env_file:
            lines.extend(_read_lines(filename))
        lines.extend(env)

        env_dict = {}
        for line in lines:
            splitted = line.split("=", 1)
            name = splitted[0]
            if len(splitted) == 1:
                val = os.environ.get(splitted[0], "")
            else:
                val = splitted[1]
            env_dict[name] = val
        return env_dict

    def _extract_secret_env(
        self, env_dict: dict[str, str], cluster_name: str | None = None
    ) -> dict[str, URL]:
        secret_env_dict = {}
        for name, val in env_dict.copy().items():
            if val.startswith("secret:"):
                secret_env_dict[name] = self._parse_secret_resource(val, cluster_name)
                del env_dict[name]
        return secret_env_dict

    def volumes(
        self, volume: Sequence[str], cluster_name: str | None = None
    ) -> VolumeParseResult:
        # N.B. Preserve volumes order when splitting the whole 'volumes' sequence.

        secret_files = []
        disk_volumes = []
        volumes = []
        for vol in volume:
            if vol.startswith("secret:"):
                secret_files.append(vol)
            elif vol.startswith("disk:"):
                disk_volumes.append(vol)
            else:
                volumes.append(vol)
        return VolumeParseResult(
            volumes=self._build_volumes(volumes, cluster_name),
            secret_files=self._build_secret_files(secret_files, cluster_name),
            disk_volumes=self._build_disk_volumes(disk_volumes, cluster_name),
        )

    def uri_to_str(self, uri: URL) -> str:
        return str(uri)

    def str_to_uri(
        self,
        id_or_name_or_uri: str,
        *,
        allowed_schemes: Iterable[str] = (),
        project_name: str | None = None,
        cluster_name: str | None = None,
        org_name: str | _Unset | None = _Unset(),
        short: bool = False,
    ) -> URL:
        ret = uri_from_cli(
            id_or_name_or_uri,
            project_name or self._config.project_name_or_raise,
            cluster_name or self._config.cluster_name,
            org_name if not isinstance(org_name, _Unset) else self._config.org_name,
            allowed_schemes=allowed_schemes,
        )
        if short:
            ret = self._short(ret)
        return ret

    def uri_to_path(self, uri: URL) -> Path:
        if uri.scheme != "file":
            raise ValueError(
                f"Invalid scheme '{uri.scheme}:' (only 'file:' is allowed)"
            )
        return _extract_path(uri)

    def path_to_uri(
        self,
        path: Path,
    ) -> URL:
        return uri_from_cli(
            str(path),
            self._config.project_name_or_raise,
            self._config.cluster_name,
            self._config.org_name,
            allowed_schemes=("file",),
        )

    def normalize_uri(
        self,
        uri: URL,
        *,
        allowed_schemes: Iterable[str] = (),
        project_name: str | None = None,
        cluster_name: str | None = None,
        org_name: str | _Unset | None = _Unset(),
        short: bool = False,
    ) -> URL:
        _check_scheme(uri.scheme, allowed_schemes)
        ret = _normalize_uri(
            uri,
            project_name or self._config.project_name_or_raise,
            cluster_name or self._config.cluster_name,
            org_name if not isinstance(org_name, _Unset) else self._config.org_name,
        )
        if short:
            ret = self._short(ret)
        return ret

    def _short(self, uri: URL) -> URL:
        ret = uri
        if uri.scheme != "file":
            if ret.host == self._config.cluster_name:
                prefix: tuple[str, ...]
                if self._config.org_name is None:
                    prefix = ("/", self._config.project_name_or_raise)
                else:
                    prefix = (
                        "/",
                        self._config.org_name,
                        self._config.project_name_or_raise,
                    )
                if ret.parts[: len(prefix)] == prefix:
                    ret = URL.build(
                        scheme=ret.scheme,
                        host="",
                        path="/".join(ret.parts[len(prefix) :]),
                    )
        else:
            # file scheme doesn't support relative URLs.
            pass
        while ret.path.endswith("/") and ret.path != "/":
            # drop trailing slashes if any
            ret = URL.build(scheme=ret.scheme, host=ret.host or "", path=ret.path[:-1])
        return ret


def _read_lines(env_file: str) -> Iterator[str]:
    with open(env_file, encoding="utf-8-sig") as ef:
        lines = ef.read().splitlines()
    for line in lines:
        line = line.lstrip()
        if line and not line.startswith("#"):
            yield line
