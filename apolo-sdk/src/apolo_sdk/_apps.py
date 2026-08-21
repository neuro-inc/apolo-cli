import builtins
import enum
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aiohttp import WSMsgType
from yarl import URL

from ._config import Config
from ._core import _Core
from ._errors import ResourceNotFound
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager


@rewrite_module
@dataclass(frozen=True)
class AppTemplate:
    name: str
    title: str
    version: str
    short_description: str = ""
    tags: list[str] = field(default_factory=list)
    input: dict[str, Any] | None = None
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
    def get_active_states(cls) -> list["AppState"]:
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
    namespace: str
    state: str
    creator: str
    created_at: datetime
    updated_at: datetime
    endpoints: list[str]


@rewrite_module
@dataclass(frozen=True)
class AppEventResource:
    kind: str | None = None
    name: str | None = None
    uid: str | None = None
    health_status: str | None = None
    health_message: str | None = None


@rewrite_module
@dataclass(frozen=True)
class AppEvent:
    created_at: datetime
    state: str
    reason: str | None
    message: str | None
    resources: list[AppEventResource]


@rewrite_module
@dataclass(frozen=True)
class AppConfigurationRevision:
    revision_number: int
    creator: str
    comment: str | None
    created_at: datetime
    end_at: datetime | None


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> list[dict[str, Any]]:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        target = root.get("$defs", {}).get(ref.split("/")[-1])
        return _resolve(target, root) if isinstance(target, dict) else []

    variants = schema.get("anyOf") or schema.get("oneOf")
    if isinstance(variants, list):
        return [
            resolved
            for variant in variants
            if isinstance(variant, dict)
            for resolved in _resolve(variant, root)
        ]

    return [schema]


def undefined_input_fields(
    schema: dict[str, Any] | None,
    value: Any,
    root: dict[str, Any] | None = None,
    prefix: str = "",
    depth: int = 0,
) -> list[str]:
    """Paths in ``value`` that ``schema`` does not define.

    The app API answers 500 rather than a validation error when it is given a
    field the template does not have, which is what a config written for
    another version of the same app usually carries.
    """
    if not isinstance(schema, dict) or not isinstance(value, dict) or depth > 10:
        return []

    root = root if root is not None else schema
    variants = _resolve(schema, root)

    known: dict[str, dict[str, Any]] = {}
    for variant in variants:
        properties = variant.get("properties")
        if isinstance(properties, dict):
            for name, definition in properties.items():
                if isinstance(definition, dict):
                    known.setdefault(name, definition)

    if not known:
        return []

    undefined = []
    for name, nested in value.items():
        path = f"{prefix}.{name}" if prefix else name
        definition = known.get(name)
        if definition is None:
            undefined.append(path)
        else:
            undefined.extend(
                undefined_input_fields(definition, nested, root, path, depth + 1)
            )

    return undefined


@rewrite_module
class Apps(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    def _build_base_url(
        self,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> URL:
        pk = self._config.get_project_key(cluster_name, org_name, project_name)

        # Get TODO: the base URL without the /api/v1 prefix
        base_url = self._config.api_url.with_path("")
        url = (
            base_url
            / "apis/apps/v1/cluster"
            / pk.cluster_name
            / "org"
            / pk.org_name
            / "project"
            / pk.project_name
        )
        return url

    def _build_v2_base_url(
        self,
    ) -> URL:
        base_url = self._config.api_url.with_path("")
        return base_url / "apis/apps/v2"

    def _get_monitoring_url(self, cluster_name: str | None) -> URL:
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        return self._config.get_cluster(cluster_name).monitoring_url.with_path(
            "/api/v1"
        )

    @staticmethod
    def _parse_app_read_instance(item: dict[str, Any]) -> App:
        return App(
            id=item["id"],
            name=item["name"],
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            creator=item["creator"],
            display_name=item["display_name"],
            template_name=item["template_name"],
            template_version=item["template_version"],
            project_name=item["project_name"],
            org_name=item["org_name"],
            cluster_name=item["cluster_name"],
            namespace=item["namespace"],
            state=item["state"],
            endpoints=item["endpoints"],
        )

    @asyncgeneratorcontextmanager
    async def list(
        self,
        states: list[AppState] | None = None,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[App]:
        url = self._build_v2_base_url() / "instances"
        cluster_name = cluster_name or self._config.cluster_name
        org_name = org_name or self._config.org_name
        project_name = project_name or self._config.project_name_or_raise
        current_page = 1
        url = url.update_query(
            cluster=cluster_name,
            org=org_name,
            project=project_name,
            page=current_page,
        )
        if states:
            url = url.update_query(states=[state.value for state in states])

        auth = await self._config._api_auth()
        while True:
            async with self._core.request("GET", url, auth=auth) as resp:
                data = await resp.json()
            for item in data["items"]:
                yield self._parse_app_read_instance(item)

            total_pages = data.get("pages", 1)
            if current_page >= total_pages:
                break
            current_page += 1
            url = url.update_query(page=current_page)

    async def get(self, app_id: str) -> App:
        url = self._build_v2_base_url() / "instances" / app_id

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            item = await resp.json()
            return self._parse_app_read_instance(item)

    async def install(
        self,
        app_data: dict[str, Any],
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
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
            return self._parse_app_read_instance(item)

    async def _undefined_for_app(
        self, existing_app: App, app_data: dict[str, Any]
    ) -> builtins.list[str]:
        try:
            template = await self.get_template(
                name=existing_app.template_name,
                version=existing_app.template_version,
                cluster_name=existing_app.cluster_name,
                org_name=existing_app.org_name,
                project_name=existing_app.project_name,
            )
        except ResourceNotFound:
            return []

        if template is None:
            return []

        return undefined_input_fields(template.input, app_data.get("input"))

    async def configure(
        self,
        app_id: str,
        app_data: dict[str, Any],
        comment: str | None = None,
    ) -> App:
        existing_app = await self.get(app_id)

        if existing_app.template_name != app_data.get("template_name"):
            raise ValueError(
                f"Cannot update app: it was installed from "
                f"{existing_app.template_name!r} and the config is for "
                f"{app_data.get('template_name')!r}"
            )

        undefined = await self._undefined_for_app(existing_app, app_data)

        if undefined:
            raise ValueError(
                f"Cannot update app: "
                f"{existing_app.template_version} has no "
                f"{', '.join(undefined)}. Remove "
                f"{'them' if len(undefined) > 1 else 'it'} from the config or "
                f"install a version that still has "
                f"{'them' if len(undefined) > 1 else 'it'}."
            )

        url = (
            self._build_base_url(
                cluster_name=existing_app.cluster_name,
                org_name=existing_app.org_name,
                project_name=existing_app.project_name,
            )
            / "instances"
            / app_id
        )

        configure_payload = {}
        if "display_name" in app_data:
            configure_payload["display_name"] = app_data["display_name"]
        if "input" in app_data:
            configure_payload["input"] = app_data["input"]
        if comment is not None:
            configure_payload["comment"] = comment

        auth = await self._config._api_auth()
        async with self._core.request(
            "PUT", url, json=configure_payload, auth=auth
        ) as resp:
            resp.raise_for_status()
            item = await resp.json()
            return self._parse_app_read_instance(item)

    async def uninstall(
        self,
        app_id: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
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
        app_id: str | None = None,
        value_type: str | None = None,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
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
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
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
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
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
        version: str | None = None,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AppTemplate | None:
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

    async def get_output(
        self,
        app_id: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> dict[str, Any]:
        """Get output parameters from an app instance.

        Args:
            app_id: The ID of the app instance
            cluster_name: Optional cluster name override
            org_name: Optional organization name override
            project_name: Optional project name override

        Returns:
            A dictionary containing output parameters as key-value pairs

        Raises:
            ResourceNotFound: If app instance not found or no output records exist
        """
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "instances"
            / app_id
            / "output"
        )

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            return await resp.json()

    @asyncgeneratorcontextmanager
    async def logs(
        self,
        app_id: str,
        *,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        since: datetime | None = None,
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

    @asyncgeneratorcontextmanager
    async def get_events(
        self,
        app_id: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[AppEvent]:
        """Get events for an app instance.

        Args:
            app_id: The ID of the app instance
            cluster_name: Optional cluster name override
            org_name: Optional organization name override
            project_name: Optional project name override

        Returns:
            An async iterator of AppEvent objects
        """
        url = (
            self._build_base_url(
                cluster_name=cluster_name,
                org_name=org_name,
                project_name=project_name,
            )
            / "instances"
            / app_id
            / "events"
        )

        auth = await self._config._api_auth()
        current_page = 1
        while True:
            async with self._core.request("GET", url, auth=auth) as resp:
                resp.raise_for_status()
                data = await resp.json()
            for item in data.get("items", []):
                resources = []
                for res in item.get("resources", []):
                    resources.append(
                        AppEventResource(
                            kind=res.get("kind"),
                            name=res.get("name"),
                            uid=res.get("uid"),
                            health_status=res.get("health_status"),
                            health_message=res.get("health_message"),
                        )
                    )
                yield AppEvent(
                    created_at=item["created_at"],
                    state=item["state"],
                    reason=item["reason"],
                    message=item.get("message"),
                    resources=resources,
                )
            total_pages = data.get("pages", 1)
            if current_page >= total_pages:
                break
            current_page += 1
            url = url.update_query(page=current_page)

    async def get_revisions(
        self,
        app_id: str,
    ) -> builtins.list[AppConfigurationRevision]:
        url = self._build_v2_base_url() / "instances" / app_id / "revisions"

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return [
                AppConfigurationRevision(
                    revision_number=item["revision_number"],
                    creator=item["creator"],
                    comment=item["comment"],
                    created_at=item["created_at"],
                    end_at=item["end_at"],
                )
                for item in data
            ]

    async def rollback(
        self,
        app_id: str,
        revision_number: int,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        comment: str | None = None,
    ) -> App:
        url = (
            self._build_base_url(
                cluster_name=cluster_name or self._config.cluster_name,
                org_name=org_name or self._config.org_name,
                project_name=project_name or self._config.project_name_or_raise,
            )
            / "instances"
            / app_id
            / "revisions"
            / str(revision_number)
            / "rollback"
        )
        auth = await self._config._api_auth()
        payload = {}
        if comment is not None:
            payload["comment"] = comment
        async with self._core.request("POST", url, json=payload, auth=auth) as resp:
            resp.raise_for_status()
            item = await resp.json()
            return self._parse_app_read_instance(item)

    async def get_input(
        self,
        app_id: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
        revision: int | None = None,
    ) -> dict[str, Any]:
        url = (
            self._build_base_url(
                cluster_name=cluster_name or self._config.cluster_name,
                org_name=org_name or self._config.org_name,
                project_name=project_name or self._config.project_name_or_raise,
            )
            / "instances"
            / app_id
        )
        if revision is not None:
            url = url / "revisions" / str(revision) / "input"
        else:
            url = url / "input"
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            resp.raise_for_status()
            return await resp.json()
