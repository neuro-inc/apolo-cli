from pathlib import Path

from yarl import URL


def normalize_storage_path_uri(uri: URL, username: str) -> URL:
    """Normalize storage url."""
    if uri.scheme != "storage":
        raise ValueError(
            f"Invalid storage scheme '{uri.scheme}://' "
            "(only 'storage://' is allowed)"
        )

    if uri.host == "~":
        uri = uri.with_host(username)
    elif not uri.host:
        uri = URL("storage://" + username + "/" + uri.path)
    uri = uri.with_path(uri.path.lstrip("/"))

    return uri


def normalize_local_path_uri(uri: URL) -> URL:
    """Normalize local file url."""
    if uri.scheme != "file":
        raise ValueError(
            f"Invalid local file scheme '{uri.scheme}://' "
            "(only 'file://' is allowed)"
        )
    if uri.host:
        raise ValueError(f"Host part is not allowed, found '{uri.host}'")
    path = Path(uri.path).expanduser().resolve()
    return URL(path.as_uri())
