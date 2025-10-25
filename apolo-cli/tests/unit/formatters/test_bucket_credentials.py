from typing import Any, Awaitable, Callable, List, Tuple

import pytest
from dateutil.parser import isoparse

from apolo_sdk import Bucket, BucketCredentials, PersistentBucketCredentials

from apolo_cli.formatters.bucket_credentials import (
    BucketCredentialFormatter,
    BucketCredentialsFormatter,
    SimpleBucketCredentialsFormatter,
)


async def test_bucket_credentials_formatter(rich_cmp: Any) -> None:
    bucket = Bucket(
        id="bucket",
        name="test-bucket",
        owner="user",
        cluster_name="cluster",
        provider=Bucket.Provider.AWS,
        created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
        imported=False,
        org_name="org",
        project_name="test-project",
    )
    credentials = PersistentBucketCredentials(
        id="bucket-credentials",
        name="test-credentials",
        owner="user",
        cluster_name="cluster",
        read_only=False,
        credentials=[
            BucketCredentials(
                provider=Bucket.Provider.AWS,
                bucket_id=bucket.id,
                credentials={
                    "key1": "value1",
                    "key2": "very-long-value-" * 100,
                },
            )
        ],
    )

    async def _get_bucket(bucket_id: str) -> Bucket:
        assert bucket_id == bucket.id
        return bucket

    fmtr = BucketCredentialFormatter(get_bucket=_get_bucket)
    rich_cmp(await fmtr(credentials))


CredListFixture = Tuple[
    List[PersistentBucketCredentials], Callable[[str], Awaitable[Bucket]]
]


@pytest.fixture
def credentials_list_fixture() -> CredListFixture:
    buckets = [
        Bucket(
            id="bucket-1",
            name="test-bucket",
            owner="user",
            cluster_name="cluster",
            created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="org",
            project_name="test-project",
        ),
        Bucket(
            id="bucket-2",
            name="test-bucket-2",
            owner="user",
            cluster_name="cluster",
            created_at=isoparse("2016-03-04T12:28:59.759433+00:00"),
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="org",
            project_name="test-project",
        ),
        Bucket(
            id="bucket-3",
            name=None,
            owner="user-2",
            cluster_name="cluster",
            created_at=isoparse("2018-03-04T12:28:59.759433+00:00"),
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="org",
            project_name="test-project",
        ),
        Bucket(
            id="bucket-4",
            name=None,
            owner="user",
            cluster_name="cluster",
            created_at=isoparse("2019-03-04T12:28:59.759433+00:00"),
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="org",
            project_name="test-project",
        ),
    ]

    async def _get_bucket(bucket_id: str) -> Bucket:
        return next(bucket for bucket in buckets if bucket.id == bucket_id)

    credentials = [
        PersistentBucketCredentials(
            id="bucket-credentials-1",
            name="test-credentials-1",
            owner="user",
            cluster_name="cluster",
            read_only=False,
            credentials=[
                BucketCredentials(
                    provider=Bucket.Provider.AWS,
                    bucket_id="bucket-1",
                    credentials={
                        "key1": "value1",
                        "key2": "value2",
                    },
                ),
                BucketCredentials(
                    provider=Bucket.Provider.AWS,
                    bucket_id="bucket-2",
                    credentials={
                        "key1": "value1",
                        "key2": "value2",
                    },
                ),
            ],
        ),
        PersistentBucketCredentials(
            id="bucket-credentials-2",
            name="test-credentials-3",
            owner="user",
            cluster_name="cluster",
            read_only=True,
            credentials=[
                BucketCredentials(
                    provider=Bucket.Provider.AWS,
                    bucket_id="bucket-3",
                    credentials={
                        "key1": "value1",
                        "key2": "value2",
                    },
                ),
            ],
        ),
        PersistentBucketCredentials(
            id="bucket-credentials-3",
            name="test-credentials-3",
            owner="user",
            cluster_name="cluster",
            read_only=False,
            credentials=[
                BucketCredentials(
                    provider=Bucket.Provider.AWS,
                    bucket_id="bucket-3",
                    credentials={
                        "key1": "value1",
                        "key2": "value2",
                    },
                ),
                BucketCredentials(
                    provider=Bucket.Provider.AWS,
                    bucket_id="bucket-4",
                    credentials={
                        "key1": "value1",
                        "key2": "value2",
                    },
                ),
            ],
        ),
    ]
    return credentials, _get_bucket


async def test_buckets_credentials_formatter_simple(
    credentials_list_fixture: CredListFixture, rich_cmp: Any
) -> None:
    fmtr = SimpleBucketCredentialsFormatter()
    rich_cmp(await fmtr(credentials_list_fixture[0]))


async def test_buckets_credentials_formatter(
    credentials_list_fixture: CredListFixture, rich_cmp: Any
) -> None:
    fmtr = BucketCredentialsFormatter(credentials_list_fixture[1])
    rich_cmp(await fmtr(credentials_list_fixture[0]))
