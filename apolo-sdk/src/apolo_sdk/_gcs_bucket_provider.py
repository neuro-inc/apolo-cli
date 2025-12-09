import abc
import asyncio
import base64
import json
import logging
import urllib.parse
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from typing import Any

from aiohttp import ClientResponse, ClientSession
from dateutil.parser import isoparse
from google.auth.transport._aiohttp_requests import Request
from google.oauth2._service_account_async import Credentials as SACredentials
from yarl import URL

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

logger = logging.getLogger(__package__)


class AutoRefreshingGCSToken(abc.ABC):
    def __init__(
        self,
    ) -> None:
        self._lock = asyncio.Lock()
        self._token = ""

    @abc.abstractmethod
    def _refresh_required(self) -> bool:
        pass

    @abc.abstractmethod
    async def _do_refresh(self) -> None:
        pass

    async def _refresh_if_needed(self) -> None:
        if not self._refresh_required():
            return
        async with self._lock:
            if not self._refresh_required():
                return
            await self._do_refresh()

    async def get_token(self) -> str:
        await self._refresh_if_needed()
        return self._token


class NeuroAutoRefreshingGCSToken(AutoRefreshingGCSToken):
    REFRESH_DELAY = timedelta(minutes=10)

    def __init__(
        self,
        initial_credentials: "BucketCredentials",
        get_credentials: Callable[[], Awaitable["BucketCredentials"]],
    ):
        super().__init__()
        self._parse_credentials(initial_credentials)
        self._get_credentials = get_credentials

    def _parse_credentials(self, credentials: "BucketCredentials") -> None:
        self._token = credentials.credentials["access_token"]
        self._expiry = isoparse(credentials.credentials["expire_time"])

    def _refresh_required(self) -> bool:
        return (
            self._token is None
            or (self._expiry - datetime.now(timezone.utc)) < self.REFRESH_DELAY
        )

    async def _do_refresh(self) -> None:
        self._parse_credentials(await self._get_credentials())


class ServiceAccountRefreshingGCSToken(AutoRefreshingGCSToken):
    def __init__(self, key_data_json_b64: str, request: Request) -> None:
        super().__init__()
        self._credential: SACredentials = SACredentials.from_service_account_info(
            json.loads(base64.b64decode(key_data_json_b64).decode())
        )
        self._credential = self._credential.with_scopes(
            ["https://www.googleapis.com/auth/devstorage.read_write"]
        )
        self._request = request

    async def _do_refresh(self) -> None:
        await self._credential.refresh(self._request)
        self._token = self._credential.token  # type: ignore

    def _refresh_required(self) -> bool:
        return not self._token or not self._credential.valid


class GCSProvider(MeasureTimeDiffMixin, BucketProvider):
    BASE_URL = "https://storage.googleapis.com/storage/v1"
    UPLOAD_BASE_URL = "https://storage.googleapis.com/upload/storage/v1"
    MIN_CHUNK_SIZE = 10 * 262144

    def __init__(
        self,
        session: ClientSession,
        token: AutoRefreshingGCSToken,
        bucket: "Bucket",
        gcs_bucket_name: str,
    ) -> None:
        super().__init__()
        self.bucket = bucket
        self._session = session
        self._token = token
        self._gcs_bucket_name = gcs_bucket_name

        def _extract_date(resp: ClientResponse) -> datetime:
            date_str = resp.headers["Date"]
            return parsedate_to_datetime(date_str)

        self._request = self._wrap_api_call_ctx_manager(  # type: ignore
            self._request, _extract_date
        )

    @asynccontextmanager
    async def _request(
        self,
        method: str,
        url: str,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Mapping[str, Any] | None = None,
        data: Any | None = None,
    ) -> AsyncIterator[ClientResponse]:
        async with self._session.request(
            method,
            url,
            params=params,
            headers=headers,
            json=json,
            data=data,
        ) as resp:
            if resp.status == 404:
                raise ResourceNotFound
            if resp.status > 400:
                # Some error response are OK (404 for example), so just log here
                response_text = await resp.text()
                logger.info(f"Request to GCS failed {method} {url}: {response_text}")
            resp.raise_for_status()
            yield resp

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        bucket: "Bucket",
        _get_credentials: Callable[[], Awaitable["BucketCredentials"]],
    ) -> AsyncIterator[BucketProvider]:
        initial_credentials = await _get_credentials()

        async with ClientSession(auto_decompress=False) as session:
            token: AutoRefreshingGCSToken
            if "key_data" in initial_credentials.credentials:
                raw = initial_credentials.credentials["key_data"]
                token = ServiceAccountRefreshingGCSToken(raw, request=Request(session))
            else:
                token = NeuroAutoRefreshingGCSToken(
                    initial_credentials, _get_credentials
                )

            yield cls(
                session, token, bucket, initial_credentials.credentials["bucket_name"]
            )

    async def _get_auth_headers(self) -> Mapping[str, str]:
        token = await self._token.get_token()
        return {"Authorization": f"Bearer {token}"}

    def _parse_obj(self, data: Mapping[str, Any]) -> BlobObject:
        created_at = isoparse(data["timeCreated"])
        return BlobObject(
            bucket=self.bucket,
            key=data["name"],
            size=int(data["size"]),
            created_at=created_at,
            modified_at=created_at,  # blobs are immutable
        )

    @asyncgeneratorcontextmanager
    async def list_blobs(
        self, prefix: str, recursive: bool = False, limit: int | None = None
    ) -> AsyncIterator[BucketEntry]:
        url = f"{self.BASE_URL}/b/{self._gcs_bucket_name}/o"

        params = {
            "prefix": prefix,
            "pageToken": "",
        }
        if not recursive:
            params["delimiter"] = "/"
        cnt = 0
        while True:
            async with self._request(
                "GET", url=url, params=params, headers=await self._get_auth_headers()
            ) as resp:
                data = await resp.json()
            for item in data.get("items", []):
                yield self._parse_obj(item)
                cnt += 1
                if cnt == limit:
                    return
            for prefix in data.get("prefixes", []):
                yield BlobCommonPrefix(
                    bucket=self.bucket,
                    key=prefix,
                    size=0,
                )
                cnt += 1
                if cnt == limit:
                    return
            params["pageToken"] = data.get("nextPageToken", "")
            if not params["pageToken"]:
                break

    async def head_blob(self, key: str) -> BucketEntry:
        key = urllib.parse.quote(key, safe="")
        url = f"{self.BASE_URL}/b/{self._gcs_bucket_name}/o/{key}"

        try:
            async with self._request(
                "GET", url=url, headers=await self._get_auth_headers()
            ) as resp:
                return self._parse_obj(await resp.json())
        except ResourceNotFound:
            raise ResourceNotFound(
                f"There is no object with key {key} in bucket {self.bucket.name}"
            )

    async def put_blob(
        self,
        key: str,
        body: AsyncIterator[bytes] | bytes,
        progress: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        # Step 1: initiate multipart upload
        url = f"{self.UPLOAD_BASE_URL}/b/{self._gcs_bucket_name}/o"
        params = {"uploadType": "resumable", "name": key}
        async with self._request(
            "POST",
            url=url,
            params=params,
            headers=await self._get_auth_headers(),
            json={},
        ) as resp:
            session_url = URL(resp.headers["Location"])

        uploaded_bytes = 0
        buffer = b""

        async def _upload_chunk(*, final: bool = False) -> None:
            nonlocal uploaded_bytes
            nonlocal buffer
            size = len(buffer)
            if final:
                total = str(uploaded_bytes + size)
            else:
                total = "*"
            if size == 0:
                data_range = "*"
            else:
                data_range = f"{uploaded_bytes}-{uploaded_bytes + size - 1}"
            async with self._request(
                "PUT",
                url=str(session_url),
                data=BytesIO(buffer),
                headers={"Content-Range": (f"bytes {data_range}/{total}")},
            ):
                pass
            if progress:
                await progress(size)
            uploaded_bytes += size
            buffer = b""

        if isinstance(body, bytes):
            buffer = body
        else:
            async for chunk in body:
                buffer += chunk
                if len(buffer) > self.MIN_CHUNK_SIZE:
                    await _upload_chunk()

        # Complete file:
        await _upload_chunk(final=True)

    @asyncgeneratorcontextmanager
    async def fetch_blob(self, key: str, offset: int = 0) -> AsyncIterator[bytes]:
        key = urllib.parse.quote(key, safe="")
        url = f"{self.BASE_URL}/b/{self._gcs_bucket_name}/o/{key}"
        params = {"alt": "media"}
        headers = dict(await self._get_auth_headers())
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            async with self._request(
                "GET", url=url, params=params, headers=headers
            ) as resp:
                async for data in resp.content.iter_any():
                    yield data
        except ResourceNotFound:
            raise ResourceNotFound(
                f"There is no object with key {key} in bucket {self.bucket.name}"
            )

    async def delete_blob(self, key: str) -> None:
        key = urllib.parse.quote(key, safe="")
        url = f"{self.BASE_URL}/b/{self._gcs_bucket_name}/o/{key}"
        try:
            async with self._request(
                "DELETE", url=url, headers=await self._get_auth_headers()
            ):
                pass
        except ResourceNotFound:
            raise ResourceNotFound(
                f"There is no object with key {key} in bucket {self.bucket.name}"
            )
