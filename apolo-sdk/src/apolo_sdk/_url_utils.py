import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import quote_from_bytes

from yarl import URL

CLUSTER_SCHEMES = ("storage", "image", "job", "secret", "disk", "blob", "flow")


def uri_from_cli(
    path_or_uri: str,
    project_name: str,
    cluster_name: str,
    org_name: str | None,
    *,
    allowed_schemes: Iterable[str] = ("file", "storage"),
) -> URL:
    if not isinstance(allowed_schemes, tuple):
        allowed_schemes = tuple(allowed_schemes)
    if "file" in allowed_schemes and path_or_uri.startswith("~"):
        path_or_uri = os.path.expanduser(path_or_uri)
        if path_or_uri.startswith("~"):
            raise ValueError(f"Cannot expand user for {path_or_uri}")
        path_or_uri = Path(path_or_uri).as_uri()
        uri = URL(path_or_uri)
    else:
        uri = URL(path_or_uri)
        # len(uri.scheme) == 1 is a workaround for Windows path like C:/path/to.txt
        if not uri.scheme or len(uri.scheme) == 1:
            # Workaround for urllib.parse.urlsplit()'s strange behavior with
            # URLs like "scheme:123".
            if re.fullmatch(r"[a-zA-Z0-9+\-.]{2,}:[0-9]+", path_or_uri):
                uri = URL(f"{path_or_uri}#")
            elif "file" in allowed_schemes:
                path = Path(path_or_uri)
                if path.is_absolute():
                    uri = URL(path.as_uri())
                elif re.fullmatch(r"[0-9]+", path_or_uri):
                    uri = URL(f"file:{path_or_uri}#")
                else:
                    uri = URL("file:" + quote_from_bytes(path.as_posix().encode()))
                path_or_uri = str(uri)
    if not uri.scheme:
        raise ValueError(
            f"URI Scheme not specified. "
            f"Please specify one of {', '.join(allowed_schemes)}."
        )
    _check_scheme(uri.scheme, allowed_schemes)
    # Check string representation to detect also trailing "?" and "#".
    _check_uri_str(path_or_uri, uri.scheme)
    if uri.scheme == "file":
        uri = normalize_local_path_uri(uri)
    else:
        # TODO (y.s.): replace username to project_name
        uri = _normalize_uri(uri, project_name, cluster_name, org_name)
    return uri


def _check_scheme(scheme: str, allowed: Iterable[str]) -> None:
    if not isinstance(allowed, tuple):
        allowed = tuple(allowed)
    if not allowed:
        return
    if scheme not in allowed:
        allowed_str = ", ".join(f"'{item}:'" for item in allowed)
        if len(allowed) > 1:
            verb = "are"
        else:
            verb = "is"
        raise ValueError(
            f"Invalid scheme '{scheme}:' (only {allowed_str} {verb} allowed)"
        )


def normalize_storage_path_uri(
    uri: URL, project_name: str, cluster_name: str, org_name: str | None
) -> URL:
    """Normalize storage url."""
    if uri.scheme != "storage":
        raise ValueError(
            f"Invalid storage scheme '{uri.scheme}:' (only 'storage:' is allowed)"
        )
    return _normalize_uri(uri, project_name, cluster_name, org_name)


def normalize_secret_uri(
    uri: URL, project_name: str, cluster_name: str, org_name: str | None
) -> URL:
    """Normalize secret url."""
    if uri.scheme != "secret":
        raise ValueError(
            f"Invalid secret scheme '{uri.scheme}:' (only 'secret:' is allowed)"
        )
    return _normalize_uri(uri, project_name, cluster_name, org_name)


def normalize_disk_uri(
    uri: URL, project_name: str, cluster_name: str, org_name: str | None
) -> URL:
    """Normalize disk url."""
    if uri.scheme != "disk":
        raise ValueError(
            f"Invalid disk scheme '{uri.scheme}:' (only 'disk:' is allowed)"
        )
    return _normalize_uri(uri, project_name, cluster_name, org_name)


def _normalize_uri(
    uri: URL, project_name: str, cluster_name: str, org_name: str | None
) -> URL:
    """Normalize all other project-bound URI's like jobs, storage, images, etc."""
    _check_uri(uri)
    path = uri.path
    if (uri.host or path.lstrip("/")).startswith("~"):
        raise ValueError(f"Cannot expand user for {uri}")
    if not uri.host:
        if uri.scheme in CLUSTER_SCHEMES:
            host = cluster_name
            if path.startswith("/"):
                path = path.lstrip("/")
            else:
                path = f"{project_name}/{path}" if path else project_name
            if org_name is not None:
                path = f"{org_name}/{path}"
        else:
            raise ValueError(f"Absolute URI is required for scheme {uri.scheme}")
        uri = URL.build(scheme=uri.scheme, host=host, path="/" + path)

    return uri


def normalize_local_path_uri(uri: URL) -> URL:
    """Normalize local file url."""
    if uri.scheme != "file":
        raise ValueError(
            f"Invalid local file scheme '{uri.scheme}:' (only 'file:' is allowed)"
        )
    _check_uri(uri)
    if uri.host:
        raise ValueError(f"Host part is not allowed in file URI, found '{uri.host}'")
    if uri.path.startswith("~"):
        raise ValueError(f"Cannot expand user for {uri}")
    path = _extract_path(uri)
    # path.absolute() does not work with relative path with disk
    # See https://bugs.python.org/issue36305
    path = Path(path.anchor).resolve() / path
    ret = URL(path.as_uri())
    while ret.path.startswith("//"):
        ret = ret.with_path(ret.path[1:])
    return ret


def _extract_path(uri: URL) -> Path:
    path = Path(uri.path)
    if sys.platform == "win32":
        # result of previous normalization
        if re.match(r"[/\\][A-Za-z]:[/\\]", str(path)):
            return Path(str(path)[1:])
    return path


def _check_uri(uri: URL) -> None:
    if uri.fragment:
        raise ValueError(
            f"Fragment part is not allowed in {uri.scheme} URI. "
            f"Use '%23' to quote '#' in path."
        )
    if uri.query:
        raise ValueError(
            f"Query part is not allowed in {uri.scheme} URI. "
            f"Use '%3F' to quote '?' in path."
        )
    if uri.user is not None:
        raise ValueError(f"User is not allowed in {uri.scheme} URI.")
    if uri.password is not None:
        raise ValueError(f"Password is not allowed in {uri.scheme} URI")
    if uri.port is not None:
        raise ValueError(f"Port is not allowed in {uri.scheme} URI")


def _check_uri_str(uri: str, scheme: str) -> None:
    if "#" in uri:
        raise ValueError(
            f"Fragment part is not allowed in {scheme} URI. "
            f"Use '%23' to quote '#' in path."
        )
    if "?" in uri:
        raise ValueError(
            f"Query part is not allowed in {scheme} URI. "
            f"Use '%3F' to quote '?' in path."
        )
