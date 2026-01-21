from collections.abc import Awaitable, Callable
from pathlib import Path

import aiohttp
from yarl import URL

from ._abc import (
    AbstractDeleteProgress,
    AbstractDockerImageProgress,
    AbstractFileProgress,
    AbstractRecursiveFileProgress,
    ImageCommitFinished,
    ImageCommitStarted,
    ImageProgressPull,
    ImageProgressPush,
    ImageProgressSave,
    ImageProgressStep,
    StorageProgressComplete,
    StorageProgressDelete,
    StorageProgressEnterDir,
    StorageProgressFail,
    StorageProgressLeaveDir,
    StorageProgressStart,
    StorageProgressStep,
)
from ._admin import (
    _Admin,
    _Balance,
    _Cluster,
    _ClusterUser,
    _ClusterUserRoleType,
    _ClusterUserWithInfo,
    _Org,
    _OrgCluster,
    _OrgUser,
    _OrgUserRoleType,
    _OrgUserWithInfo,
    _Project,
    _ProjectUser,
    _ProjectUserRoleType,
    _ProjectUserWithInfo,
    _Quota,
    _UserInfo,
)
from ._apps import (
    App,
    AppConfigurationRevision,
    AppEvent,
    AppEventResource,
    Apps,
    AppState,
    AppTemplate,
    AppValue,
)
from ._bucket_base import (
    BlobCommonPrefix,
    BlobObject,
    Bucket,
    BucketCredentials,
    BucketEntry,
    PersistentBucketCredentials,
)
from ._buckets import Buckets
from ._client import Client
from ._clusters import (
    _AMDGPU,
    _AMDGPUPreset,
    _Clusters,
    _ConfigCluster,
    _EnergyConfig,
    _EnergySchedule,
    _EnergySchedulePeriod,
    _IntelGPU,
    _IntelGPUPreset,
    _NvidiaGPU,
    _NvidiaGPUPreset,
    _ResourcePoolType,
    _ResourcePreset,
    _TPUPreset,
    _TPUResource,
)
from ._config import Config
from ._config_factory import (
    CONFIG_ENV_NAME,
    DEFAULT_API_URL,
    DEFAULT_CONFIG_PATH,
    PASS_CONFIG_ENV_NAME,
    Factory,
)
from ._core import DEFAULT_TIMEOUT
from ._disks import Disk, Disks
from ._errors import (
    AuthenticationError,
    AuthError,
    AuthorizationError,
    BadGateway,
    ClientError,
    ConfigError,
    IllegalArgumentError,
    NDJSONError,
    NotSupportedError,
    ResourceNotFound,
    ServerNotAvailable,
    StdStreamError,
)
from ._file_filter import AsyncFilterFunc, FileFilter
from ._images import Images
from ._jobs import (
    Container,
    HTTPPort,
    JobDescription,
    JobPriority,
    JobRestartPolicy,
    Jobs,
    JobStatus,
    JobStatusHistory,
    JobStatusItem,
    JobTelemetry,
    Resources,
    StdStream,
)
from ._parser import (
    DiskVolume,
    EnvParseResult,
    Parser,
    SecretFile,
    Volume,
    VolumeParseResult,
)
from ._parsing_utils import LocalImage, RemoteImage, Tag, TagOption
from ._plugins import ConfigBuilder, ConfigScope, PluginManager, VersionChecker
from ._secrets import Secret, Secrets
from ._server_cfg import AppsConfig, Cluster, Preset, Project, ResourcePool
from ._service_accounts import ServiceAccount, ServiceAccounts
from ._storage import DiskUsageInfo, FileStatus, FileStatusType, Storage
from ._tracing import gen_trace_id
from ._url_utils import CLUSTER_SCHEMES as SCHEMES
from ._users import Action, Permission, Quota, Share, Users
from ._utils import _ContextManager, find_project_root
from ._vcluster import KubeServiceAccount, VCluster

__version__ = "26.1.0"


__all__ = (
    "AbstractDeleteProgress",
    "AbstractDockerImageProgress",
    "AbstractFileProgress",
    "AbstractRecursiveFileProgress",
    "Action",
    "App",
    "AppConfigurationRevision",
    "AppEvent",
    "AppEventResource",
    "AppState",
    "AppTemplate",
    "AppValue",
    "Apps",
    "AppsConfig",
    "AsyncFilterFunc",
    "AuthError",
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "BadGateway",
    "BlobCommonPrefix",
    "BlobObject",
    "Bucket",
    "BucketCredentials",
    "BucketEntry",
    "Buckets",
    "CONFIG_ENV_NAME",
    "Client",
    "ClientError",
    "Cluster",
    "Config",
    "ConfigBuilder",
    "ConfigError",
    "ConfigScope",
    "Container",
    "DEFAULT_API_URL",
    "DEFAULT_CONFIG_PATH",
    "Disk",
    "DiskUsageInfo",
    "DiskVolume",
    "Disks",
    "EnvParseResult",
    "Factory",
    "FileFilter",
    "FileStatus",
    "FileStatusType",
    "HTTPPort",
    "IllegalArgumentError",
    "ImageCommitFinished",
    "ImageCommitStarted",
    "ImageProgressPull",
    "ImageProgressPush",
    "ImageProgressSave",
    "ImageProgressStep",
    "Images",
    "JobDescription",
    "JobPriority",
    "JobRestartPolicy",
    "JobStatus",
    "JobStatusHistory",
    "JobStatusItem",
    "JobTelemetry",
    "Jobs",
    "KubeServiceAccount",
    "LocalImage",
    "NDJSONError",
    "NotSupportedError",
    "PASS_CONFIG_ENV_NAME",
    "Parser",
    "Permission",
    "PersistentBucketCredentials",
    "PluginManager",
    "Preset",
    "Project",
    "Quota",
    "RemoteImage",
    "ResourceNotFound",
    "ResourcePool",
    "Resources",
    "SCHEMES",
    "Secret",
    "SecretFile",
    "Secrets",
    "ServerNotAvailable",
    "ServiceAccount",
    "ServiceAccounts",
    "Share",
    "StdStream",
    "StdStreamError",
    "Storage",
    "StorageProgressComplete",
    "StorageProgressDelete",
    "StorageProgressEnterDir",
    "StorageProgressFail",
    "StorageProgressLeaveDir",
    "StorageProgressStart",
    "StorageProgressStep",
    "Tag",
    "TagOption",
    "Users",
    "VCluster",
    "VersionChecker",
    "Volume",
    "VolumeParseResult",
    "_AMDGPU",
    "_AMDGPUPreset",
    "_Admin",
    "_Balance",
    "_Cluster",
    "_ClusterUser",
    "_ClusterUserRoleType",
    "_ClusterUserWithInfo",
    "_Clusters",
    "_ConfigCluster",
    "_EnergyConfig",
    "_EnergySchedule",
    "_EnergySchedulePeriod",
    "_IntelGPU",
    "_IntelGPUPreset",
    "_NvidiaGPU",
    "_NvidiaGPUPreset",
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
    "_ResourcePoolType",
    "_ResourcePreset",
    "_TPUPreset",
    "_TPUResource",
    "_UserInfo",
    "__version__",
    "find_project_root",
    "gen_trace_id",
    "get",
    "login",
    "login_with_token",
    "logout",
)


def get(
    *,
    path: Path | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
    trace_configs: list[aiohttp.TraceConfig] | None = None,
) -> _ContextManager[Client]:
    return _ContextManager[Client](_get(path, timeout, trace_configs))


async def _get(
    path: Path | None,
    timeout: aiohttp.ClientTimeout,
    trace_configs: list[aiohttp.TraceConfig] | None,
) -> Client:
    return await Factory(path, trace_configs).get(timeout=timeout)


async def login(
    show_browser_cb: Callable[[URL], Awaitable[None]],
    *,
    url: URL = DEFAULT_API_URL,
    path: Path | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
) -> None:
    await Factory(path).login(show_browser_cb, url=url, timeout=timeout)


async def login_with_token(
    token: str,
    *,
    url: URL = DEFAULT_API_URL,
    path: Path | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
) -> None:
    await Factory(path).login_with_token(token, url=url, timeout=timeout)


async def login_headless(
    get_auth_code_cb: Callable[[URL], Awaitable[str]],
    *,
    url: URL = DEFAULT_API_URL,
    path: Path | None = None,
    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
) -> None:
    await Factory(path).login_headless(get_auth_code_cb, url=url, timeout=timeout)


async def logout(
    *,
    path: Path | None = None,
    show_browser_cb: Callable[[URL], Awaitable[None]] | None = None,
) -> None:
    await Factory(path).logout(show_browser_cb)
