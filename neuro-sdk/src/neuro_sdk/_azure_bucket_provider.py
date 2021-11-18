import asyncio
import secrets
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, Tuple, Union

from azure.core.credentials import AzureSasCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobBlock
from azure.storage.blob.aio import ContainerClient
from azure.storage.blob.aio._list_blobs_helper import BlobPrefix
from dateutil.parser import isoparse

from ._bucket_base import (
    BlobCommonPrefix,
    BlobObject,
    Bucket,
    BucketCredentials,
    BucketEntry,
    BucketProvider,
    MeasureTimeDiffMixin,
)
from .errors import ResourceNotFound
from .utils import asyncgeneratorcontextmanager

if sys.version_info >= (3, 7):
    from contextlib import AsyncExitStack, asynccontextmanager
else:
    from async_exit_stack import AsyncExitStack
    from async_generator import asynccontextmanager


class AzureProvider(MeasureTimeDiffMixin, BucketProvider):
    def __init__(self, container_client: ContainerClient, bucket: "Bucket") -> None:
        super().__init__()
        self.bucket = bucket

        self._client = container_client

        def _extract_date(resp: Any) -> datetime:
            date_str = resp.http_response.headers["Date"]
            return parsedate_to_datetime(date_str)

        # Hack to get client-server clock difference
        container_client._client._client._pipeline.run = self._wrap_api_call(
            container_client._client._client._pipeline.run, _extract_date
        )

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        bucket: "Bucket",
        _get_credentials: Callable[[], Awaitable["BucketCredentials"]],
    ) -> AsyncIterator[BucketProvider]:
        initial_credentials = await _get_credentials()

        async with AsyncExitStack() as exit_stack:
            credential: Union[AzureSasCredential, str]
            if "sas_token" in initial_credentials.credentials:
                sas_credential = AzureSasCredential(
                    initial_credentials.credentials["sas_token"]
                )
                credential = sas_credential

                @asynccontextmanager
                async def _token_renewer() -> AsyncIterator[None]:
                    async def renew_token_loop() -> None:
                        expiry = isoparse(initial_credentials.credentials["expiry"])
                        while True:
                            delay = (
                                expiry
                                - timedelta(minutes=10)
                                - datetime.now(timezone.utc)
                            ).total_seconds()
                            await asyncio.sleep(max(delay, 0))
                            credentials = await _get_credentials()
                            sas_credential.update(credentials.credentials["sas_token"])
                            expiry = isoparse(credentials.credentials["expiry"])

                    task = asyncio.ensure_future(renew_token_loop())
                    try:
                        yield
                    finally:
                        task.cancel()

                await exit_stack.enter_async_context(_token_renewer())
            else:
                credential = initial_credentials.credentials["credential"]

            container_client = await exit_stack.enter_async_context(
                ContainerClient(
                    account_url=initial_credentials.credentials["storage_endpoint"],
                    container_name=initial_credentials.credentials["bucket_name"],
                    credential=credential,
                )
            )
            yield cls(container_client, bucket)

    @asyncgeneratorcontextmanager
    async def list_blobs(
        self, prefix: str, recursive: bool = False, limit: Optional[int] = None
    ) -> AsyncIterator[BucketEntry]:
        if recursive:
            it = self._client.list_blobs(prefix)
        else:
            it = self._client.walk_blobs(prefix)
        count = 0
        async for item in it:
            if isinstance(item, BlobPrefix):
                entry: BucketEntry = BlobCommonPrefix(
                    bucket=self.bucket,
                    key=item.name,
                    size=0,
                )
            else:
                entry = BlobObject(
                    bucket=self.bucket,
                    key=item.name,
                    size=item.size,
                    created_at=item.creation_time,
                    modified_at=item.last_modified,
                )
            yield entry
            count += 1
            if count == limit:
                return

    async def head_blob(self, key: str) -> BucketEntry:
        try:
            blob_info = await self._client.get_blob_client(key).get_blob_properties()
            return BlobObject(
                bucket=self.bucket,
                key=blob_info.name,
                size=blob_info.size,
                created_at=blob_info.creation_time,
                modified_at=blob_info.last_modified,
            )
        except ResourceNotFoundError:
            raise ResourceNotFound(
                f"There is no object with key {key} in bucket {self.bucket.name}"
            )

    async def put_blob(
        self, key: str, body: Union[AsyncIterator[bytes], bytes]
    ) -> None:
        blob_client = self._client.get_blob_client(key)
        if isinstance(body, bytes):
            await blob_client.upload_blob(body)
        else:
            blocks = []
            async for data in body:
                block_id = secrets.token_hex(16)
                await blob_client.stage_block(block_id, data)
                blocks.append(BlobBlock(block_id=block_id))
            await blob_client.commit_block_list(blocks)

    @asyncgeneratorcontextmanager
    async def fetch_blob(self, key: str, offset: int = 0) -> AsyncIterator[bytes]:
        try:
            downloader = await self._client.get_blob_client(key).download_blob(
                offset=offset
            )
        except ResourceNotFoundError:
            raise ResourceNotFound(
                f"There is no object with key {key} in bucket {self.bucket.name}"
            )
        async for chunk in downloader.chunks():
            yield chunk

    async def delete_blob(self, key: str) -> None:
        try:
            await self._client.get_blob_client(key).delete_blob()
        except ResourceNotFoundError:
            raise ResourceNotFound(
                f"There is no object with key {key} in bucket {self.bucket.name}"
            )

    async def get_time_diff_to_local(self) -> Tuple[float, float]:
        if self._min_time_diff is None or self._max_time_diff is None:
            return 0, 0
        return self._min_time_diff, self._max_time_diff
