from typing import Any

from mcp.server.fastmcp import FastMCP

import apolo_sdk

from .._client import client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def run_job(
        image: str,
        preset_name: str,
        command: str | None = None,
        name: str | None = None,
        description: str | None = None,
        env: dict[str, str] | None = None,
        life_span_hours: float | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a job on the Apolo platform.

        Args:
            image: Docker image to run (e.g. "python:3.11", "ghcr.io/org/image:tag").
            preset_name: Resource preset (e.g. "gpu-small", "cpu-large"). List available
                presets with your cluster config or ask the platform admin.
            command: Shell command to run inside the container.
            name: Optional human-readable job name.
            description: Optional free-text description.
            env: Environment variables to set inside the container.
            life_span_hours: How long (hours) the job may run before auto-kill. Omit for
                the cluster default.
            tags: Optional list of tags for filtering.
        """
        life_span = life_span_hours * 3600 if life_span_hours is not None else None
        async with client() as c:
            remote_image = c.parse.remote_image(image)
            job = await c.jobs.start(
                image=remote_image,
                preset_name=preset_name,
                command=command,
                name=name,
                description=description,
                env=env or {},
                life_span=life_span,
                tags=tags or [],
            )
        return {
            "id": job.id,
            "name": job.name,
            "status": job.status.value,
            "image": str(job.container.image),
            "created_at": (
                job.history.created_at.isoformat() if job.history.created_at else None
            ),
        }

    @mcp.tool()
    async def list_jobs(
        statuses: list[str] | None = None,
        name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List jobs on the Apolo platform.

        Args:
            statuses: Filter by status. Valid values: pending, running, succeeded,
                failed, cancelled. Defaults to all active (pending + running).
            name: Filter by job name (exact match).
            limit: Maximum number of jobs to return (default 20).
        """
        status_filter: set[apolo_sdk.JobStatus] | None = None
        if statuses:
            status_filter = {apolo_sdk.JobStatus(s) for s in statuses}
        else:
            status_filter = apolo_sdk.JobStatus.active_items()

        results = []
        async with client() as c:
            async for job in c.jobs.list(statuses=status_filter, name=name):
                results.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "status": job.status.value,
                        "image": str(job.container.image),
                        "created_at": (
                            job.history.created_at.isoformat()
                            if job.history.created_at
                            else None
                        ),
                        "description": job.description,
                    }
                )
                if len(results) >= limit:
                    break
        return results

    @mcp.tool()
    async def get_job_status(job_id: str) -> dict[str, Any]:
        """Get the current status and details of a job.

        Args:
            job_id: The job ID (e.g. "job-abc123").
        """
        async with client() as c:
            job = await c.jobs.status(job_id)
        history = job.history
        return {
            "id": job.id,
            "name": job.name,
            "status": job.status.value,
            "image": str(job.container.image),
            "command": job.container.command,
            "preset": job.preset_name,
            "created_at": (
                history.created_at.isoformat() if history.created_at else None
            ),
            "started_at": (
                history.started_at.isoformat() if history.started_at else None
            ),
            "finished_at": (
                history.finished_at.isoformat() if history.finished_at else None
            ),
            "exit_code": history.exit_code,
            "reason": history.reason,
            "description": history.description,
            "tags": list(job.tags),
        }

    @mcp.tool()
    async def get_job_logs(job_id: str, max_bytes: int = 32768) -> str:
        """Fetch stdout/stderr logs from a job.

        Args:
            job_id: The job ID.
            max_bytes: Maximum bytes to return (default 32 KB). Logs are truncated
                from the beginning if they exceed this limit.
        """
        chunks: list[bytes] = []
        total = 0
        async with client() as c:
            async for chunk in c.jobs.monitor(job_id):
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    break
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            raw = raw[-max_bytes:]
        return raw.decode("utf-8", errors="replace")

    @mcp.tool()
    async def kill_job(job_id: str) -> dict[str, str]:
        """Kill (cancel) a running or pending job.

        Args:
            job_id: The job ID to kill.
        """
        async with client() as c:
            await c.jobs.kill(job_id)
        return {"status": "killed", "id": job_id}
