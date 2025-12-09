from datetime import datetime
from typing import Any

import pytest

from apolo_sdk import BlobCommonPrefix, BlobObject, Bucket, BucketEntry

from apolo_cli.formatters.blob_storage import (
    BaseBlobFormatter,
    LongBlobFormatter,
    SimpleBlobFormatter,
)


class TestBlobFormatter:
    buckets: list[Bucket] = [
        Bucket(
            id="bucket-1",
            name="apolo-my-bucket",
            created_at=datetime(2018, 1, 1, 3),
            cluster_name="test-cluster",
            owner="test-user",
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="org",
            project_name="test-project",
        ),
        Bucket(
            id="bucket-2",
            name="apolo-public-bucket",
            created_at=datetime(2018, 1, 1, 17, 2, 4),
            cluster_name="test-cluster",
            owner="public",
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="org",
            project_name="test-project",
        ),
        Bucket(
            id="bucket-3",
            name="apolo-shared-bucket",
            created_at=datetime(2018, 1, 1, 13, 1, 5),
            cluster_name="test-cluster",
            owner="another-user",
            provider=Bucket.Provider.AWS,
            imported=False,
            org_name="test-org",
            project_name="test-project",
        ),
    ]

    blobs: list[BucketEntry] = [
        BlobObject(
            key="file1024.txt",
            modified_at=datetime(2018, 1, 1, 14, 0, 0),
            bucket=buckets[0],
            size=1024,
        ),
        BlobObject(
            key="file_bigger.txt",
            modified_at=datetime(2018, 1, 1, 14, 0, 0),
            bucket=buckets[1],
            size=1_024_001,
        ),
        BlobObject(
            key="folder2/info.txt",
            modified_at=datetime(2018, 1, 1, 14, 0, 0),
            bucket=buckets[2],
            size=240,
        ),
        BlobObject(
            key="folder2/",
            modified_at=datetime(2018, 1, 1, 14, 0, 0),
            bucket=buckets[2],
            size=0,
        ),
    ]
    folders: list[BucketEntry] = [
        BlobCommonPrefix(bucket=buckets[0], key="folder1/", size=0),
        BlobCommonPrefix(bucket=buckets[1], key="folder2/", size=0),
    ]

    all: list[Bucket | BucketEntry] = [*buckets, *blobs, *folders]

    @pytest.mark.parametrize(
        "formatter",
        [
            SimpleBlobFormatter(color=False, uri_formatter=str),
            LongBlobFormatter(human_readable=False, color=False, uri_formatter=str),
        ],
    )
    def test_long_formatter(self, rich_cmp: Any, formatter: BaseBlobFormatter) -> None:
        for index, item in enumerate(self.all):
            rich_cmp(formatter(item), index=index)
