import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, List, Optional

from aiohttp import WSMsgType
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
    input: Optional[dict[str, Any]] = None
    description: str = ""


@rewrite_module
@dataclass(frozen=True)
class AppValue:
    instance_id: str
    type: str
    path: str
    value: Any


@rewrite_module
class AppState(str, enum.Enum):
    QUEUED = "queued"
    PROGRESSING = "progressing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ERRORED = "errored"
    UNINSTALLING = "uninstalling"
    UNINSTALLED = "uninstalled"

    @classmethod
    def get_active_states(cls) -> List["AppState"]:
        return [state for state in cls if state != cls.UNINSTALLED]


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
    cluster_name: str
    state: str
    creator: str
    created_at: datetime
    updated_at: datetime
    endpoints: list[str]


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

    def _build_v2_base_url(
        self,
    ) -> URL:
        base_url = self._config.api_url.with_path("")
        return base_url / "apis/apps/v2"

    def _get_monitoring_url(self, cluster_name: Optional[str]) -> URL:
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        return self._config.get_cluster(cluster_name).monitoring_url.with_path(
            "/api/v1"
        )

    @asyncgeneratorcontextmanager
    async def list(
        self,
        states: Optional[List[AppState]] = None,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[App]:
        url = self._build_v2_base_url() / "instances"
        cluster_name = cluster_name or self._config.cluster_name
        org_name = org_name or self._config.org_name
        project_name = project_name or self._config.project_name_or_raise
        url = url.update_query(
            cluster=cluster_name,
            org=org_name,
            project=project_name,
        )
        if states:
            url = url.update_query(states=[state.value for state in states])

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
                    cluster_name=item["cluster_name"],
                    state=item["state"],
                    creator=item["creator"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    endpoints=item["endpoints"],
                )

    async def get(self, app_id: str) -> App:
        url = self._build_v2_base_url() / "instances" / app_id

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            item = await resp.json()
            return App(
                id=item["id"],
                name=item["name"],
                display_name=item["display_name"],
                template_name=item["template_name"],
                template_version=item["template_version"],
                project_name=item["project_name"],
                org_name=item["org_name"],
                cluster_name=item["cluster_name"],
                creator=item["creator"],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                endpoints=item["endpoints"],
                state=item["state"],
            )

    async def install(
        self,
        app_data: dict[str, Any],
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> App:
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "instances"
        )

        auth = await self._config._api_auth()
        async with self._core.request("POST", url, json=app_data, auth=auth) as resp:
            resp.raise_for_status()
            item = await resp.json()
            return App(
                id=item.get("id"),
                name=item.get("name"),
                display_name=item.get("display_name"),
                template_name=item.get("template_name"),
                template_version=item.get("template_version"),
                project_name=item.get("project_name"),
                org_name=item.get("org_name"),
                cluster_name=cluster_name or self._config.cluster_name,
                creator=item.get("creator"),
                created_at=item.get("created_at"),
                updated_at=item.get("updated_at"),
                state=item.get("state"),
                endpoints=[],
            )

    def _can_update_app(self, existing_app: App, app_data: dict[str, Any]) -> bool:
        if existing_app.template_name != app_data["template_name"]:
            return False
        elif existing_app.template_version != app_data["template_version"]:
            return False
        return True

    async def update(
        self,
        app_id: str,
        app_data: dict[str, Any],
    ) -> App:
        existing_app = await self.get(app_id)
        if not self._can_update_app(existing_app, app_data):
            raise ValueError("Cannot update app: template name or version mismatch")

        url = (
            self._build_base_url(
                cluster_name=existing_app.cluster_name,
                org_name=existing_app.org_name,
                project_name=existing_app.project_name,
            )
            / "instances"
            / app_id
        )

        update_payload = {}
        if "display_name" in app_data:
            update_payload["display_name"] = app_data["display_name"]
        if "input" in app_data:
            update_payload["input"] = app_data["input"]

        auth = await self._config._api_auth()
        async with self._core.request(
            "PUT", url, json=update_payload, auth=auth
        ) as resp:
            resp.raise_for_status()
            item = await resp.json()
            return App(
                id=item["id"],
                name=item["name"],
                display_name=item["display_name"],
                template_name=item["template_name"],
                template_version=item["template_version"],
                project_name=existing_app.project_name,
                org_name=existing_app.org_name,
                cluster_name=existing_app.cluster_name,
                state=item["state"],
                creator=item["creator"],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                endpoints=[],
            )

    async def uninstall(
        self,
        app_id: str,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
        *,
        force: bool = False,
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

        params = {}
        if force:
            params["force"] = "true"

        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, params=params, auth=auth):
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
                    instance_id=item.get("instance_id", item.get("app_instance_id")),
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
                    input=None,
                    description="",
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
                    input=None,
                    description="",
                )

    async def get_template(
        self,
        name: str,
        version: Optional[str] = None,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Optional[AppTemplate]:
        """Get detailed information for a specific app template.

        Args:
            name: The name of the app template
            version: Optional version of the template (latest if not specified)
            cluster_name: Optional cluster name override
            org_name: Optional organization name override
            project_name: Optional project name override

        Returns:
            An AppTemplate object with complete template information
        """
        if version is None:
            version = "latest"

        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "templates"
            / name
            / version
        )

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            data = await resp.json()

            if data is None:
                return None

            return AppTemplate(
                name=data.get("name", name),
                title=data.get("title", ""),
                version=data.get("version", ""),
                short_description=data.get("short_description", ""),
                tags=data.get("tags", []),
                input=data.get("input"),
                description=data.get("description", ""),
            )

    @asyncgeneratorcontextmanager
    async def logs(
        self,
        app_id: str,
        *,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
        since: Optional[datetime] = None,
        timestamps: bool = False,
    ) -> AsyncIterator[bytes]:
        """Get logs for an app instance.

        Args:
            app_id: The ID of the app instance
            cluster_name: Optional cluster name override
            org_name: Optional organization name override
            project_name: Optional project name override
            since: Optional timestamp to start logs from
            timestamps: Include timestamps in the logs output

        Returns:
            An async iterator of log chunks as bytes
        """
        url = self._get_monitoring_url(cluster_name) / "apps" / app_id / "log_ws"

        if url.scheme == "https":  # pragma: no cover
            url = url.with_scheme("wss")
        else:
            url = url.with_scheme("ws")

        if since is not None:
            if since.tzinfo is None:
                # Interpret naive datetime object as local time.
                since = since.astimezone()  # pragma: no cover
            url = url.update_query(since=since.isoformat())
        if timestamps:
            url = url.update_query(timestamps="true")

        auth = await self._config._api_auth()
        async with self._core.ws_connect(
            url,
            auth=auth,
            timeout=None,
            heartbeat=30,
        ) as ws:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    if msg.data:
                        yield msg.data
                elif msg.type == WSMsgType.ERROR:  # pragma: no cover
                    raise ws.exception()  # type: ignore
                else:  # pragma: no cover
                    raise RuntimeError(f"Incorrect WebSocket message: {msg!r}")
