from dataclasses import dataclass
from typing import AsyncIterator, Optional

from ._config import Config
from ._core import _Core
from ._rewrite import rewrite_module
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager


@rewrite_module
@dataclass(frozen=True)
class AppInstance:
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

    @asyncgeneratorcontextmanager
    async def list(
        self,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> AsyncIterator[AppInstance]:
        cluster_name = cluster_name or self._config.cluster_name
        org_name = org_name or self._config.org_name
        project_name = project_name or self._config.project_name

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
            / "instances"
        )

        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            data = await resp.json()
            for item in data["items"]:
                yield AppInstance(
                    id=item["id"],
                    name=item["name"],
                    display_name=item["display_name"],
                    template_name=item["template_name"],
                    template_version=item["template_version"],
                    project_name=item["project_name"],
                    org_name=item["org_name"],
                    state=item["state"],
                )
