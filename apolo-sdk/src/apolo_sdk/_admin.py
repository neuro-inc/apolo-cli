# Admin API is experimental,
# remove underscore prefix after stabilizing and making public
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional, Union

import aiohttp
from neuro_admin_client import AdminClientBase
from neuro_admin_client import Balance as _Balance
from neuro_admin_client import Cluster as _Cluster
from neuro_admin_client import ClusterUser as _ClusterUser
from neuro_admin_client import ClusterUserRoleType as _ClusterUserRoleType
from neuro_admin_client import ClusterUserWithInfo as _ClusterUserWithInfo
from neuro_admin_client import Org as _Org
from neuro_admin_client import OrgCluster as _OrgCluster
from neuro_admin_client import OrgUser as _OrgUser
from neuro_admin_client import OrgUserRoleType as _OrgUserRoleType
from neuro_admin_client import OrgUserWithInfo as _OrgUserWithInfo
from neuro_admin_client import Project as _Project
from neuro_admin_client import ProjectUser as _ProjectUser
from neuro_admin_client import ProjectUserRoleType as _ProjectUserRoleType
from neuro_admin_client import ProjectUserWithInfo as _ProjectUserWithInfo
from neuro_admin_client import Quota as _Quota
from neuro_admin_client import UserInfo as _UserInfo
from yarl import URL, Query

from ._config import Config
from ._core import _Core
from ._errors import NotSupportedError
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor

# Explicit __all__ to re-export neuro_admin_client entities

__all__ = [
    "_Admin",
    "_Balance",
    "_Cluster",
    "_ClusterUser",
    "_ClusterUserRoleType",
    "_ClusterUserWithInfo",
    "_Org",
    "_OrgCluster",
    "_OrgUser",
    "_OrgUserRoleType",
    "_OrgUserWithInfo",
    "_Project",
    "_ProjectUser",
    "_ProjectUserRoleType",
    "_ProjectUserWithInfo",
    "_Quota",
    "_UserInfo",
]


@rewrite_module
class _Admin(AdminClientBase, metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config) -> None:
        self._core = core
        self._config = config

    @property
    def _admin_url(self) -> URL:
        url = self._config.admin_url
        if not url:
            raise NotSupportedError("admin API is not supported by server")
        else:
            return url

    @asynccontextmanager
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Union[Query, None] = None,
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        url = self._admin_url / path
        auth = await self._config._api_auth()
        async with self._core.request(
            method=method,
            url=url,
            params=params,
            json=json,
            auth=auth,
        ) as resp:
            yield resp
