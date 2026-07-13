from typing import Any

from mcp.server.fastmcp import FastMCP

from .._client import client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_disks() -> list[dict[str, Any]]:
        """List persistent disks in the current project."""
        results = []
        async with client() as c:
            async for disk in c.disks.list():
                results.append(
                    {
                        "id": disk.id,
                        "name": disk.name,
                        "status": disk.status.value,
                        "size_gb": disk.storage // (1024**3),
                        "used_gb": (
                            (disk.used_bytes // (1024**3))
                            if disk.used_bytes is not None
                            else None
                        ),
                        "uri": str(disk.uri),
                        "created_at": disk.created_at.isoformat(),
                        "last_usage": (
                            disk.last_usage.isoformat() if disk.last_usage else None
                        ),
                    }
                )
        return results

    @mcp.tool()
    async def create_disk(
        size_gb: int,
        name: str | None = None,
        timeout_unused_hours: float | None = None,
    ) -> dict[str, Any]:
        """Create a persistent disk for attaching to jobs.

        Args:
            size_gb: Disk size in gigabytes.
            name: Optional human-readable name.
            timeout_unused_hours: Auto-delete the disk after this many hours of
                non-attachment. Omit for no auto-deletion.
        """
        from datetime import timedelta

        timeout = (
            timedelta(hours=timeout_unused_hours)
            if timeout_unused_hours is not None
            else None
        )
        async with client() as c:
            disk = await c.disks.create(
                storage=size_gb * (1024**3),
                name=name,
                timeout_unused=timeout,
            )
        return {
            "id": disk.id,
            "name": disk.name,
            "status": disk.status.value,
            "size_gb": disk.storage // (1024**3),
            "uri": str(disk.uri),
            "created_at": disk.created_at.isoformat(),
        }

    @mcp.tool()
    async def delete_disk(disk_id_or_name: str) -> dict[str, str]:
        """Delete a persistent disk.

        Args:
            disk_id_or_name: Disk ID or name.
        """
        async with client() as c:
            await c.disks.rm(disk_id_or_name)
        return {"status": "deleted", "id": disk_id_or_name}
