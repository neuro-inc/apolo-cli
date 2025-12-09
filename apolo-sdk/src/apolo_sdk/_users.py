from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from aiohttp.web import HTTPCreated, HTTPNoContent
from yarl import URL

from ._admin import _Admin
from ._config import Config
from ._core import _Core
from ._errors import AuthError, ClientError, NotSupportedError
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor


@rewrite_module
class Action(str, Enum):
    READ = "read"
    WRITE = "write"
    MANAGE = "manage"


@rewrite_module
@dataclass(frozen=True)
class Permission:
    uri: URL
    action: Action


@rewrite_module
@dataclass(frozen=True)
class Share:
    user: str
    permission: Permission


@rewrite_module
@dataclass(frozen=True)
class Quota:
    credits: Decimal | None = None
    total_running_jobs: int | None = None


@rewrite_module
class Users(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config, admin: _Admin) -> None:
        self._core = core
        self._config = config
        self._admin = admin

    async def get_quota(self) -> Quota:
        try:
            try:
                ret = await self._admin.get_cluster_user(
                    cluster_name=self._config.cluster_name,
                    org_name=self._config.org_name,
                    user_name=self._config.username,
                )
            except AuthError:
                ret = await self._admin.get_cluster_user(
                    cluster_name=self._config.cluster_name,
                    org_name=None,
                    user_name=self._config.username,
                )
        except NotSupportedError:
            # FOSS configuration without admin service and limits
            return Quota(credits=None, total_running_jobs=None)
        return Quota(
            credits=ret.balance.credits,
            total_running_jobs=ret.quota.total_running_jobs,
        )

    async def get_org_quota(self) -> Quota | None:
        if self._config.org_name is None:
            return None
        try:
            ret = await self._admin.get_org_cluster(
                cluster_name=self._config.cluster_name,
                org_name=self._config.org_name,
            )
        except NotSupportedError:
            # FOSS configuration without admin service and limits
            return Quota(credits=None, total_running_jobs=None)
        return Quota(
            credits=ret.balance.credits,
            total_running_jobs=ret.quota.total_running_jobs,
        )

    async def get_acl(
        self, user: str, scheme: str | None = None, *, uri: URL | None = None
    ) -> Sequence[Permission]:
        url = self._get_user_url(user) / "permissions"
        if scheme:
            if uri is not None:
                raise ValueError("Conflicting arguments 'uri' and 'scheme'")
            uri = URL.build(scheme=scheme)
        params = {"uri": str(uri)} if uri is not None else {}
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, params=params, auth=auth) as resp:
            payload = await resp.json()
        ret = []
        for item in payload:
            uri = URL(item["uri"])
            action = Action(item["action"])
            ret.append(Permission(uri, action))
        return ret

    async def get_shares(
        self, user: str, scheme: str | None = None, *, uri: URL | None = None
    ) -> Sequence[Share]:
        url = self._get_user_url(user) / "permissions" / "shared"
        if scheme:
            if uri is not None:
                raise ValueError("Conflicting arguments 'uri' and 'scheme'")
            uri = URL.build(scheme=scheme)
        params = {"uri": str(uri)} if uri is not None else {}
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, params=params, auth=auth) as resp:
            payload = await resp.json()
        ret = []
        for item in payload:
            uri = URL(item["uri"])
            action = Action(item["action"])
            ret.append(Share(item["user"], Permission(uri, action)))
        return ret

    async def get_subroles(
        self,
        user: str,
    ) -> Sequence[str]:
        url = self._get_user_url(user) / "subroles"
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            payload = await resp.json()
        return payload["subroles"]

    async def share(self, user: str, permission: Permission) -> Permission:
        url = self._get_user_url(user) / "permissions"
        payload = [_permission_to_api(permission)]
        auth = await self._config._api_auth()
        async with self._core.request("POST", url, json=payload, auth=auth) as resp:
            if resp.status != HTTPCreated.status_code:
                raise ClientError("Server return unexpected result.")
            payload = await resp.json()
            perm = payload[0]
            return Permission(
                uri=URL(perm["uri"]),
                action=Action(perm["action"]),
            )

    async def revoke(self, user: str, uri: URL) -> None:
        url = self._get_user_url(user) / "permissions"
        auth = await self._config._api_auth()
        async with self._core.request(
            "DELETE", url, params={"uri": str(uri)}, auth=auth
        ) as resp:
            #  TODO: server part contain TODO record for returning more then
            #  HTTPNoContent, this part must me refactored then
            if resp.status != HTTPNoContent.status_code:
                raise ClientError(f"Server return unexpected result: {resp.status}.")
        return None

    async def add(self, role_name: str) -> None:
        url = self._config.api_url / "users"
        auth = await self._config._api_auth()
        async with self._core.request(
            "POST", url, json={"name": role_name}, auth=auth
        ) as resp:
            if resp.status != HTTPCreated.status_code:
                raise ClientError(f"Server return unexpected result: {resp.status}.")
        return None

    async def remove(self, role_name: str) -> None:
        url = self._get_user_url(role_name)
        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth) as resp:
            if resp.status != HTTPNoContent.status_code:
                raise ClientError(f"Server return unexpected result: {resp.status}.")
        return None

    def _get_user_url(self, user: str) -> URL:
        if ":" in user:
            raise ValueError(f"Invalid name: {user!r}")
        return self._config.api_url / "users" / user.replace("/", ":")


def _permission_to_api(perm: Permission) -> dict[str, Any]:
    primitive: dict[str, Any] = {"uri": str(perm.uri), "action": perm.action.value}
    return primitive
