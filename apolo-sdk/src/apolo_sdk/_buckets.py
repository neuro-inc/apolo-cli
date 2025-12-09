import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from typing import (
    AbstractSet,
    Any,
)

from dateutil.parser import isoparse
from yarl import URL

from ._abc import (
    AbstractDeleteProgress,
    AbstractFileProgress,
    AbstractRecursiveFileProgress,
)
from ._bucket_base import (
    Bucket,
    BucketCredentials,
    BucketEntry,
    BucketProvider,
    BucketUsage,
    PersistentBucketCredentials,
)
from ._config import Config
from ._core import _Core
from ._errors import NDJSONError, ResourceNotFound
from ._file_filter import (
    AsyncFilterFunc,
    _glob_safe_prefix,
    _has_magic,
    _isrecursive,
    translate,
)
from ._file_utils import FileSystem, FileTransferer, LocalFS, rm
from ._parser import Parser
from ._rewrite import rewrite_module
from ._url_utils import _extract_path, normalize_local_path_uri
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager


class BucketFS(FileSystem[PurePosixPath]):
    fs_name = "Bucket"
    supports_offset_read = True
    supports_offset_write = False

    def __init__(self, provider: BucketProvider) -> None:
        self._provider = provider

    @property
    def bucket(self) -> Bucket:
        return self._provider.bucket

    def _as_file_key(self, path: PurePosixPath) -> str:
        if not path.is_absolute():
            path = "/" / path
        return str(path).lstrip("/")

    def _as_dir_key(self, path: PurePosixPath) -> str:
        return (self._as_file_key(path) + "/").lstrip("/")

    async def exists(self, path: PurePosixPath) -> bool:
        if self._as_dir_key(path) == "":
            return True
        try:
            await self._provider.head_blob(self._as_file_key(path))
            return True
        except ResourceNotFound:
            # Maybe this is a directory?
            async with self._provider.list_blobs(
                prefix=self._as_dir_key(path), recursive=False, limit=1
            ) as it:
                return bool([entry async for entry in it])

    async def is_dir(self, path: PurePosixPath) -> bool:
        if self._as_dir_key(path) == "":
            return True
        async with self._provider.list_blobs(
            prefix=self._as_dir_key(path), recursive=False, limit=1
        ) as it:
            return bool([entry async for entry in it])

    async def is_file(self, path: PurePosixPath) -> bool:
        try:
            await self._provider.head_blob(self._as_file_key(path))
            return True
        except ResourceNotFound:
            return False

    async def stat(self, path: PurePosixPath) -> "FileSystem.BasicStat[PurePosixPath]":
        blob = await self._provider.head_blob(self._as_file_key(path))
        return FileSystem.BasicStat(
            name=path.name,
            path=path,
            size=blob.size,
            modification_time=(
                blob.modified_at.timestamp() if blob.modified_at else None
            ),
        )

    @asyncgeneratorcontextmanager
    async def read_chunks(
        self, path: PurePosixPath, offset: int = 0
    ) -> AsyncIterator[bytes]:
        async with self._provider.fetch_blob(self._as_file_key(path), offset) as it:
            async for chunk in it:
                yield chunk

    async def write_chunks(
        self,
        path: PurePosixPath,
        body: AsyncIterator[bytes],
        offset: int = 0,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        assert offset == 0, "Buckets do not support offset write"
        await self._provider.put_blob(self._as_file_key(path), body, progress)

    @asyncgeneratorcontextmanager
    async def iter_dir(self, path: PurePosixPath) -> AsyncIterator[PurePosixPath]:
        async with self._provider.list_blobs(
            prefix=self._as_dir_key(path), recursive=False
        ) as it:
            async for item in it:
                res = PurePosixPath(item.key)
                if res != path:  # Directory can be listed as self child
                    yield res

    async def mkdir(self, path: PurePosixPath) -> None:
        key = self._as_dir_key(path)
        if key == "":
            raise ValueError("Can not create a bucket root folder")
        await self._provider.put_blob(key=key, body=b"")

    async def rmdir(self, path: PurePosixPath) -> None:
        key = self._as_dir_key(path)
        if key == "":
            return  # Root dir cannot be removed
        try:
            await self._provider.delete_blob(key=key)
        except ResourceNotFound:
            pass  # Dir already removed/was a prefix - just ignore

    async def rm(self, path: PurePosixPath) -> None:
        key = self._as_file_key(path)
        await self._provider.delete_blob(key=key)

    def to_url(self, path: PurePosixPath) -> URL:
        return self._provider.bucket.uri / self._as_file_key(path)

    async def get_time_diff_to_local(self) -> tuple[float, float]:
        return await self._provider.get_time_diff_to_local()

    def parent(self, path: PurePosixPath) -> PurePosixPath:
        return path.parent

    def name(self, path: PurePosixPath) -> str:
        return path.name

    def child(self, path: PurePosixPath, child: str) -> PurePosixPath:
        return path / child


@rewrite_module
class Buckets(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config, parser: Parser) -> None:
        self._core = core
        self._config = config
        self._parser = parser
        self._providers: dict[Bucket.Provider, type[BucketProvider]] = {}

    def _parse_bucket_payload(self, payload: Mapping[str, Any]) -> Bucket:
        return Bucket(
            id=payload["id"],
            owner=payload["owner"],
            name=payload.get("name"),
            created_at=isoparse(payload["created_at"]),
            provider=Bucket.Provider(payload["provider"]),
            imported=payload.get("imported", False),
            public=payload.get("public", False),
            cluster_name=self._config.cluster_name,
            org_name=payload.get("org_name") or "",
            project_name=payload["project_name"],
        )

    def _parse_bucket_credentials_payload(
        self, payload: Mapping[str, Any]
    ) -> BucketCredentials:
        return BucketCredentials(
            bucket_id=payload["bucket_id"],
            provider=Bucket.Provider(payload["provider"]),
            credentials=payload["credentials"],
        )

    def _get_buckets_url(self, cluster_name: str | None) -> URL:
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        return self._config.get_cluster(cluster_name).buckets_url / "buckets"

    def _get_bucket_url_params(
        self,
        org_name: str | None,
        project_name: str | None,
    ) -> dict[str, Any]:
        org_name_val = org_name or self._config.org_name
        params = {
            "org_name": org_name_val or "",
            "project_name": project_name or self._config.project_name_or_raise,
        }
        return params

    @asyncgeneratorcontextmanager
    async def list(
        self,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[Bucket]:
        url = self._get_buckets_url(cluster_name)
        auth = await self._config._api_auth()
        headers = {"Accept": "application/x-ndjson"}
        params = {}
        params["org_name"] = org_name or self._config.org_name
        if project_name:
            params["project_name"] = project_name
        async with self._core.request(
            "GET", url, headers=headers, auth=auth, params=params
        ) as resp:
            if resp.headers.get("Content-Type", "").startswith("application/x-ndjson"):
                async for line in resp.content:
                    server_message = json.loads(line)
                    if "error" in server_message:
                        raise NDJSONError(server_message["error"])
                    yield self._parse_bucket_payload(server_message)
            else:
                ret = await resp.json()
                for bucket_data in ret:
                    yield self._parse_bucket_payload(bucket_data)

    async def create(
        self,
        name: str | None = None,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> Bucket:
        url = self._get_buckets_url(cluster_name)
        auth = await self._config._api_auth()
        data = {
            "name": name,
            "org_name": org_name or self._config.org_name,
            "project_name": project_name or self._config.project_name_or_raise,
        }
        async with self._core.request("POST", url, auth=auth, json=data) as resp:
            payload = await resp.json()
            return self._parse_bucket_payload(payload)

    async def import_external(
        self,
        provider: Bucket.Provider,
        provider_bucket_name: str,
        credentials: Mapping[str, str],
        name: str | None = None,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> Bucket:
        url = self._get_buckets_url(cluster_name) / "import" / "external"
        auth = await self._config._api_auth()
        data = {
            "name": name,
            "provider": provider.value,
            "provider_bucket_name": provider_bucket_name,
            "credentials": credentials,
            "org_name": org_name or self._config.org_name,
            "project_name": project_name or self._config.project_name_or_raise,
        }
        async with self._core.request("POST", url, auth=auth, json=data) as resp:
            payload = await resp.json()
            return self._parse_bucket_payload(payload)

    async def get(
        self,
        bucket_id_or_name: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> Bucket:
        url = self._get_buckets_url(cluster_name) / bucket_id_or_name
        params = self._get_bucket_url_params(org_name, project_name)
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth, params=params) as resp:
            payload = await resp.json()
            return self._parse_bucket_payload(payload)

    async def rm(
        self,
        bucket_id_or_name: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> None:
        url = self._get_buckets_url(cluster_name) / bucket_id_or_name
        params = self._get_bucket_url_params(org_name, project_name)
        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth, params=params):
            pass

    async def set_public_access(
        self,
        bucket_id_or_name: str,
        public_access: bool,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> Bucket:
        url = self._get_buckets_url(cluster_name) / bucket_id_or_name
        params = self._get_bucket_url_params(org_name, project_name)
        auth = await self._config._api_auth()
        data = {
            "public": public_access,
        }
        async with self._core.request(
            "PATCH", url, auth=auth, json=data, params=params
        ) as resp:
            payload = await resp.json()
            return self._parse_bucket_payload(payload)

    async def request_tmp_credentials(
        self,
        bucket_id_or_name: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> BucketCredentials:
        url = (
            self._get_buckets_url(cluster_name)
            / bucket_id_or_name
            / "make_tmp_credentials"
        )
        params = self._get_bucket_url_params(org_name, project_name)
        auth = await self._config._api_auth()
        async with self._core.request("POST", url, auth=auth, params=params) as resp:
            payload = await resp.json()
            return self._parse_bucket_credentials_payload(payload)

    @asyncgeneratorcontextmanager
    async def get_disk_usage(
        self,
        bucket_id_or_name: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[BucketUsage]:
        total_bytes = 0
        obj_count = 0
        async with self._get_provider_by_exact(
            bucket_id_or_name,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        ) as provider:
            async with provider.list_blobs("", recursive=True) as it:
                async for obj in it:
                    total_bytes += obj.size
                    obj_count += 1
                    yield BucketUsage(total_bytes, obj_count)

    # Helper functions

    async def _get_bucket_for_uri(self, uri: URL) -> Bucket:
        cluster_name = uri.host

        url = self._get_buckets_url(cluster_name) / "find" / "by_path"
        query = {"path": uri.path.lstrip("/")}
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth, params=query) as resp:
            payload = await resp.json()
            return self._parse_bucket_payload(payload)

    @asynccontextmanager
    async def _get_provider(self, uri: URL) -> AsyncIterator[BucketProvider]:
        bucket = await self._get_bucket_for_uri(uri)
        async with self._get_provider_for_bucket(bucket) as provider:
            yield provider

    @asynccontextmanager
    async def _get_provider_by_exact(
        self,
        bucket_id_or_name: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[BucketProvider]:
        bucket = await self.get(
            bucket_id_or_name,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        )
        async with self._get_provider_for_bucket(bucket) as provider:
            yield provider

    @asynccontextmanager
    async def _get_provider_for_bucket(
        self, bucket: Bucket
    ) -> AsyncIterator[BucketProvider]:
        async def _get_new_credentials() -> BucketCredentials:
            return await self.request_tmp_credentials(bucket.id, bucket.cluster_name)

        provider_factory = self._providers.get(bucket.provider)
        if provider_factory is None:
            if bucket.provider in (
                Bucket.Provider.AWS,
                Bucket.Provider.MINIO,
                Bucket.Provider.OPEN_STACK,
            ):
                from ._s3_bucket_provider import S3Provider

                provider_factory = self._providers[bucket.provider] = S3Provider
            elif bucket.provider == Bucket.Provider.AZURE:
                from ._azure_bucket_provider import AzureProvider

                provider_factory = self._providers[bucket.provider] = AzureProvider
            elif bucket.provider == Bucket.Provider.GCP:
                from ._gcs_bucket_provider import GCSProvider

                provider_factory = self._providers[bucket.provider] = GCSProvider
            else:
                raise AssertionError(f"Unknown provider {bucket.provider}")

        async with provider_factory.create(bucket, _get_new_credentials) as provider:
            yield provider

    @asynccontextmanager
    async def _get_bucket_fs(self, uri: URL) -> AsyncIterator[BucketFS]:
        async with self._get_provider(uri) as provider:
            yield BucketFS(provider)

    # Low level operations

    async def head_blob(
        self,
        bucket_id_or_name: str,
        key: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> BucketEntry:
        async with self._get_provider_by_exact(
            bucket_id_or_name,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        ) as provider:
            return await provider.head_blob(key)

    async def put_blob(
        self,
        bucket_id_or_name: str,
        key: str,
        body: AsyncIterator[bytes] | bytes,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> None:
        async with self._get_provider_by_exact(
            bucket_id_or_name,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        ) as provider:
            await provider.put_blob(key, body)

    @asyncgeneratorcontextmanager
    async def fetch_blob(
        self,
        bucket_id_or_name: str,
        key: str,
        offset: int = 0,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> AsyncIterator[bytes]:
        async with self._get_provider_by_exact(
            bucket_id_or_name,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        ) as provider:
            async with provider.fetch_blob(key, offset=offset) as it:
                async for chunk in it:
                    yield chunk

    async def delete_blob(
        self,
        bucket_id_or_name: str,
        key: str,
        cluster_name: str | None = None,
        org_name: str | None = None,
        project_name: str | None = None,
    ) -> None:
        async with self._get_provider_by_exact(
            bucket_id_or_name,
            cluster_name=cluster_name,
            org_name=org_name,
            project_name=project_name,
        ) as provider:
            return await provider.delete_blob(key)

    # Listing operations

    @asyncgeneratorcontextmanager
    async def list_blobs(
        self,
        uri: URL,
        recursive: bool = False,
        limit: int | None = None,
    ) -> AsyncIterator[BucketEntry]:
        uri = self._parser.normalize_uri(uri, allowed_schemes=("blob",))
        async with self._get_provider(uri) as provider:
            key = provider.bucket.get_key_for_uri(uri)
            async with provider.list_blobs(key, recursive=recursive, limit=limit) as it:
                async for entry in it:
                    yield entry

    @asyncgeneratorcontextmanager
    async def glob_blobs(self, uri: URL) -> AsyncIterator[BucketEntry]:
        uri = self._parser.normalize_uri(uri, allowed_schemes=("blob",))
        async with self._get_provider(uri) as provider:
            key = provider.bucket.get_key_for_uri(uri)
            async with self._glob_blobs("", key, provider) as it:
                async for entry in it:
                    yield entry

    @asyncgeneratorcontextmanager
    async def _glob_blobs(
        self, prefix: str, pattern: str, provider: BucketProvider
    ) -> AsyncIterator[BucketEntry]:
        # TODO: factor out code with storage

        part, _, remaining = pattern.partition("/")

        if _isrecursive(part):
            # Patter starts with ** => any key may match it
            full_match = re.compile(translate(pattern)).fullmatch
            async with provider.list_blobs(prefix, recursive=True) as it:
                async for entry in it:
                    if full_match(entry.key[len(prefix) :]):
                        yield entry
            return

        has_magic = _has_magic(part)
        # Optimize the prefix for matching. If we have a pattern `folder1/b*/*.json`
        # it's better to scan with prefix `folder1/b` on the 2nd step, not `folder1/`
        if has_magic:
            opt_prefix = prefix + _glob_safe_prefix(part)
        else:
            opt_prefix = prefix
        match = re.compile(translate(part)).fullmatch

        # If this is the last part in the search pattern we have to scan keys, not
        # just prefixes
        if not remaining:
            async with provider.list_blobs(opt_prefix, recursive=False) as it:
                async for entry in it:
                    if match(entry.name) and not entry.key == opt_prefix:
                        yield entry
            return

        # We can be sure no blobs on this level will match the pattern, as results are
        # deeper down the tree. Recursively scan folders only.
        if has_magic:
            async with provider.list_blobs(opt_prefix, recursive=False) as it:
                async for entry in it:
                    if not entry.is_dir() or not match(entry.name):
                        continue
                    async with self._glob_blobs(
                        entry.key, remaining, provider
                    ) as blob_iter:
                        async for blob in blob_iter:
                            yield blob
        else:
            async with self._glob_blobs(
                prefix + part + "/", remaining, provider
            ) as blob_iter:
                async for blob in blob_iter:
                    yield blob

    # High level transfer operations

    async def upload_file(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        progress: AbstractFileProgress | None = None,
    ) -> None:
        src = normalize_local_path_uri(src)
        dst = self._parser.normalize_uri(dst, allowed_schemes=("blob",))
        async with self._get_bucket_fs(dst) as bucket_fs:
            dst_key = bucket_fs.bucket.get_key_for_uri(dst)
            transferer = FileTransferer(LocalFS(), bucket_fs)
            await transferer.transfer_file(
                src=_extract_path(src),
                dst=PurePosixPath(dst_key),
                update=update,
                progress=progress,
            )

    async def download_file(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        continue_: bool = False,
        progress: AbstractFileProgress | None = None,
    ) -> None:
        src = self._parser.normalize_uri(src, allowed_schemes=("blob",))
        dst = normalize_local_path_uri(dst)
        async with self._get_bucket_fs(src) as bucket_fs:
            src_key = bucket_fs.bucket.get_key_for_uri(src)
            transferer = FileTransferer(bucket_fs, LocalFS())
            await transferer.transfer_file(
                src=PurePosixPath(src_key),
                dst=_extract_path(dst),
                update=update,
                continue_=continue_,
                progress=progress,
            )

    async def upload_dir(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        filter: AsyncFilterFunc | None = None,
        ignore_file_names: AbstractSet[str] = frozenset(),
        progress: AbstractRecursiveFileProgress | None = None,
    ) -> None:
        src = normalize_local_path_uri(src)
        dst = self._parser.normalize_uri(dst, allowed_schemes=("blob",))
        async with self._get_bucket_fs(dst) as bucket_fs:
            dst_key = bucket_fs.bucket.get_key_for_uri(dst)
            transferer = FileTransferer(LocalFS(), bucket_fs)
            await transferer.transfer_dir(
                src=_extract_path(src),
                dst=PurePosixPath(dst_key),
                filter=filter,
                ignore_file_names=ignore_file_names,
                update=update,
                progress=progress,
            )

    async def download_dir(
        self,
        src: URL,
        dst: URL,
        *,
        update: bool = False,
        continue_: bool = False,
        filter: AsyncFilterFunc | None = None,
        progress: AbstractRecursiveFileProgress | None = None,
    ) -> None:
        src = self._parser.normalize_uri(src, allowed_schemes=("blob",))
        dst = normalize_local_path_uri(dst)
        async with self._get_bucket_fs(src) as bucket_fs:
            src_key = bucket_fs.bucket.get_key_for_uri(src)
            transferer = FileTransferer(bucket_fs, LocalFS())
            await transferer.transfer_dir(
                src=PurePosixPath(src_key),
                dst=_extract_path(dst),
                update=update,
                continue_=continue_,
                filter=filter,
                progress=progress,
            )

    async def blob_is_dir(self, uri: URL) -> bool:
        uri = self._parser.normalize_uri(uri, allowed_schemes=("blob",))
        if uri.path.endswith("/"):
            return True
        async with self._get_bucket_fs(uri) as bucket_fs:
            key = bucket_fs.bucket.get_key_for_uri(uri)
            return await bucket_fs.is_dir(PurePosixPath(key))

    async def blob_rm(
        self,
        uri: URL,
        *,
        recursive: bool = False,
        progress: AbstractDeleteProgress | None = None,
    ) -> None:
        uri = self._parser.normalize_uri(uri, allowed_schemes=("blob",))
        async with self._get_bucket_fs(uri) as bucket_fs:
            key = bucket_fs.bucket.get_key_for_uri(uri)
            await rm(bucket_fs, PurePosixPath(key), recursive, progress)

    async def make_signed_url(
        self,
        uri: URL,
        expires_in_seconds: int = 3600,
    ) -> URL:
        uri = self._parser.normalize_uri(uri, allowed_schemes=("blob",))
        bucket = await self._get_bucket_for_uri(uri)
        url = self._get_buckets_url(bucket.cluster_name) / bucket.id / "sign_blob_url"
        auth = await self._config._api_auth()
        data = {
            "key": bucket.get_key_for_uri(uri),
            "expires_in_sec": expires_in_seconds,
        }
        async with self._core.request(
            "POST", url, auth=auth, json=data, params={"owner": bucket.owner}
        ) as resp:
            resp_data = await resp.json()
            return URL(resp_data["url"])

    # Persistent bucket credentials commands

    def _parse_persistent_credentials_payload(
        self, payload: Mapping[str, Any]
    ) -> PersistentBucketCredentials:
        return PersistentBucketCredentials(
            id=payload["id"],
            owner=payload["owner"],
            name=payload.get("name"),
            cluster_name=self._config.cluster_name,
            credentials=[
                self._parse_bucket_credentials_payload(item)
                for item in payload["credentials"]
            ],
            read_only=payload.get("read_only", False),
        )

    def _get_persistent_credentials_url(self, cluster_name: str | None) -> URL:
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        return (
            self._config.get_cluster(cluster_name).buckets_url
            / "persistent_credentials"
        )

    @asyncgeneratorcontextmanager
    async def persistent_credentials_list(
        self, cluster_name: str | None = None
    ) -> AsyncIterator[PersistentBucketCredentials]:
        url = self._get_persistent_credentials_url(cluster_name)
        auth = await self._config._api_auth()
        headers = {"Accept": "application/x-ndjson"}
        async with self._core.request("GET", url, headers=headers, auth=auth) as resp:
            if resp.headers.get("Content-Type", "").startswith("application/x-ndjson"):
                async for line in resp.content:
                    server_message = json.loads(line)
                    if "error" in server_message:
                        raise NDJSONError(server_message["error"])
                    yield self._parse_persistent_credentials_payload(server_message)
            else:
                ret = await resp.json()
                for cred_data in ret:
                    yield self._parse_persistent_credentials_payload(cred_data)

    async def persistent_credentials_create(
        self,
        bucket_ids: Iterable[str],
        name: str | None = None,
        cluster_name: str | None = None,
        read_only: bool | None = False,
    ) -> PersistentBucketCredentials:
        url = self._get_persistent_credentials_url(cluster_name)
        auth = await self._config._api_auth()
        data = {
            "name": name,
            "bucket_ids": list(bucket_ids),
            "read_only": read_only,
        }
        async with self._core.request("POST", url, auth=auth, json=data) as resp:
            payload = await resp.json()
            return self._parse_persistent_credentials_payload(payload)

    async def persistent_credentials_get(
        self, credential_id_or_name: str, cluster_name: str | None = None
    ) -> PersistentBucketCredentials:
        url = self._get_persistent_credentials_url(cluster_name) / credential_id_or_name
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            payload = await resp.json()
            return self._parse_persistent_credentials_payload(payload)

    async def persistent_credentials_rm(
        self, credential_id_or_name: str, cluster_name: str | None = None
    ) -> None:
        url = self._get_persistent_credentials_url(cluster_name) / credential_id_or_name
        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth):
            pass
