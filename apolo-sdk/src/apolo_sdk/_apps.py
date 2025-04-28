from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Optional

from yarl import URL

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager


@rewrite_module
@dataclass(frozen=True)
class AppTemplate:
    name: str
    title: str
    version: str
    short_description: str = ""
    tags: List[str] = field(default_factory=list)


@rewrite_module
@dataclass(frozen=True)
class AppValue:
    app_instance_id: str
    type: str
    path: str
    value: Any


@rewrite_module
@dataclass(frozen=True)
class App:
    id: str
    name: str
    display_name: str
    template_name: str
    template_version: str
    project_name: str
    org_name: str
    state: str


@rewrite_module
class Apps(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    def _build_base_url(
        self,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> URL:
        cluster_name = cluster_name or self._config.cluster_name
        if org_name is None:
            org_name = self._config.org_name
            if org_name is None:
                raise ValueError("Organization name is required")
        if project_name is None:
            project_name = self._config.project_name
            if project_name is None:
                raise ValueError("Project name is required")

        # Get the base URL without the /api/v1 prefix
        base_url = self._config.api_url.with_path("")
        url = (
            base_url
            / "apis/apps/v1/cluster"
            / cluster_name
            / "org"
            / org_name
            / "project"
            / project_name
        )
        return url

    @asyncgeneratorcontextmanager
    async def list(
        self,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[App]:
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "instances"
        )

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            data = await resp.json()
            for item in data["items"]:
                yield App(
                    id=item["id"],
                    name=item["name"],
                    display_name=item["display_name"],
                    template_name=item["template_name"],
                    template_version=item["template_version"],
                    project_name=item["project_name"],
                    org_name=item["org_name"],
                    state=item["state"],
                )

    async def install(
        self,
        app_data: dict[str, Any],
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> None:
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "instances"
        )

        auth = await self._config._api_auth()
        async with self._core.request("POST", url, json=app_data, auth=auth):
            pass

    async def uninstall(
        self,
        app_id: str,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> None:
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "instances"
            / app_id
        )

        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth):
            pass

    @asyncgeneratorcontextmanager
    async def get_values(
        self,
        app_id: Optional[str] = None,
        value_type: Optional[str] = None,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[AppValue]:
        """Get values from app instances.

        Args:
            app_id: Optional app instance ID to filter values
            value_type: Optional value type to filter
            cluster_name: Optional cluster name override
            org_name: Optional organization name override
            project_name: Optional project name override

        Returns:
            An async iterator of AppValue objects
        """
        base_url = self._build_base_url(
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        )

        if app_id is not None:
            url = base_url / "instances" / app_id / "values"
        else:
            url = base_url / "instances" / "values"

        params = {}
        if value_type is not None:
            params["type"] = value_type

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, params=params, auth=auth) as resp:
            data = await resp.json()
            for item in data["items"]:
                yield AppValue(
                    app_instance_id=item["app_instance_id"],
                    type=item["type"],
                    path=item["path"],
                    value=item.get("value"),
                )

    @asyncgeneratorcontextmanager
    async def list_templates(
        self,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[AppTemplate]:
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "templates"
        )

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            data = await resp.json()
            for item in data:
                # Create the AppTemplate object with only the required fields
                yield AppTemplate(
                    name=item.get("name", ""),
                    version=item.get("version", ""),
                    title=item.get("title", ""),
                    short_description=item.get("short_description", ""),
                    tags=item.get("tags", []),
                )

    @asyncgeneratorcontextmanager
    async def list_template_versions(
        self,
        name: str,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[AppTemplate]:
        """List all available versions for a specific app template.

        Args:
            name: The name of the app template
            cluster_name: Optional cluster name override
            org_name: Optional organization name override
            project_name: Optional project name override

        Returns:
            An async iterator of AppTemplate objects
        """
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "templates"
            / name
        )

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            data = await resp.json()
            for item in data:
                # Return AppTemplate objects with the same name but different versions
                yield AppTemplate(
                    name=name,
                    version=item.get("version", ""),
                    title=item.get("title", ""),
                    short_description=item.get("short_description", ""),
                    tags=item.get("tags", []),
                )
