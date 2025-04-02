import abc
import os
import re
from datetime import datetime, timedelta
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import quote, unquote

import click
from click import BadParameter
from click.shell_completion import (
    BashComplete,
    CompletionItem,
    ZshComplete,
    add_completion_class,
)
from yarl import URL

from apolo_sdk import (
    Client,
    LocalImage,
    Preset,
    Project,
    RemoteImage,
    ResourceNotFound,
    TagOption,
)

from .asyncio_utils import asyncgeneratorcontextmanager
from .parse_utils import (
    JobTableFormat,
    parse_memory,
    parse_ps_columns,
    parse_top_columns,
)
from .root import Root

JOB_NAME_MIN_LENGTH = 3
JOB_NAME_MAX_LENGTH = 40
JOB_NAME_PATTERN = "^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
JOB_NAME_REGEX = re.compile(JOB_NAME_PATTERN)
JOB_LIMIT_ENV = "NEURO_CLI_JOB_AUTOCOMPLETE_LIMIT"


DISK_NAME_MIN_LENGTH = 3
DISK_NAME_MAX_LENGTH = 40
DISK_NAME_PATTERN = "^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
DISK_NAME_REGEX = re.compile(JOB_NAME_PATTERN)


BUCKET_NAME_MIN_LENGTH = 3
BUCKET_NAME_MAX_LENGTH = 40
BUCKET_NAME_PATTERN = "^[a-z][a-z0-9_]*(?:-+[a-z0-9_]+)*$"
BUCKET_NAME_REGEX = re.compile(BUCKET_NAME_PATTERN)


_T = TypeVar("_T")


class AsyncType(click.ParamType, Generic[_T], abc.ABC):
    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> _T:
        assert ctx is not None
        root = cast(Root, ctx.obj)
        return root.run(self.async_convert(root, value, param, ctx))

    @abc.abstractmethod
    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> _T:
        pass

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        root = cast(Root, ctx.obj)
        return root.run(self.async_shell_complete(root, ctx, param, incomplete))

    @abc.abstractmethod
    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        pass


class LocalImageType(click.ParamType):
    name = "local_image"

    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> LocalImage:
        assert ctx is not None
        root = cast(Root, ctx.obj)
        client = root.run(root.init_client())
        return client.parse.local_image(value)


def _complete_clusters(
    client: Client,
    prefix: str,
    incomplete: str,
) -> List[CompletionItem]:
    return [
        CompletionItem(f"{name}/", type="uri", prefix=prefix)
        for name in client.config.clusters
        if name.startswith(incomplete)
    ]


class RemoteImageType(AsyncType[RemoteImage]):
    name = "image"

    def __init__(self, tag_option: TagOption = TagOption.DEFAULT) -> None:
        self.tag_option = tag_option

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> RemoteImage:
        client = await root.init_client()
        cluster_name = client.cluster_name
        if ctx:
            cluster_name = ctx.params.get("cluster", client.cluster_name)
        return client.parse.remote_image(
            value, tag_option=self.tag_option, cluster_name=cluster_name
        )

    async def _complete_image_names(
        self,
        client: Client,
        uri_prefix: str,
        path_prefix: str,
        cluster_name: str,
        incomplete: str,
    ) -> List[CompletionItem]:
        if cluster_name not in client.config.clusters:
            return []
        names = []
        prefix = f"{path_prefix}{unquote(incomplete)}"
        for image in await client.images.list(cluster_name):
            path = f"{image.project_name}/{image.name}"
            if image.org_name:
                path = f"{image.org_name}/{path}"
            if path.startswith(prefix):
                names.append(incomplete + quote(path[len(prefix) :]))
        return [CompletionItem(name, type="uri", prefix=uri_prefix) for name in names]

    async def _complete_image_tags(
        self,
        client: Client,
        image_str: str,
        incomplete: str,
    ) -> List[CompletionItem]:
        image = client.parse.remote_image(image_str, tag_option=TagOption.DENY)
        result = []
        for image_tag in await client.images.tags(image):
            assert image_tag.tag
            if image_tag.tag.startswith(incomplete):
                result.append(
                    CompletionItem(image_tag.tag, type="uri", prefix=image_str + ":")
                )
        return result

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        if "image".startswith(incomplete):
            return [CompletionItem("image:", type="uri", prefix="")]

        async with await root.init_client() as client:
            if incomplete.startswith("image:") and client.config.project_name:
                incomplete = incomplete[len("image:") :]
                if self.tag_option != TagOption.DENY and ":" in incomplete:
                    prefix, incomplete = incomplete.split(":", 1)
                    return await self._complete_image_tags(
                        client, f"image:{prefix}", incomplete
                    )

                if incomplete.startswith("///"):
                    return []

                if incomplete.startswith("//"):
                    incomplete = incomplete[2:]
                    if "/" not in incomplete:
                        return _complete_clusters(client, "image://", incomplete)
                    cluster_name, incomplete = incomplete.split("/", 1)
                    return await self._complete_image_names(
                        client, f"image://{cluster_name}/", "", cluster_name, incomplete
                    )

                if incomplete.startswith("/"):
                    incomplete = incomplete[1:]
                    return await self._complete_image_names(
                        client, "image:/", "", client.cluster_name, incomplete
                    )

                path_prefix = f"{client.config.project_name}/"
                if client.config.org_name:
                    path_prefix = f"{client.config.org_name}/{path_prefix}"
                return await self._complete_image_names(
                    client, "image:", path_prefix, client.cluster_name, incomplete
                )

            return []


class RemoteTaglessImageType(RemoteImageType):
    def __init__(self, tag_option: TagOption = TagOption.DENY) -> None:
        super().__init__(tag_option=TagOption.DENY)


class LocalRemotePortParamType(click.ParamType):
    name = "local-remote-port-pair"

    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> Tuple[int, int]:
        try:
            local_str, remote_str = value.split(":")
            local, remote = int(local_str), int(remote_str)
            if not (0 < local <= 65535 and 0 < remote <= 65535):
                raise ValueError("Port should be in range 1 to 65535")
            return local, remote
        except ValueError as e:
            raise BadParameter(f"{value} is not a valid port combination: {e}")


LOCAL_REMOTE_PORT = LocalRemotePortParamType()


class MemoryType(click.ParamType):
    name = "memory_amount"

    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> int:
        if isinstance(value, int):
            return int(value)
        return parse_memory(value)


MEMORY = MemoryType()


class JobNameType(click.ParamType):
    name = "job_name"

    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> str:
        if (
            len(value) < JOB_NAME_MIN_LENGTH
            or len(value) > JOB_NAME_MAX_LENGTH
            or JOB_NAME_REGEX.match(value) is None
        ):
            raise ValueError(
                f"Invalid job name '{value}'.\n"
                "The name can only contain lowercase letters, numbers and hyphens "
                "with the following rules: \n"
                "  - the first character must be a letter; \n"
                "  - each hyphen must be surrounded by non-hyphen characters; \n"
                f"  - total length must be between {JOB_NAME_MIN_LENGTH} and "
                f"{JOB_NAME_MAX_LENGTH} characters long."
            )
        return value


JOB_NAME = JobNameType()


class DiskNameType(click.ParamType):
    name = "disk_name"

    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> str:
        if (
            len(value) < DISK_NAME_MIN_LENGTH
            or len(value) > DISK_NAME_MAX_LENGTH
            or DISK_NAME_REGEX.match(value) is None
        ):
            raise ValueError(
                f"Invalid disk name '{value}'.\n"
                "The name can only contain lowercase letters, numbers and hyphens "
                "with the following rules: \n"
                "  - the first character must be a letter; \n"
                "  - each hyphen must be surrounded by non-hyphen characters; \n"
                f"  - total length must be between {DISK_NAME_MIN_LENGTH} and "
                f"{DISK_NAME_MAX_LENGTH} characters long."
            )
        return value


DISK_NAME = DiskNameType()


class BucketNameType(click.ParamType):
    name = "bucket_name"

    def convert(
        self, value: str, param: Optional[click.Parameter], ctx: Optional[click.Context]
    ) -> str:
        if (
            len(value) < BUCKET_NAME_MIN_LENGTH
            or len(value) > BUCKET_NAME_MAX_LENGTH
            or BUCKET_NAME_REGEX.match(value) is None
        ):
            raise ValueError(
                f"Invalid bucket name '{value}'.\n"
                "The name can only contain lowercase letters, numbers and "
                "hyphens and underscores with the following rules: \n"
                "  - the first character must be a letter; \n"
                "  - each hyphen/underscore must be surrounded by non-hyphen "
                "characters; \n"
                f"  - total length must be between {BUCKET_NAME_MIN_LENGTH} and "
                f"{BUCKET_NAME_MAX_LENGTH} characters long."
            )
        return value


BUCKET_NAME = BucketNameType()


class JobColumnsType(click.ParamType):
    name = "columns"

    def convert(
        self,
        value: Union[str, JobTableFormat],
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> JobTableFormat:
        if isinstance(value, list):
            return value
        return parse_ps_columns(value)


JOB_COLUMNS = JobColumnsType()


class TopColumnsType(click.ParamType):
    name = "columns"

    def convert(
        self,
        value: Union[str, JobTableFormat],
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> JobTableFormat:
        if isinstance(value, list):
            return value
        return parse_top_columns(value)


TOP_COLUMNS = TopColumnsType()


class PresetType(AsyncType[str]):
    name = "preset"

    def _get_presets(
        self, ctx: Optional[click.Context], client: Client
    ) -> Mapping[str, Preset]:
        cluster_name = client.cluster_name
        if ctx:
            cluster_name = ctx.params.get("cluster", client.cluster_name)
        if cluster_name not in client.config.clusters:
            return {}
        return client.config.clusters[cluster_name].presets

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        client = await root.init_client()
        if value not in self._get_presets(ctx, client):
            cluster_name = client.cluster_name
            if ctx:
                cluster_name = ctx.params.get("cluster", client.cluster_name)
            if cluster_name != client.cluster_name:
                error_message = (
                    f"Preset {value} is not valid for cluster {cluster_name}."
                )
            else:
                error_message = f"Preset {value} is not valid, "
                "run 'apolo config show' to get a list of available presets"
            raise click.BadParameter(
                error_message,
                ctx,
                param,
            )
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        # async context manager is used to prevent a message about
        # unclosed session
        async with await root.init_client() as client:
            presets = list(self._get_presets(ctx, client))
            return [CompletionItem(p) for p in presets if p.startswith(incomplete)]


PRESET = PresetType()


class ClusterType(AsyncType[str]):
    name = "cluster"

    def __init__(self, allow_unknown: bool = False):
        self._allow_unknown = allow_unknown

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        if self._allow_unknown:
            return value
        client = await root.init_client()
        if value not in client.config.clusters:
            raise click.BadParameter(
                f"Cluster {value} is not valid, "
                "run 'apolo config get-clusters' to get a list of available clusters",
                ctx,
                param,
            )
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        # async context manager is used to prevent a message about
        # unclosed session
        async with await root.init_client() as client:
            clusters = list(client.config.clusters)
            return [CompletionItem(c) for c in clusters if c.startswith(incomplete)]


CLUSTER = ClusterType()
CLUSTER_ALLOW_UNKNOWN = ClusterType(allow_unknown=True)


class OrgType(AsyncType[str]):
    name = "org"

    def __init__(self, allow_unknown: bool = False):
        self._allow_unknown = allow_unknown

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        if self._allow_unknown:
            return value
        client = await root.init_client()
        org_name = value
        if org_name not in client.config.available_orgs:
            avail = ", ".join(client.config.available_orgs)
            raise click.BadParameter(
                f"Org {value} is not valid, " f"available orgs are {{{avail}}}",
                ctx,
                param,
            )
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        # async context manager is used to prevent a message about
        # unclosed session
        async with await root.init_client() as client:
            org_names = client.config.available_orgs
            return [
                CompletionItem(org_name)
                for org_name in org_names
                if org_name.startswith(incomplete)
            ]


ORG = OrgType()
ORG_ALLOW_UNKNOWN = OrgType(allow_unknown=True)


class ProjectType(AsyncType[str]):
    name = "project"

    def __init__(self, allow_unknown: bool = False):
        self._allow_unknown = allow_unknown

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        if self._allow_unknown:
            return value
        client = await root.init_client()
        cluster_name = root.client.config.cluster_name
        org_name = root.client.config.org_name
        project_key = Project.Key(
            cluster_name=cluster_name, org_name=org_name, project_name=value
        )
        if project_key not in client.config.projects:
            raise click.BadParameter(
                f"Project {value} is not valid, "
                "run 'apolo admin get-projects' to get a list of available projects",
                ctx,
                param,
            )
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        # async context manager is used to prevent a message about
        # unclosed session
        async with await root.init_client() as client:
            projects = client.config.cluster_org_projects
            return [
                CompletionItem(p.name)
                for p in projects
                if p.name.startswith(incomplete)
            ]


PROJECT = ProjectType()
PROJECT_ALLOW_UNKNOWN = ProjectType(allow_unknown=True)


class JobType(AsyncType[str]):
    name = "job"

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        return value

    async def _complete_job_projects(
        self,
        client: Client,
        prefix: str,
        cluster_name: str,
        incomplete: str,
    ) -> List[CompletionItem]:
        if cluster_name not in client.config.clusters:
            return []
        completions = []
        for project_key in client.config.projects.keys():
            if project_key.cluster_name != cluster_name:
                continue
            if project_key.project_name.startswith(incomplete):
                completions.append(
                    CompletionItem(
                        f"{project_key.project_name}/", type="uri", prefix=prefix
                    )
                )
        return completions

    async def _complete_job_names(
        self,
        client: Client,
        prefix: str,
        cluster_name: str,
        project_name: Optional[str],
        incomplete: str,
    ) -> List[CompletionItem]:
        if cluster_name not in client.config.clusters:
            return []
        now = datetime.now()
        limit = int(os.environ.get(JOB_LIMIT_ENV, 100))
        names = {}
        async with client.jobs.list(
            since=now - timedelta(days=7),
            reverse=True,
            limit=limit,
            cluster_name=cluster_name,
            project_names=(project_name,) if project_name else (),
        ) as it:
            async for job in it:
                id = job.id
                name = job.name
                if id.startswith(incomplete):
                    names[id] = name
                if name and name.startswith(incomplete):
                    names[name] = id
        if prefix:
            return [CompletionItem(name, type="uri", prefix=prefix) for name in names]
        else:
            return [CompletionItem(name, help=help) for name, help in names.items()]

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        if "job".startswith(incomplete):
            return [CompletionItem("job:", type="uri", prefix="")]

        async with await root.init_client() as client:
            if incomplete.startswith("job:///"):
                return []

            if incomplete.startswith("job://"):
                parts = incomplete[len("job://") :].split("/")
                if len(parts) == 1:
                    return _complete_clusters(client, "job://", *parts)
                elif len(parts) == 2:
                    return await self._complete_job_projects(
                        client, f"job://{parts[0]}/", *parts
                    )
                elif len(parts) == 3:
                    return await self._complete_job_names(
                        client, f"job://{parts[0]}/{parts[1]}/", *parts
                    )
                return []

            if incomplete.startswith("job:/"):
                parts = incomplete[len("job:/") :].split("/")
                if len(parts) == 1:
                    return await self._complete_job_projects(
                        client, "job:/", client.cluster_name, *parts
                    )
                elif len(parts) == 2:
                    return await self._complete_job_names(
                        client, f"job:/{parts[0]}/", client.cluster_name, *parts
                    )
                return []

            if incomplete.startswith("job:"):
                parts = incomplete[len("job:") :].split("/")
                if len(parts) == 1:
                    return await self._complete_job_names(
                        client,
                        "job:",
                        client.cluster_name,
                        client.config.project_name,
                        *parts,
                    )
                return []

            return await self._complete_job_names(
                client, "", client.cluster_name, client.config.project_name, incomplete
            )


JOB = JobType()


def _complete_id_name(
    id: str, name: Optional[str], incomplete: str
) -> Iterator[CompletionItem]:
    if id.startswith(incomplete):
        yield CompletionItem(id, help=name or "")
    if name and name.startswith(incomplete):
        yield CompletionItem(name, help=id)


class DiskType(AsyncType[str]):
    name = "disk"

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        async with await root.init_client() as client:
            ret: List[CompletionItem] = []
            async with client.disks.list(cluster_name=ctx.params.get("cluster")) as it:
                async for disk in it:
                    ret.extend(_complete_id_name(disk.id, disk.name, incomplete))
            return ret


DISK = DiskType()


class ServiceAccountType(AsyncType[str]):
    name = "service_account"

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        async with await root.init_client() as client:
            ret: List[CompletionItem] = []
            async with client.service_accounts.list() as it:
                async for account in it:
                    ret.extend(_complete_id_name(account.id, account.name, incomplete))

            return ret


SERVICE_ACCOUNT = ServiceAccountType()


class URLCompleter(abc.ABC):
    @abc.abstractmethod
    def get_completions(
        self,
        uri: URL,
        root: Root,
        incomplete: str,
    ) -> AsyncIterator[CompletionItem]:
        pass


class PathURLCompleter(URLCompleter, abc.ABC):
    class DirEntry(Protocol):
        @property
        def name(self) -> str: ...

        def is_dir(self) -> bool: ...

    def __init__(
        self,
        complete_dir: bool = True,
        complete_file: bool = True,
    ) -> None:
        self._complete_dir = complete_dir
        self._complete_file = complete_file

    def _split_uri(self, uri: URL, incomplete: str) -> Tuple[URL, str]:
        if incomplete.endswith("/") or incomplete == uri.scheme + ":":
            return uri, ""
        return uri.parent, uri.name

    def _make_item(
        self,
        parent: URL,
        name: str,
        is_dir: bool,
    ) -> CompletionItem:
        if is_dir:
            name += "/"
        ppath = parent.path
        prefix = str(parent)
        if (parent.host and ppath == "/") or (ppath and not ppath.endswith("/")):
            if prefix and not prefix.endswith("/"):
                prefix += "/"
        return CompletionItem(
            name,
            type="uri",
            prefix=prefix,
        )

    @abc.abstractmethod
    async def _is_valid_dir(self, root: Root, uri: URL) -> bool:
        pass

    @abc.abstractmethod
    def _iter_dir(
        self, root: Root, uri: URL
    ) -> AsyncContextManager[AsyncIterator["PathURLCompleter.DirEntry"]]:
        pass

    async def get_completions(
        self,
        uri: URL,
        root: Root,
        incomplete: str,
    ) -> AsyncIterator[CompletionItem]:
        dir_uri, incomplete_name = self._split_uri(uri, incomplete)
        if not await self._is_valid_dir(root, dir_uri):
            return
        async with self._iter_dir(root, dir_uri) as it:
            async for item in it:
                if item.name.startswith(incomplete_name):
                    if item.is_dir() and not self._complete_dir:
                        continue
                    if not item.is_dir() and not self._complete_file:
                        continue

                    yield self._make_item(
                        dir_uri,
                        item.name,
                        item.is_dir(),
                    )


class FilePathURLCompleter(PathURLCompleter):
    async def _is_valid_dir(self, root: Root, uri: URL) -> bool:
        path = root.client.parse.uri_to_path(uri)
        return path.exists() and path.is_dir()

    @asyncgeneratorcontextmanager
    async def _iter_dir(
        self, root: Root, uri: URL
    ) -> AsyncIterator[PathURLCompleter.DirEntry]:
        path = root.client.parse.uri_to_path(uri)
        for item in path.iterdir():
            yield item


class StoragePathURLCompleter(PathURLCompleter):
    async def _is_valid_dir(self, root: Root, uri: URL) -> bool:
        try:
            stat = await root.client.storage.stat(uri)
        except ResourceNotFound:
            return False
        return stat.is_dir()

    @asyncgeneratorcontextmanager
    async def _iter_dir(
        self, root: Root, uri: URL
    ) -> AsyncIterator[PathURLCompleter.DirEntry]:
        async with root.client.storage.list(uri) as it:
            async for fstat in it:
                yield fstat


class BlobPathURLCompleter(PathURLCompleter):
    async def _is_valid_dir(self, root: Root, uri: URL) -> bool:
        # Not used
        raise NotImplementedError

    @asyncgeneratorcontextmanager
    async def _iter_dir(
        self, root: Root, uri: URL
    ) -> AsyncIterator[PathURLCompleter.DirEntry]:
        # Not used
        raise NotImplementedError
        yield

    async def get_completions(
        self,
        uri: URL,
        root: Root,
        incomplete: str,
    ) -> AsyncIterator[CompletionItem]:
        full_uri = root.client.parse.normalize_uri(uri)
        if not self._is_bucket_uri_complete(full_uri, root, incomplete):
            prefix = uri.parent
            full_prefix = full_uri.parent if uri.path else full_uri
            full_prefix_str = str(full_prefix)
            full_uri_str = str(full_uri) if uri.path else str(full_uri) + "/"
            completions = set()
            async with root.client.buckets.list(cluster_name=full_uri.host) as it:
                async for bucket in it:
                    bucket_uris = [bucket.uri]
                    if bucket.name:
                        bucket_uris = [bucket.uri.parent / bucket.id] + bucket_uris
                    for bucket_uri in bucket_uris:
                        bucket_uri_str = str(bucket_uri)
                        if not bucket_uri_str.startswith(full_uri_str):
                            continue
                        path_parts = bucket_uri_str[len(full_prefix_str) :].split("/")
                        if path_parts and not path_parts[0]:
                            del path_parts[0]
                        if len(path_parts) == 0:
                            continue
                        name = path_parts[0]
                        if name not in completions:
                            completions.add(name)
                            yield self._make_item(prefix, name, True)
        else:
            # Generic get_completions() is not used here because we can
            # benefit from prefix search in list_blobs().
            if incomplete.endswith("/"):
                prefix = uri
                full_uri = URL(str(full_uri) + "/")
                skip_uri_len = len(full_uri.parts)
            else:
                prefix = uri.parent
                skip_uri_len = None

            async with root.client.buckets.list_blobs(full_uri) as it:
                async for item in it:
                    if item.is_dir():
                        if not self._complete_dir:
                            continue
                        # Directory itself is also listed as it is prefix search
                        if len(item.uri.parts) == skip_uri_len:
                            continue
                    else:
                        if not self._complete_file:
                            continue

                    yield self._make_item(prefix, item.name, item.is_dir())

    def _is_bucket_uri_complete(self, uri: URL, root: Root, incomplete: str) -> bool:
        parts = uri.parts
        if len(parts) > 4:
            # Check uri has format blob://cluster/org/project/bucket/
            return True
        if len(parts) == 4 or (
            len(parts) == 3 and parts[-1] and incomplete.endswith("/")
        ):
            assert uri.host
            cluster = root.client.config.clusters.get(uri.host)
            # Check uri has format blob://cluster/project/bucket/
            return bool(cluster and parts[1] not in cluster.orgs)
        return False


class PlatformURIType(AsyncType[URL]):
    name = "uri"

    def __init__(
        self,
        *,
        allowed_schemes: Iterable[str] = ("file", "storage", "blob"),
        complete_dir: bool = True,
        complete_file: bool = True,
    ) -> None:
        self._allowed_schemes = list(allowed_schemes)
        self._complete_dir = complete_dir
        self._complete_file = complete_file
        self._completers: Mapping[str, URLCompleter] = {
            "file": FilePathURLCompleter(complete_dir, complete_file),
            "storage": StoragePathURLCompleter(complete_dir, complete_file),
            "blob": BlobPathURLCompleter(complete_dir, complete_file),
        }

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> URL:
        await root.init_client()
        return root.client.parse.str_to_uri(
            value,
            allowed_schemes=self._allowed_schemes,
            short=False,
        )

    async def _find_matches(self, incomplete: str, root: Root) -> List[CompletionItem]:
        ret: List[CompletionItem] = []
        for scheme in self._allowed_schemes:
            scheme += ":"
            if incomplete.startswith(scheme):
                # found valid scheme, try to resolve path
                break
            if scheme.startswith(incomplete):
                ret.append(CompletionItem(scheme, type="uri", prefix=""))
        else:
            return ret

        if scheme != "file:" and incomplete == scheme + "//":
            return _complete_clusters(root.client, incomplete, "")

        uri = root.client.parse.str_to_uri(
            incomplete,
            allowed_schemes=self._allowed_schemes,
            short=not (
                incomplete.startswith(scheme + "//")
                and not incomplete.startswith(scheme + "///")
            ),
        )
        if (
            uri.scheme != "file"
            and uri.host
            and uri.path == "/"
            and not incomplete.endswith("/")
        ):
            # Cluster name is incomplete
            return _complete_clusters(root.client, f"{uri.scheme}://", uri.host)
        completer = self._completers.get(uri.scheme)
        if completer:
            return [
                item async for item in completer.get_completions(uri, root, incomplete)
            ]
        return []

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        async with await root.init_client():
            ret = await self._find_matches(incomplete, root)
            return ret


_SOURCE_ZSH = """\
#compdef %(prog_name)s

%(complete_func)s() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    local -a uris
    local prefix
    (( ! $+commands[%(prog_name)s] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) \
%(complete_var)s=zsh_complete %(prog_name)s)}")

    for type key descr pre in ${response}; do
        if [[ "$type" == "uri" ]]; then
            uris+=("$key")
            if [[ $pre != "_" ]]; then
                prefix="$pre"
            fi
        elif [[ "$type" == "plain" ]]; then
            if [[ "$descr" == "_" ]]; then
                completions+=("$key")
            else
                completions_with_descriptions+=("$key":"$descr")
            fi
        elif [[ "$type" == "dir" ]]; then
            _path_files -/
        elif [[ "$type" == "file" ]]; then
            _path_files -f
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi

    if [ -n "$uris" ]; then
        compset -S '[^:/]*' && compstate[to_end]=''
        compadd -P "$prefix" -S '' -U -V unsorted -a uris
    fi
}

compdef %(complete_func)s %(prog_name)s;
"""


class NewZshComplete(ZshComplete):
    source_template = _SOURCE_ZSH

    def format_completion(self, item: CompletionItem) -> str:
        return f"{item.type}\n{item.value}\n{item.help or '_'}\n{item.prefix or '_'}"


_SOURCE_BASH = """\
%(complete_func)s() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD \
%(complete_var)s=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value prefix <<< "$completion"

        if [[ $type == 'uri' ]]; then
            COMPREPLY+=("$prefix$value")
            compopt -o nospace
        elif [[ $type == 'dir' ]]; then
            COMREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

%(complete_func)s_setup() {
    complete -o nosort -F %(complete_func)s %(prog_name)s
}

%(complete_func)s_setup;
"""


def _merge_autocompletion_args(
    args: List[str], incomplete: str
) -> Tuple[List[str], str]:
    new_args: List[str] = []
    for arg in args:
        if arg == ":":
            if new_args:
                new_args[-1] += ":"
            else:
                new_args.append(":")
        else:
            if new_args and new_args[-1].endswith(":"):
                new_args[-1] += arg
            else:
                new_args.append(arg)

    if new_args:
        if new_args[-1].endswith(":"):
            incomplete = new_args[-1] + incomplete
            del new_args[-1]
        elif incomplete == ":":
            incomplete = new_args[-1] + ":"
            del new_args[-1]
    return new_args, incomplete


class NewBashComplete(BashComplete):
    source_template = _SOURCE_BASH

    def get_completion_args(self) -> Tuple[List[str], str]:
        args, incomplete = super().get_completion_args()
        args, incomplete = _merge_autocompletion_args(args, incomplete)
        return args, incomplete

    def format_completion(self, item: CompletionItem) -> str:
        # bash assumes ':' as a word separator along with ' '
        pre, sep, prefix = (item.prefix or "").rpartition(":")
        return f"{item.type},{item.value},{prefix}"


class BucketType(AsyncType[str]):
    name = "bucket"

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        async with await root.init_client() as client:
            ret: List[CompletionItem] = []
            async with client.buckets.list(
                cluster_name=ctx.params.get("cluster")
            ) as it:
                async for bucket in it:
                    ret.extend(_complete_id_name(bucket.id, bucket.name, incomplete))

            return ret


BUCKET = BucketType()


class BucketCredentialType(AsyncType[str]):
    name = "bucket_credential"

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> str:
        return value

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        async with await root.init_client() as client:
            ret: List[CompletionItem] = []
            async with client.buckets.persistent_credentials_list(
                cluster_name=ctx.params.get("cluster")
            ) as it:
                async for credential in it:
                    ret.extend(
                        _complete_id_name(credential.id, credential.name, incomplete)
                    )

            return ret


BUCKET_CREDENTIAL = BucketCredentialType()


class UnionType(AsyncType[Any]):
    def __init__(self, name: str, *types: AsyncType[Any]) -> None:
        self.name = name
        self._inner_types = types

    async def async_convert(
        self,
        root: Root,
        value: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Any:
        for inner_type in self._inner_types:
            try:
                return await inner_type.async_convert(root, value, param, ctx)
            except ValueError:
                pass
        raise ValueError(f"Cannot parse {value} as {self.name}")

    async def async_shell_complete(
        self, root: Root, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[CompletionItem]:
        result = []
        for inner_type in self._inner_types:
            result += await inner_type.async_shell_complete(
                root, ctx, param, incomplete
            )
        return result


def setup_shell_completion() -> None:
    add_completion_class(NewZshComplete)
    add_completion_class(NewBashComplete)
