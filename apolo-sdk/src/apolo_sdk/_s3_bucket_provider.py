from contextlib import asynccontextmanager
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping, Optional, Union

import aiobotocore.session
import botocore
import botocore.exceptions
import certifi
from aiobotocore.client import AioBaseClient
from aiobotocore.config import AioConfig
from aiobotocore.credentials import AioCredentials, AioRefreshableCredentials
from packaging.version import parse

from ._bucket_base import (
    BlobCommonPrefix,
    BlobObject,
    Bucket,
    BucketCredentials,
    BucketEntry,
    BucketProvider,
    MeasureTimeDiffMixin,
)
from ._errors import ResourceNotFound
from ._utils import asyncgeneratorcontextmanager

# Content-MD5 hash is no longer populated since this version,
# so we should adjust our config a bit to continue a population
# of checksum which is required by the MiniO
VERSION_BOTOCORE_CHECKSUM_CALCULATION = parse("1.36.0")
CHECKSUM_CALCULATE_WHEN_REQUIRED = "WHEN_REQUIRED"


class S3Provider(MeasureTimeDiffMixin, BucketProvider):
    def __init__(
        self, client: AioBaseClient, bucket: "Bucket", bucket_name: str
    ) -> None:
        super().__init__()
        self.bucket = bucket
        self._client = client
        self._bucket_name = bucket_name

        def _extract_date(resp: Any) -> datetime:
            date_str = resp["ResponseMetadata"]["HTTPHeaders"]["date"]
            return parsedate_to_datetime(date_str)

        client._make_api_call = self._wrap_api_call(
            client._make_api_call, _extract_date
        )

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        bucket: "Bucket",
        _get_credentials: Callable[[], Awaitable["BucketCredentials"]],
    ) -> AsyncIterator[BucketProvider]:
        initial_credentials = await _get_credentials()

        session = aiobotocore.session.get_session()

        if "expiration" in initial_credentials.credentials:

            def _credentials_to_meta(
                credentials: "BucketCredentials",
            ) -> Mapping[str, str]:
                return {
                    "access_key": credentials.credentials["access_key_id"],
                    "secret_key": credentials.credentials["secret_access_key"],
                    "token": credentials.credentials["session_token"],
                    "expiry_time": credentials.credentials["expiration"],
                }

            async def _refresher() -> Mapping[str, str]:
                return _credentials_to_meta(await _get_credentials())

            session._credentials = AioRefreshableCredentials.create_from_metadata(
                metadata=_credentials_to_meta(initial_credentials),
                refresh_using=_refresher,
                method="neuro-bucket-api-refresh",  # This is just a label
            )
        else:
            # Permanent credentials
            session._credentials = AioCredentials(
                access_key=initial_credentials.credentials["access_key_id"],
                secret_key=initial_credentials.credentials["secret_access_key"],
            )

        config_kwargs: dict[str, int | str] = {"max_pool_connections": 100}
        if parse(botocore.__version__) >= VERSION_BOTOCORE_CHECKSUM_CALCULATION:
            config_kwargs.update(
                {
                    "request_checksum_calculation": CHECKSUM_CALCULATE_WHEN_REQUIRED,
                    "response_checksum_validation": CHECKSUM_CALCULATE_WHEN_REQUIRED,
                }
            )

        config = AioConfig(**config_kwargs)

        async with session.create_client(
            "s3",
            endpoint_url=initial_credentials.credentials.get("endpoint_url"),
            region_name=initial_credentials.credentials.get("region_name"),
            config=config,
            verify=certifi.where(),
        ) as client:
            yield cls(client, bucket, initial_credentials.credentials["bucket_name"])

    @asyncgeneratorcontextmanager
    async def list_blobs(
        self, prefix: str, recursive: bool = False, limit: Optional[int] = None
    ) -> AsyncIterator[BucketEntry]:
        paginator = self._client.get_paginator("list_objects_v2")
        kwargs = dict(Bucket=self._bucket_name, Prefix=prefix)
        if not recursive:
            kwargs["Delimiter"] = "/"
        cnt = 0
        async for result in paginator.paginate(**kwargs):
            for common_prefix in result.get("CommonPrefixes", []):
                yield BlobCommonPrefix(
                    bucket=self.bucket,
                    size=0,
                    key=common_prefix["Prefix"],
                )
                cnt += 1
                if cnt == limit:
                    return
            for blob in result.get("Contents", []):
                yield BlobObject(
                    bucket=self.bucket,
                    key=blob["Key"],
                    modified_at=blob["LastModified"],
                    size=blob["Size"],
                )
                cnt += 1
                if cnt == limit:
                    return

    async def head_blob(self, key: str) -> BucketEntry:
        try:
            blob = await self._client.head_object(Bucket=self._bucket_name, Key=key)
            return BlobObject(
                bucket=self.bucket,
                key=key,
                modified_at=blob["LastModified"],
                size=blob["ContentLength"],
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ResourceNotFound(
                    f"There is no object with key {key} in bucket {self.bucket.name}"
                )
            raise

    MIN_CHUNK_SIZE = 10 * (2**20)  # 10mb

    async def put_blob(
        self,
        key: str,
        body: Union[AsyncIterator[bytes], bytes],
        progress: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> None:
        if isinstance(body, bytes):
            await self._client.put_object(
                Bucket=self._bucket_name,
                Key=key,
                Body=body,
            )
            return
        upload_id = (
            await self._client.create_multipart_upload(
                Bucket=self._bucket_name,
                Key=key,
            )
        )["UploadId"]
        try:
            part_id = 1
            parts_info = []
            buffer = b""

            async def _upload_chunk() -> None:
                nonlocal buffer, part_id
                part = await self._client.upload_part(
                    Bucket=self._bucket_name,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_id,
                    Body=buffer,
                )
                if progress is not None:
                    await progress(len(buffer))
                buffer = b""
                parts_info.append({"ETag": part["ETag"], "PartNumber": part_id})
                part_id += 1

            async for chunk in body:
                buffer += chunk
                if len(buffer) > self.MIN_CHUNK_SIZE:
                    await _upload_chunk()
            if buffer or len(parts_info) == 0:
                # Either there is final part of file or file is zero-length file
                await _upload_chunk()
        except Exception:
            await self._client.abort_multipart_upload(
                Bucket=self._bucket_name,
                Key=key,
                UploadId=upload_id,
            )
            raise
        else:
            await self._client.complete_multipart_upload(
                Bucket=self._bucket_name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": parts_info,
                },
            )

    @asyncgeneratorcontextmanager
    async def fetch_blob(self, key: str, offset: int = 0) -> AsyncIterator[bytes]:
        response = await self._client.get_object(
            Bucket=self._bucket_name,
            Key=key,
            Range=f"bytes={offset}-" if offset else "",
        )
        async with response["Body"] as stream:
            async for chunk in stream.content.iter_any():
                yield chunk

    async def delete_blob(self, key: str) -> None:
        await self._client.delete_object(Bucket=self._bucket_name, Key=key)
