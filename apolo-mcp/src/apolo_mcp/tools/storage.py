from typing import Any

from mcp.server.fastmcp import FastMCP
from yarl import URL

import apolo_sdk

from .._client import client


def _resolve_uri(path: str, c: apolo_sdk.Client) -> URL:
    """Accept apolo:// URIs or bare paths; return a normalized storage URL."""
    if path.startswith("apolo://") or path.startswith("storage:"):
        return URL(path)
    # Bare path: resolve against current cluster/org/project
    cfg = c.config
    cluster = cfg.cluster_name
    org = cfg.org_name or ""
    project = cfg.project_name_or_raise
    base = f"apolo://{cluster}/{org}/{project}"
    path = path.lstrip("/")
    return URL(f"{base}/{path}" if path else base)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_files(path: str = "") -> list[dict[str, Any]]:
        """List files and directories in Apolo storage.

        Args:
            path: Storage path. Use an apolo:// URI or a bare path like
                "/my-project/results". Defaults to the project root.
        """
        results = []
        async with client() as c:
            uri = _resolve_uri(path, c)
            async for entry in c.storage.list(uri):
                results.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": entry.size,
                        "modified_at": entry.modification_time,
                        "path": str(uri / entry.name),
                    }
                )
        return results

    @mcp.tool()
    async def upload_text(path: str, content: str) -> dict[str, str]:
        """Write a text file to Apolo storage.

        Useful for saving experiment configs, results, or any text artifact.

        Args:
            path: Destination path (apolo:// URI or bare path like "/results/run.txt").
            content: Text content to write.
        """
        async with client() as c:
            uri = _resolve_uri(path, c)
            await c.storage.create(uri, content.encode())
        return {"status": "uploaded", "path": str(uri)}

    @mcp.tool()
    async def download_text(path: str, max_bytes: int = 65536) -> str:
        """Read a text file from Apolo storage.

        Args:
            path: Source path (apolo:// URI or bare path).
            max_bytes: Maximum bytes to read (default 64 KB).
        """
        async with client() as c:
            uri = _resolve_uri(path, c)
            chunks: list[bytes] = []
            total = 0
            async for chunk in c.storage.open(uri):
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    break
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            raw = raw[:max_bytes]
        return raw.decode("utf-8", errors="replace")

    @mcp.tool()
    async def make_dir(path: str) -> dict[str, str]:
        """Create a directory in Apolo storage.

        Args:
            path: Directory path to create (apolo:// URI or bare path).
        """
        async with client() as c:
            uri = _resolve_uri(path, c)
            await c.storage.mkdir(uri, parents=True, exist_ok=True)
        return {"status": "created", "path": str(uri)}

    @mcp.tool()
    async def delete_path(path: str, recursive: bool = False) -> dict[str, str]:
        """Delete a file or directory from Apolo storage.

        Args:
            path: Path to delete (apolo:// URI or bare path).
            recursive: If True, delete a directory and all its contents.
        """
        async with client() as c:
            uri = _resolve_uri(path, c)
            await c.storage.rm(uri, recursive=recursive)
        return {"status": "deleted", "path": str(uri)}
