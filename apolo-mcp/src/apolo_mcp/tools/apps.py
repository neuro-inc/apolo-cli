from typing import Any

from mcp.server.fastmcp import FastMCP

from .._client import client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_app_templates() -> list[dict[str, Any]]:
        """List available application templates on the Apolo platform."""
        results = []
        async with client() as c:
            async for template in c.apps.list_templates():
                results.append(
                    {
                        "name": template.name,
                        "title": template.title,
                        "version": template.version,
                        "short_description": template.short_description,
                        "tags": template.tags,
                    }
                )
        return results

    @mcp.tool()
    async def install_app(
        template_name: str,
        template_version: str,
        app_name: str,
        display_name: str | None = None,
        input_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Install (deploy) an application from a template.

        Use list_app_templates to discover available templates and their versions.
        Use get_app_template_details (if available) to learn the required input schema.

        Args:
            template_name: Template name (e.g. "jupyter", "mlflow").
            template_version: Template version string (e.g. "1.0.0").
            app_name: Unique name for this app instance.
            display_name: Human-readable label (defaults to app_name).
            input_values: Template input values. Keys and types depend on the template's
                input schema.
        """
        app_data: dict[str, Any] = {
            "template_name": template_name,
            "template_version": template_version,
            "name": app_name,
            "display_name": display_name or app_name,
            "input": input_values or {},
        }
        async with client() as c:
            app = await c.apps.install(app_data=app_data)
        return {
            "id": app.id,
            "name": app.name,
            "display_name": app.display_name,
            "template_name": app.template_name,
            "state": app.state,
            "endpoints": app.endpoints,
            "created_at": app.created_at.isoformat(),
        }

    @mcp.tool()
    async def list_apps(
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """List installed applications.

        Args:
            include_inactive: If True, also return uninstalled apps.
        """
        results = []
        async with client() as c:
            async for app in c.apps.list():
                if not include_inactive and app.state == "uninstalled":
                    continue
                results.append(
                    {
                        "id": app.id,
                        "name": app.name,
                        "display_name": app.display_name,
                        "template_name": app.template_name,
                        "state": app.state,
                        "endpoints": app.endpoints,
                        "created_at": app.created_at.isoformat(),
                        "updated_at": app.updated_at.isoformat(),
                    }
                )
        return results

    @mcp.tool()
    async def get_app(app_id: str) -> dict[str, Any]:
        """Get details of an installed application.

        Args:
            app_id: The app ID.
        """
        async with client() as c:
            app = await c.apps.get(app_id)
        return {
            "id": app.id,
            "name": app.name,
            "display_name": app.display_name,
            "template_name": app.template_name,
            "template_version": app.template_version,
            "state": app.state,
            "endpoints": app.endpoints,
            "namespace": app.namespace,
            "cluster_name": app.cluster_name,
            "org_name": app.org_name,
            "project_name": app.project_name,
            "created_at": app.created_at.isoformat(),
            "updated_at": app.updated_at.isoformat(),
        }

    @mcp.tool()
    async def uninstall_app(app_id: str) -> dict[str, str]:
        """Uninstall (delete) an application.

        Args:
            app_id: The app ID to uninstall.
        """
        async with client() as c:
            await c.apps.uninstall(app_id)
        return {"status": "uninstalling", "id": app_id}
