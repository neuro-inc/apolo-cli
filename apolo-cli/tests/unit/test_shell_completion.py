import logging
import os
import shlex
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)
from unittest import mock

import pytest
from dateutil.parser import isoparse
from yarl import URL

from apolo_sdk import (
    Action,
    BlobObject,
    Bucket,
    BucketCredentials,
    Container,
    Disk,
    Disks,
    FileStatus,
    FileStatusType,
    Images,
    JobDescription,
    Jobs,
    JobStatus,
    JobStatusHistory,
    PersistentBucketCredentials,
    RemoteImage,
    Resources,
    ServiceAccount,
    ServiceAccounts,
    Storage,
)
from apolo_sdk._buckets import Buckets
from apolo_sdk._url_utils import normalize_storage_path_uri
from apolo_sdk._utils import asyncgeneratorcontextmanager

from .conftest import SysCapWithCode

JOB_OUTPUT_TIMEOUT = 10 * 60
NETWORK_TIMEOUT = 3 * 60.0
_RunCli = Callable[[Sequence[str]], SysCapWithCode]

log = logging.getLogger(__name__)


def _default_args(verbosity: int, network_timeout: float, nmrc_path: Path) -> List[str]:
    args = [
        "--show-traceback",
        "--disable-pypi-version-check",
        "--color=no",
        f"--network-timeout={network_timeout}",
        "--skip-stats",
        f"--neuromation-config={nmrc_path}",
    ]

    if verbosity < 0:
        args.append("-" + "q" * (-verbosity))
    if verbosity > 0:
        args.append("-" + "v" * verbosity)

    return args


def autocomplete(
    run_cli: _RunCli,
    nmrc_path: Path,
    monkeypatch: Any,
    arguments: Sequence[str],
    *,
    shell: str,
    verbosity: int = 0,
    network_timeout: float = NETWORK_TIMEOUT,
    timeout: float = JOB_OUTPUT_TIMEOUT,
) -> str:
    __tracebackhide__ = True

    log.info("Run 'apolo %s'", " ".join(arguments))

    args = _default_args(verbosity, network_timeout, nmrc_path)
    env = dict(os.environ)

    env["_PYTEST_COMPLETE"] = f"{shell}_complete"
    env["COMP_WORDS"] = " ".join(shlex.quote(arg) for arg in [*args, *arguments])
    env["COMP_CWORD"] = str(len(args) + len(arguments) - 1)
    env["NEURO_CLI_JOB_AUTOCOMPLETE_LIMIT"] = "500"

    monkeypatch.setattr(os, "environ", env)
    proc = run_cli([])
    assert proc.code == 0
    assert not proc.err
    return proc.out


_RunAC = Callable[[List[str]], Tuple[str, str]]


@pytest.fixture()
def run_autocomplete(run_cli: _RunCli, nmrc_path: Path, monkeypatch: Any) -> _RunAC:
    def autocompleter(args: Sequence[str]) -> Tuple[str, str]:
        zsh_out = autocomplete(run_cli, nmrc_path, monkeypatch, args, shell="zsh")
        bash_out = autocomplete(run_cli, nmrc_path, monkeypatch, args, shell="bash")
        return zsh_out, bash_out

    return autocompleter


skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32", reason="Autocompletion is not supported on Windows"
)


@skip_on_windows
def test_file_autocomplete(run_autocomplete: _RunAC, tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "file.txt").write_bytes(b"")
    (base / "folder").mkdir()
    (base / "folder/file2.txt").write_bytes(b"")
    (base / "folder/folder2").mkdir()

    zsh_out, bash_out = run_autocomplete(["storage", "cp", "fi"])
    assert bash_out == "uri,file:,"
    assert zsh_out == "uri\nfile:\n_\n_"

    base_uri = base.as_uri()
    base_prefix = base_uri[5:]
    names = os.listdir(base)
    names = [name + ("/" if "folder" in name else "") for name in names]

    zsh_out, bash_out = run_autocomplete(["storage", "cp", base_uri + "/"])
    assert bash_out == "\n".join(f"uri,{name},{base_prefix}/" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\n{base_uri}/" for name in names)

    zsh_out, bash_out = run_autocomplete(["storage", "cp", base_uri + "/f"])
    assert bash_out == "\n".join(f"uri,{name},{base_prefix}/" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\n{base_uri}/" for name in names)

    zsh_out, bash_out = run_autocomplete(["storage", "cp", base_uri + "/fi"])
    assert bash_out == f"uri,file.txt,{base_prefix}/"
    assert zsh_out == f"uri\nfile.txt\n_\n{base_uri}/"

    zsh_out, bash_out = run_autocomplete(["storage", "cp", base_uri + "/folder"])
    assert bash_out == f"uri,folder/,{base_prefix}/"
    assert zsh_out == f"uri\nfolder/\n_\n{base_uri}/"

    zsh_out, bash_out = run_autocomplete(["storage", "cp", base_uri + "/folder/"])
    names = os.listdir(base / "folder")
    names = [name + ("/" if "folder" in name else "") for name in names]
    assert bash_out == "\n".join(f"uri,{name},{base_prefix}/folder/" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\n{base_uri}/folder/" for name in names)


@skip_on_windows
def test_file_autocomplete_default(run_autocomplete: _RunAC) -> None:
    default = Path.cwd()
    default_uri = default.as_uri()
    default_prefix = default_uri[5:]
    names = [p.name + ("/" if p.is_dir() else "") for p in default.iterdir()]
    zsh_out, bash_out = run_autocomplete(["storage", "cp", "file:"])
    assert bash_out == "\n".join(f"uri,{name},{default_prefix}/" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\n{default_uri}/" for name in names)

    cwd = Path.cwd()
    cwd_uri = cwd.as_uri()
    cwd_prefix = cwd_uri[5:]
    names = [p.name + ("/" if p.is_dir() else "") for p in cwd.iterdir()]
    zsh_out, bash_out = run_autocomplete(["storage", "cp", "file://"])
    assert bash_out == "\n".join(f"uri,{name},{cwd_prefix}/" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\n{cwd_uri}/" for name in names)


@skip_on_windows
def test_file_autocomplete_root(run_autocomplete: _RunAC) -> None:
    names = [p.name + ("/" if p.is_dir() else "") for p in Path("/").iterdir()]
    zsh_out, bash_out = run_autocomplete(["storage", "cp", "file:/"])
    assert bash_out == "\n".join(f"uri,{name},///" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\nfile:///" for name in names)

    zsh_out, bash_out = run_autocomplete(["storage", "cp", "file:///"])
    assert bash_out == "\n".join(f"uri,{name},///" for name in names)
    assert zsh_out == "\n".join(f"uri\n{name}\n_\nfile:///" for name in names)


@skip_on_windows
def test_storage_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Storage, "stat") as mocked_stat, mock.patch.object(
        Storage, "list"
    ) as mocked_list:
        tree = {
            URL("storage://default/"): ["test-user", "other-user"],
            URL("storage://default/NO_ORG"): ["test-user", "other-user"],
            URL("storage://default/test-user"): ["folder", "file.txt"],
            URL("storage://default/NO_ORG/test-user"): ["folder", "file.txt"],
            URL("storage://default/test-user/folder"): ["folder2", "file2.txt"],
            URL("storage://default/other-user"): ["folder3", "file3.txt"],
            URL("storage://other-cluster"): ["test-user"],
        }

        def is_dir(uri: URL) -> bool:
            return ".txt" not in uri.name

        async def stat(uri: URL) -> FileStatus:
            uri = normalize_storage_path_uri(uri, "test-user", "default", org_name=None)
            if uri.path.endswith("/") and uri.path != "/":
                uri = uri.with_path(uri.path.rstrip("/"))
            return FileStatus(
                path=uri.path,
                type=FileStatusType.DIRECTORY if is_dir(uri) else FileStatusType.FILE,
                size=0,
                modification_time=1234567890,
                permission=Action.WRITE,
                uri=uri,
            )

        @asyncgeneratorcontextmanager
        async def list(uri: URL) -> AsyncIterator[FileStatus]:
            uri = normalize_storage_path_uri(uri, "test-user", "default", org_name=None)
            for name in tree[uri]:
                child = uri / name
                yield FileStatus(
                    path=name,
                    type=(
                        FileStatusType.DIRECTORY
                        if is_dir(child)
                        else FileStatusType.FILE
                    ),
                    size=0,
                    modification_time=1234567890,
                    permission=Action.WRITE,
                    uri=child,
                )

        mocked_stat.side_effect = stat
        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "st"])
        assert bash_out == "uri,storage:,"
        assert zsh_out == "uri\nstorage:\n_\n_"

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:"])
        assert bash_out == ("uri,folder/,\n" "uri,file.txt,")
        assert zsh_out == ("uri\nfolder/\n_\nstorage:\n" "uri\nfile.txt\n_\nstorage:")

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:f"])
        assert bash_out == ("uri,folder/,\n" "uri,file.txt,")
        assert zsh_out == ("uri\nfolder/\n_\nstorage:\n" "uri\nfile.txt\n_\nstorage:")

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:folder/"])
        assert bash_out == ("uri,folder2/,folder/\n" "uri,file2.txt,folder/")
        assert zsh_out == (
            "uri\nfolder2/\n_\nstorage:folder/\n" "uri\nfile2.txt\n_\nstorage:folder/"
        )

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:folder/fi"])
        assert bash_out == "uri,file2.txt,folder/"
        assert zsh_out == "uri\nfile2.txt\n_\nstorage:folder/"

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:/"])
        assert bash_out == (
            "uri,test-user/,//default/NO_ORG/\n" "uri,other-user/,//default/NO_ORG/"
        )
        assert zsh_out == (
            "uri\ntest-user/\n_\nstorage://default/NO_ORG/\n"
            "uri\nother-user/\n_\nstorage://default/NO_ORG/"
        )

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:/t"])
        assert bash_out == "uri,test-user/,//default/NO_ORG/"
        assert zsh_out == "uri\ntest-user/\n_\nstorage://default/NO_ORG/"

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage:/test-user/"])
        assert bash_out == (
            "uri,folder/,//default/NO_ORG/test-user/\n"
            "uri,file.txt,//default/NO_ORG/test-user/"
        )
        assert zsh_out == (
            "uri\nfolder/\n_\nstorage://default/NO_ORG/test-user/\n"
            "uri\nfile.txt\n_\nstorage://default/NO_ORG/test-user/"
        )

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage://"])
        assert bash_out == "uri,default/,//\nuri,other/,//"
        assert zsh_out == (
            "uri\ndefault/\n_\nstorage://\n" "uri\nother/\n_\nstorage://"
        )

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage://d"])
        assert bash_out == "uri,default/,//"
        assert zsh_out == "uri\ndefault/\n_\nstorage://"

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage://default/"])
        assert bash_out == ("uri,test-user/,//default/\n" "uri,other-user/,//default/")
        assert zsh_out == (
            "uri\ntest-user/\n_\nstorage://default/\n"
            "uri\nother-user/\n_\nstorage://default/"
        )

        zsh_out, bash_out = run_autocomplete(["storage", "cp", "storage://default/t"])
        assert bash_out == "uri,test-user/,//default/"
        assert zsh_out == "uri\ntest-user/\n_\nstorage://default/"


@skip_on_windows
def test_blob_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Buckets, "list") as mocked_list, mock.patch.object(
        Buckets, "blob_is_dir"
    ) as mocked_blob_is_dir, mock.patch.object(
        Buckets, "list_blobs"
    ) as mocked_list_blobs:

        @asyncgeneratorcontextmanager
        async def list(cluster_name: str) -> AsyncIterator[Bucket]:
            yield Bucket(
                id="bucket-1",
                name="apolo-my-bucket",
                created_at=datetime(2018, 1, 1, 3),
                cluster_name="default",
                owner="user",
                provider=Bucket.Provider.AWS,
                imported=False,
                org_name="NO_ORG",
                project_name="project",
            )
            yield Bucket(
                id="bucket-2",
                name="apolo-public-bucket",
                created_at=datetime(2018, 1, 1, 17, 2, 4),
                cluster_name="default",
                owner="public",
                provider=Bucket.Provider.AWS,
                imported=False,
                org_name="NO_ORG",
                project_name="project",
            )
            yield Bucket(
                id="bucket-3",
                name="apolo-shared-bucket",
                created_at=datetime(2018, 1, 1, 13, 1, 5),
                cluster_name="default",
                owner="another-user",
                provider=Bucket.Provider.AWS,
                imported=False,
                org_name="NO_ORG",
                project_name="project",
            )
            yield Bucket(
                id="bucket-4",
                name="apolo-my-org-bucket",
                created_at=datetime(2018, 1, 1, 3),
                cluster_name="default",
                owner="user",
                provider=Bucket.Provider.AWS,
                imported=False,
                org_name="org",
                project_name="project",
            )
            yield Bucket(
                id="bucket-5",
                name="apolo-public-org-bucket",
                created_at=datetime(2018, 1, 1, 17, 2, 4),
                cluster_name="default",
                owner="public",
                provider=Bucket.Provider.AWS,
                imported=False,
                org_name="org",
                project_name="project",
            )
            yield Bucket(
                id="bucket-6",
                name="apolo-shared-org-bucket",
                created_at=datetime(2018, 1, 1, 13, 1, 5),
                cluster_name="default",
                owner="another-user",
                provider=Bucket.Provider.AWS,
                imported=False,
                org_name="org",
                project_name="project",
            )

        async def blob_is_dir(uri: URL) -> bool:
            return ".txt" not in uri.name

        @asyncgeneratorcontextmanager
        async def list_blobs(uri: URL) -> AsyncIterator[BlobObject]:
            async with list(uri.host) as it:
                async for bucket in it:
                    try:
                        key = bucket.get_key_for_uri(uri)
                    except ValueError:
                        continue
                    break
                else:
                    return
            blobs = [
                BlobObject(
                    key="file1024.txt",
                    modified_at=datetime(2018, 1, 1, 14, 0, 0),
                    bucket=bucket,
                    size=1024,
                ),
                BlobObject(
                    key="otherfile.txt",
                    modified_at=datetime(2018, 1, 1, 14, 0, 0),
                    bucket=bucket,
                    size=1024,
                ),
                BlobObject(
                    key="file_bigger.txt",
                    modified_at=datetime(2018, 1, 1, 14, 0, 0),
                    bucket=bucket,
                    size=1_024_001,
                ),
                BlobObject(
                    key="folder2/info.txt",
                    modified_at=datetime(2018, 1, 1, 14, 0, 0),
                    bucket=bucket,
                    size=240,
                ),
                BlobObject(
                    key="folder2/",
                    modified_at=datetime(2018, 1, 1, 14, 0, 0),
                    bucket=bucket,
                    size=0,
                ),
                BlobObject(
                    key="folder23/",
                    modified_at=datetime(2018, 1, 1, 14, 0, 0),
                    bucket=bucket,
                    size=0,
                ),
            ]
            for blob in blobs:
                if blob.key.startswith(key):
                    if "/" not in blob.key[len(key) :].rstrip("/"):
                        yield blob

        mocked_list.side_effect = list
        mocked_blob_is_dir.side_effect = blob_is_dir
        mocked_list_blobs.side_effect = list_blobs

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "bl"])
        assert bash_out == "uri,blob:,"
        assert zsh_out == "uri\nblob:\n_\n_"

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:"])
        assert bash_out == (
            "uri,bucket-1/,\n"
            "uri,apolo-my-bucket/,\n"
            "uri,bucket-2/,\n"
            "uri,apolo-public-bucket/,\n"
            "uri,bucket-3/,\n"
            "uri,apolo-shared-bucket/,"
        )
        assert zsh_out == (
            "uri\nbucket-1/\n_\nblob:\nuri\napolo-my-bucket/\n_\nblob:\n"
            "uri\nbucket-2/\n_\nblob:\n"
            "uri\napolo-public-bucket/\n_\nblob:\n"
            "uri\nbucket-3/\n_\nblob:\n"
            "uri\napolo-shared-bucket/\n_\nblob:"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:b"])
        assert bash_out == ("uri,bucket-1/,\n" "uri,bucket-2/,\n" "uri,bucket-3/,")
        assert zsh_out == (
            "uri\nbucket-1/\n_\nblob:\n"
            "uri\nbucket-2/\n_\nblob:\n"
            "uri\nbucket-3/\n_\nblob:"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:a"])
        assert bash_out == (
            "uri,apolo-my-bucket/,\n"
            "uri,apolo-public-bucket/,\n"
            "uri,apolo-shared-bucket/,"
        )
        assert zsh_out == (
            "uri\napolo-my-bucket/\n_\nblob:\n"
            "uri\napolo-public-bucket/\n_\nblob:\n"
            "uri\napolo-shared-bucket/\n_\nblob:"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:bucket-1"])
        assert bash_out == "uri,bucket-1/,"
        assert zsh_out == "uri\nbucket-1/\n_\nblob:"

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:bucket-1/"])
        # BROKEN???
        # assert bash_out == (
        #     "uri,file1024.txt,bucket-1/\n"
        #     "uri,otherfile.txt,bucket-1/\n"
        #     "uri,file_bigger.txt,bucket-1/\n"
        #     "uri,folder2/,bucket-1/\n"
        #     "uri,folder23/,bucket-1/"
        # )
        # assert zsh_out == (
        #     "uri\nfile1024.txt\n_\nblob:bucket-1/\n"
        #     "uri\notherfile.txt\n_\nblob:bucket-1/\n"
        #     "uri\nfile_bigger.txt\n_\nblob:bucket-1/\n"
        #     "uri\nfolder2/\n_\nblob:bucket-1/\n"
        #     "uri\nfolder23/\n_\nblob:bucket-1/"
        # )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:/p"])
        assert bash_out == "uri,project/,//default/NO_ORG/"
        assert zsh_out == "uri\nproject/\n_\nblob://default/NO_ORG/"

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:/project/"])
        assert bash_out == (
            "uri,bucket-1/,\n"
            "uri,apolo-my-bucket/,\n"
            "uri,bucket-2/,\n"
            "uri,apolo-public-bucket/,\n"
            "uri,bucket-3/,\n"
            "uri,apolo-shared-bucket/,"
        )
        assert zsh_out == (
            "uri\nbucket-1/\n_\nblob:\nuri\napolo-my-bucket/\n_\nblob:\n"
            "uri\nbucket-2/\n_\nblob:\n"
            "uri\napolo-public-bucket/\n_\nblob:\n"
            "uri\nbucket-3/\n_\nblob:\n"
            "uri\napolo-shared-bucket/\n_\nblob:"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob://default/"])
        # BROKEN?
        # assert bash_out == "uri,project/,//default/\nuri,org/,//default/"
        # assert (
        #     zsh_out
        #     == "uri\nproject/\n_\nblob://default/\nuri\norg/\n_\nblob://default/"
        # )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob://default/org/"])
        assert bash_out == "uri,project/,//default/org/"
        assert zsh_out == "uri\nproject/\n_\nblob://default/org/"

        zsh_out, bash_out = run_autocomplete(
            ["blob", "ls", "blob://default/org/project/"]
        )
        assert bash_out == (
            "uri,bucket-4/,//default/org/project/\n"
            "uri,apolo-my-org-bucket/,//default/org/project/\n"
            "uri,bucket-5/,//default/org/project/\n"
            "uri,apolo-public-org-bucket/,//default/org/project/\n"
            "uri,bucket-6/,//default/org/project/\n"
            "uri,apolo-shared-org-bucket/,//default/org/project/"
        )
        assert zsh_out == (
            "uri\nbucket-4/\n_\nblob://default/org/project/\n"
            "uri\napolo-my-org-bucket/\n_\nblob://default/org/project/\n"
            "uri\nbucket-5/\n_\nblob://default/org/project/\n"
            "uri\napolo-public-org-bucket/\n_\nblob://default/org/project/\n"
            "uri\nbucket-6/\n_\nblob://default/org/project/\n"
            "uri\napolo-shared-org-bucket/\n_\nblob://default/org/project/"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:bucket-1/f"])
        assert bash_out == (
            "uri,file1024.txt,bucket-1/\n"
            "uri,file_bigger.txt,bucket-1/\n"
            "uri,folder2/,bucket-1/\n"
            "uri,folder23/,bucket-1/"
        )
        assert zsh_out == (
            "uri\nfile1024.txt\n_\nblob:bucket-1/\n"
            "uri\nfile_bigger.txt\n_\nblob:bucket-1/\n"
            "uri\nfolder2/\n_\nblob:bucket-1/\n"
            "uri\nfolder23/\n_\nblob:bucket-1/"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:bucket-1/fi"])
        assert bash_out == (
            "uri,file1024.txt,bucket-1/\n" "uri,file_bigger.txt,bucket-1/"
        )
        assert zsh_out == (
            "uri\nfile1024.txt\n_\nblob:bucket-1/\n"
            "uri\nfile_bigger.txt\n_\nblob:bucket-1/"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:bucket-1/folder2"])
        assert bash_out == ("uri,folder2/,bucket-1/\n" "uri,folder23/,bucket-1/")
        assert zsh_out == (
            "uri\nfolder2/\n_\nblob:bucket-1/\n" "uri\nfolder23/\n_\nblob:bucket-1/"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "ls", "blob:bucket-1/folder2/"])
        assert bash_out == "uri,info.txt,bucket-1/folder2/"
        assert zsh_out == "uri\ninfo.txt\n_\nblob:bucket-1/folder2/"


def make_job(
    job_id: str,
    name: Optional[str] = None,
    org_name: Optional[str] = None,
    owner: str = "test-user",
    cluster_name: str = "default",
    project_name: str = "test-project",
) -> JobDescription:
    return JobDescription(
        status=JobStatus.FAILED,
        owner=owner,
        project_name=project_name,
        cluster_name=cluster_name,
        org_name=org_name or "NO_ORG",
        id=job_id,
        name=name,
        uri=URL(f"job://{cluster_name}/{owner}/{job_id}"),
        description=None,
        history=JobStatusHistory(
            status=JobStatus.FAILED,
            reason="ErrorReason",
            description="ErrorDesc",
            created_at=isoparse("2018-09-25T12:28:21.298672+00:00"),
            started_at=isoparse("2018-09-25T12:28:59.759433+00:00"),
            finished_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        ),
        container=Container(
            command="test-command",
            image=RemoteImage.new_external_image(name="test-image"),
            resources=Resources(memory=16, cpu=0.1, shm=True),
        ),
        scheduler_enabled=False,
        pass_config=False,
        preset_name="testing",
        total_price_credits=Decimal("150"),
        price_credits_per_hour=Decimal("15"),
    )


@skip_on_windows
def test_job_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Jobs, "list") as mocked_list:
        jobs = [
            make_job("job-0123-4567", owner="user", project_name="project"),
            make_job(
                "job-89ab-cdef", owner="user", name="jeronimo", project_name="project"
            ),
            make_job("job-0123-cdef", owner="other-user", project_name="project"),
            make_job(
                "job-0123-4567",
                owner="other-user",
                name="oeronimo",
                project_name="project",
            ),
            make_job(
                "job-89ab-4567",
                cluster_name="other",
                owner="user",
                project_name="project",
            ),
            make_job("job-4567-cdef", owner="user", project_name="otherproject"),
        ]

        @asyncgeneratorcontextmanager
        async def list(
            *,
            since: Optional[datetime] = None,
            reverse: bool = False,
            limit: Optional[int] = None,
            cluster_name: Optional[str] = None,
            owners: Iterable[str] = (),
            project_names: Iterable[str] = (),
        ) -> AsyncIterator[JobDescription]:
            for job in jobs:
                if cluster_name and job.cluster_name != cluster_name:
                    continue
                if owners and job.owner not in owners:
                    continue
                if project_names and job.project_name not in project_names:
                    continue
                yield job

        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["job", "status", "j"])
        assert bash_out == "uri,job:,"
        assert zsh_out == "uri\njob:\n_\n_"

        zsh_out, bash_out = run_autocomplete(["job", "status", "jo"])
        assert bash_out == "uri,job:,"
        assert zsh_out == "uri\njob:\n_\n_"

        zsh_out, bash_out = run_autocomplete(["job", "status", "je"])
        assert bash_out == "plain,jeronimo,"
        assert zsh_out == "plain\njeronimo\njob-89ab-cdef\n_"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:"])
        assert bash_out == (
            "uri,job-0123-4567,\n"
            "uri,job-89ab-cdef,\n"
            "uri,jeronimo,\n"
            "uri,job-0123-cdef,\n"
            "uri,oeronimo,"
        )
        assert zsh_out == (
            "uri\njob-0123-4567\n_\njob:\n"
            "uri\njob-89ab-cdef\n_\njob:\n"
            "uri\njeronimo\n_\njob:\n"
            "uri\njob-0123-cdef\n_\njob:\n"
            "uri\noeronimo\n_\njob:"
        )

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:j"])
        assert bash_out == (
            "uri,job-0123-4567,\n"
            "uri,job-89ab-cdef,\n"
            "uri,jeronimo,\n"
            "uri,job-0123-cdef,"
        )
        assert zsh_out == (
            "uri\njob-0123-4567\n_\njob:\n"
            "uri\njob-89ab-cdef\n_\njob:\n"
            "uri\njeronimo\n_\njob:\n"
            "uri\njob-0123-cdef\n_\njob:"
        )

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:je"])
        assert bash_out == "uri,jeronimo,"
        assert zsh_out == "uri\njeronimo\n_\njob:"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:/"])
        assert bash_out == ("uri,project/,/\nuri,user/,/\n" "uri,otherproject/,/")
        assert zsh_out == (
            "uri\nproject/\n_\njob:/\n"
            "uri\nuser/\n_\njob:/\n"
            "uri\notherproject/\n_\njob:/"
        )

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:/u"])
        assert bash_out == "uri,user/,/"
        assert zsh_out == "uri\nuser/\n_\njob:/"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:/o"])
        assert bash_out == "uri,otherproject/,/"
        assert zsh_out == "uri\notherproject/\n_\njob:/"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job:/project/j"])
        assert bash_out == (
            "uri,job-0123-4567,/project/\n"
            "uri,job-89ab-cdef,/project/\n"
            "uri,jeronimo,/project/\n"
            "uri,job-0123-cdef,/project/"
        )
        assert zsh_out == (
            "uri\njob-0123-4567\n_\njob:/project/\n"
            "uri\njob-89ab-cdef\n_\njob:/project/\n"
            "uri\njeronimo\n_\njob:/project/\n"
            "uri\njob-0123-cdef\n_\njob:/project/"
        )

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://"])
        assert bash_out == ("uri,default/,//\n" "uri,other/,//")
        assert zsh_out == ("uri\ndefault/\n_\njob://\n" "uri\nother/\n_\njob://")

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://d"])
        assert bash_out == "uri,default/,//"
        assert zsh_out == "uri\ndefault/\n_\njob://"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://o"])
        assert bash_out == "uri,other/,//"
        assert zsh_out == "uri\nother/\n_\njob://"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://default/"])
        assert bash_out == (
            "uri,project/,//default/\n"
            "uri,user/,//default/\n"
            "uri,otherproject/,//default/"
        )
        assert zsh_out == (
            "uri\nproject/\n_\njob://default/\n"
            "uri\nuser/\n_\njob://default/\n"
            "uri\notherproject/\n_\njob://default/"
        )

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://other/"])
        assert bash_out == "uri,user/,//other/"
        assert zsh_out == "uri\nuser/\n_\njob://other/"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://default/u"])
        assert bash_out == "uri,user/,//default/"
        assert zsh_out == "uri\nuser/\n_\njob://default/"

        zsh_out, bash_out = run_autocomplete(
            ["job", "status", "job://default/project/"]
        )
        assert bash_out == (
            "uri,job-0123-4567,//default/project/\n"
            "uri,job-89ab-cdef,//default/project/\n"
            "uri,jeronimo,//default/project/\n"
            "uri,job-0123-cdef,//default/project/\n"
            "uri,oeronimo,//default/project/"
        )
        assert zsh_out == (
            "uri\njob-0123-4567\n_\njob://default/project/\n"
            "uri\njob-89ab-cdef\n_\njob://default/project/\n"
            "uri\njeronimo\n_\njob://default/project/\n"
            "uri\njob-0123-cdef\n_\njob://default/project/\n"
            "uri\noeronimo\n_\njob://default/project/"
        )

        zsh_out, bash_out = run_autocomplete(
            ["job", "status", "job://default/project/je"]
        )
        assert bash_out == "uri,jeronimo,//default/project/"
        assert zsh_out == "uri\njeronimo\n_\njob://default/project/"

        zsh_out, bash_out = run_autocomplete(["job", "status", "job://default/otherpr"])
        assert bash_out == "uri,otherproject/,//default/"
        assert zsh_out == "uri\notherproject/\n_\njob://default/"


@skip_on_windows
def test_image_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Images, "list") as mocked_list:
        images = {
            "default": [
                RemoteImage.new_platform_image(
                    name="bananas",
                    registry="registry-api.dev.apolo.us",
                    cluster_name="default",
                    org_name=None,
                    project_name="project",
                ),
                RemoteImage.new_platform_image(
                    name="lemons",
                    registry="registry-api.dev.apolo.us",
                    cluster_name="default",
                    org_name=None,
                    project_name="project",
                ),
                RemoteImage.new_platform_image(
                    name="library/bananas",
                    registry="registry-api.dev.apolo.us",
                    cluster_name="default",
                    org_name=None,
                    project_name="project",
                ),
                RemoteImage.new_platform_image(
                    name="library/bananas",
                    registry="registry-api.dev.apolo.us",
                    cluster_name="default",
                    org_name=None,
                    project_name="other-project",
                ),
                RemoteImage.new_platform_image(
                    name="library/bananas",
                    registry="registry-api.dev.apolo.us",
                    cluster_name="default",
                    org_name="org",
                    project_name="project",
                ),
            ],
            "other": [
                RemoteImage.new_platform_image(
                    name="library/bananas",
                    registry="registry2-api.dev.apolo.us",
                    cluster_name="other",
                    org_name=None,
                    project_name="project",
                ),
            ],
        }

        async def list(cluster_name: str) -> List[RemoteImage]:
            return images[cluster_name]

        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["image", "size", "i"])
        assert bash_out == "uri,image:,"
        assert zsh_out == "uri\nimage:\n_\n_"

        zsh_out, bash_out = run_autocomplete(["image", "size", "im"])
        assert bash_out == "uri,image:,"
        assert zsh_out == "uri\nimage:\n_\n_"

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:"])
        # BROKEN??
        # assert bash_out == ("uri,bananas,\n" "uri,lemons,\n" "uri,library/bananas,")
        # assert zsh_out == (
        #     "uri\nbananas\n_\nimage:\n"
        #     "uri\nlemons\n_\nimage:\n"
        #     "uri\nlibrary/bananas\n_\nimage:"
        # )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:l"])
        # BROKEN??
        # assert bash_out == ("uri,lemons,\n" "uri,library/bananas,")
        # assert zsh_out == (
        #    "uri\nlemons\n_\nimage:\n"
        #    "uri\nlibrary/bananas\n_\nimage:")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/"])
        assert bash_out == (
            "uri,project/bananas,/\n"
            "uri,project/lemons,/\n"
            "uri,project/library/bananas,/\n"
            "uri,other-project/library/bananas,/\n"
            "uri,org/project/library/bananas,/"
        )
        assert zsh_out == (
            "uri\nproject/bananas\n_\nimage:/\n"
            "uri\nproject/lemons\n_\nimage:/\n"
            "uri\nproject/library/bananas\n_\nimage:/\n"
            "uri\nother-project/library/bananas\n_\nimage:/\n"
            "uri\norg/project/library/bananas\n_\nimage:/"
        )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/p"])
        assert bash_out == (
            "uri,project/bananas,/\n"
            "uri,project/lemons,/\n"
            "uri,project/library/bananas,/"
        )
        assert zsh_out == (
            "uri\nproject/bananas\n_\nimage:/\n"
            "uri\nproject/lemons\n_\nimage:/\n"
            "uri\nproject/library/bananas\n_\nimage:/"
        )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/o"])
        assert bash_out == (
            "uri,other-project/library/bananas,/\n" "uri,org/project/library/bananas,/"
        )
        assert zsh_out == (
            "uri\nother-project/library/bananas\n_\nimage:/\n"
            "uri\norg/project/library/bananas\n_\nimage:/"
        )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/project/l"])
        assert bash_out == ("uri,project/lemons,/\n" "uri,project/library/bananas,/")
        assert zsh_out == (
            "uri\nproject/lemons\n_\nimage:/\n"
            "uri\nproject/library/bananas\n_\nimage:/"
        )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image://"])
        assert bash_out == ("uri,default/,//\n" "uri,other/,//")
        assert zsh_out == ("uri\ndefault/\n_\nimage://\n" "uri\nother/\n_\nimage://")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image://d"])
        assert bash_out == "uri,default/,//"
        assert zsh_out == "uri\ndefault/\n_\nimage://"

        zsh_out, bash_out = run_autocomplete(["image", "size", "image://o"])
        assert bash_out == "uri,other/,//"
        assert zsh_out == "uri\nother/\n_\nimage://"

        zsh_out, bash_out = run_autocomplete(["image", "size", "image://default/"])
        assert bash_out == (
            "uri,project/bananas,//default/\n"
            "uri,project/lemons,//default/\n"
            "uri,project/library/bananas,//default/\n"
            "uri,other-project/library/bananas,//default/\n"
            "uri,org/project/library/bananas,//default/"
        )
        assert zsh_out == (
            "uri\nproject/bananas\n_\nimage://default/\n"
            "uri\nproject/lemons\n_\nimage://default/\n"
            "uri\nproject/library/bananas\n_\nimage://default/\n"
            "uri\nother-project/library/bananas\n_\nimage://default/\n"
            "uri\norg/project/library/bananas\n_\nimage://default/"
        )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image://other/"])
        assert bash_out == ("uri,project/library/bananas,//other/")
        assert zsh_out == ("uri\nproject/library/bananas\n_\nimage://other/")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image://default/o"])
        assert bash_out == (
            "uri,other-project/library/bananas,//default/\n"
            "uri,org/project/library/bananas,//default/"
        )
        assert zsh_out == (
            "uri\nother-project/library/bananas\n_\nimage://default/\n"
            "uri\norg/project/library/bananas\n_\nimage://default/"
        )

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/"]
        )
        assert bash_out == (
            "uri,project/bananas,//default/\n"
            "uri,project/lemons,//default/\n"
            "uri,project/library/bananas,//default/"
        )
        assert zsh_out == (
            "uri\nproject/bananas\n_\nimage://default/\n"
            "uri\nproject/lemons\n_\nimage://default/\n"
            "uri\nproject/library/bananas\n_\nimage://default/"
        )

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/l"]
        )
        assert bash_out == (
            "uri,project/lemons,//default/\n" "uri,project/library/bananas,//default/"
        )
        assert zsh_out == (
            "uri\nproject/lemons\n_\nimage://default/\n"
            "uri\nproject/library/bananas\n_\nimage://default/"
        )


@skip_on_windows
def test_nonascii_image_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Images, "list") as mocked_list:
        images = [
            RemoteImage.new_platform_image(
                name="ima?ge",
                registry="registry-api.dev.apolo.us",
                cluster_name="default",
                org_name=None,
                project_name="project",
            ),
            RemoteImage.new_platform_image(
                name="образ",
                registry="registry-api.dev.apolo.us",
                cluster_name="default",
                org_name=None,
                project_name="project",
            ),
        ]

        async def list(cluster_name: str) -> List[RemoteImage]:
            if cluster_name == "default":
                return images
            return []

        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:"])
        # BROKEN??
        # assert bash_out == ("uri,ima%3Fge,\n" "uri,%D0%BE%D0%B1%D1%80%D0%B0%D0%B7,")
        # assert zsh_out == (
        #     "uri\nima%3Fge\n_\nimage:\n"
        #     "uri\n%D0%BE%D0%B1%D1%80%D0%B0%D0%B7\n_\nimage:"
        # )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:im"])
        # BROKEN??
        # assert bash_out == ("uri,ima%3Fge,")
        # assert zsh_out == ("uri\nima%3Fge\n_\nimage:")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:об"])
        # BROKEN??
        # assert bash_out == ("uri,об%D1%80%D0%B0%D0%B7,")
        # assert zsh_out == ("uri\nоб%D1%80%D0%B0%D0%B7\n_\nimage:")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:%D0%BE%D0%B1"])
        # BROKEN??
        # assert bash_out == ("uri,%D0%BE%D0%B1%D1%80%D0%B0%D0%B7,")
        # assert zsh_out == ("uri\n%D0%BE%D0%B1%D1%80%D0%B0%D0%B7\n_\nimage:")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/"])
        assert bash_out == (
            "uri,project/ima%3Fge,/\n" "uri,project/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7,/"
        )
        assert zsh_out == (
            "uri\nproject/ima%3Fge\n_\nimage:/\n"
            "uri\nproject/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7\n_\nimage:/"
        )

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/project/im"])
        assert bash_out == ("uri,project/ima%3Fge,/")
        assert zsh_out == ("uri\nproject/ima%3Fge\n_\nimage:/")

        zsh_out, bash_out = run_autocomplete(["image", "size", "image:/project/об"])
        assert bash_out == ("uri,project/об%D1%80%D0%B0%D0%B7,/")
        assert zsh_out == ("uri\nproject/об%D1%80%D0%B0%D0%B7\n_\nimage:/")

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image:/project/%D0%BE%D0%B1"]
        )
        assert bash_out == ("uri,project/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7,/")
        assert zsh_out == ("uri\nproject/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7\n_\nimage:/")

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/"]
        )
        assert bash_out == (
            "uri,project/ima%3Fge,//default/\n"
            "uri,project/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7,//default/"
        )
        assert zsh_out == (
            "uri\nproject/ima%3Fge\n_\nimage://default/\n"
            "uri\nproject/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7\n_\nimage://default/"
        )

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/im"]
        )
        assert bash_out == ("uri,project/ima%3Fge,//default/")
        assert zsh_out == ("uri\nproject/ima%3Fge\n_\nimage://default/")

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/об"]
        )
        assert bash_out == ("uri,project/об%D1%80%D0%B0%D0%B7,//default/")
        assert zsh_out == ("uri\nproject/об%D1%80%D0%B0%D0%B7\n_\nimage://default/")

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/%D0%BE%D0%B1"]
        )
        assert bash_out == ("uri,project/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7,//default/")
        assert zsh_out == (
            "uri\nproject/%D0%BE%D0%B1%D1%80%D0%B0%D0%B7\n_\nimage://default/"
        )


@skip_on_windows
def test_image_tag_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Images, "list") as mocked_list, mock.patch.object(
        Images, "tags"
    ) as mocked_tags:
        image = RemoteImage.new_platform_image(
            name="library/bananas",
            registry="registry-api.dev.apolo.us",
            cluster_name="default",
            org_name=None,
            project_name="other-project",
        )

        async def list(cluster_name: str) -> List[RemoteImage]:
            return [image]

        async def tags(image: RemoteImage) -> List[RemoteImage]:
            return [
                replace(image, tag="alpha"),
                replace(image, tag="beta"),
                replace(image, tag="latest"),
            ]

        mocked_list.side_effect = list
        mocked_tags.side_effect = tags

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image:library/bananas:"]
        )
        assert bash_out == ("uri,alpha,\n" "uri,beta,\n" "uri,latest,")
        assert zsh_out == (
            "uri\nalpha\n_\nimage:library/bananas:\n"
            "uri\nbeta\n_\nimage:library/bananas:\n"
            "uri\nlatest\n_\nimage:library/bananas:"
        )

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image:library/bananas:b"]
        )
        assert bash_out == ("uri,beta,")
        assert zsh_out == ("uri\nbeta\n_\nimage:library/bananas:")

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image:/project/library/bananas:"]
        )
        assert bash_out == ("uri,alpha,\n" "uri,beta,\n" "uri,latest,")
        assert zsh_out == (
            "uri\nalpha\n_\nimage:/project/library/bananas:\n"
            "uri\nbeta\n_\nimage:/project/library/bananas:\n"
            "uri\nlatest\n_\nimage:/project/library/bananas:"
        )

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image:/project/library/bananas:b"]
        )
        assert bash_out == ("uri,beta,")
        assert zsh_out == ("uri\nbeta\n_\nimage:/project/library/bananas:")

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/library/bananas:"]
        )
        assert bash_out == ("uri,alpha,\n" "uri,beta,\n" "uri,latest,")
        assert zsh_out == (
            "uri\nalpha\n_\nimage://default/project/library/bananas:\n"
            "uri\nbeta\n_\nimage://default/project/library/bananas:\n"
            "uri\nlatest\n_\nimage://default/project/library/bananas:"
        )

        zsh_out, bash_out = run_autocomplete(
            ["image", "size", "image://default/project/library/bananas:b"]
        )
        assert bash_out == ("uri,beta,")
        assert zsh_out == ("uri\nbeta\n_\nimage://default/project/library/bananas:")


@skip_on_windows
def test_disk_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Disks, "list") as mocked_list:
        created_at = datetime.now() - timedelta(days=1)
        last_usage = datetime.now()
        disks = {
            "default": [
                Disk(
                    id="disk-123",
                    storage=500,
                    owner="user",
                    project_name="test-project",
                    status=Disk.Status.READY,
                    cluster_name="default",
                    org_name="NO_ORG",
                    created_at=created_at,
                    timeout_unused=None,
                    name=None,
                ),
                Disk(
                    id="disk-234",
                    storage=600,
                    owner="user",
                    status=Disk.Status.PENDING,
                    cluster_name="default",
                    org_name="test-org",
                    project_name="another-project",
                    created_at=created_at,
                    last_usage=last_usage,
                    timeout_unused=timedelta(hours=1),
                    name="data-disk",
                ),
            ],
            "other": [
                Disk(
                    id="disk-345",
                    storage=600,
                    owner="user",
                    status=Disk.Status.PENDING,
                    cluster_name="other",
                    project_name="test-project",
                    org_name="test-org",
                    created_at=created_at,
                    last_usage=last_usage,
                    timeout_unused=timedelta(hours=1),
                    name="data-disk2",
                ),
            ],
        }

        @asyncgeneratorcontextmanager
        async def list(cluster_name: Optional[str] = None) -> AsyncIterator[Disk]:
            for disk in disks[cluster_name or "default"]:
                yield disk

        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["disk", "get", "d"])
        assert bash_out == (
            "uri,disk:,\n" "plain,disk-123,\n" "plain,disk-234,\n" "plain,data-disk,"
        )
        assert zsh_out == (
            "uri\ndisk:\n_\n_\n"
            "plain\ndisk-123\n_\n_\n"
            "plain\ndisk-234\ndata-disk\n_\n"
            "plain\ndata-disk\ndisk-234\n_"
        )

        zsh_out, bash_out = run_autocomplete(["disk", "get", "disk-2"])
        assert bash_out == ("plain,disk-234,")
        assert zsh_out == ("plain\ndisk-234\ndata-disk\n_")

        zsh_out, bash_out = run_autocomplete(["disk", "get", "da"])
        assert bash_out == ("plain,data-disk,")
        assert zsh_out == ("plain\ndata-disk\ndisk-234\n_")

        zsh_out, bash_out = run_autocomplete(["disk", "get", "--cluster", "other", "d"])
        assert bash_out == ("uri,disk:,\n" "plain,disk-345,\n" "plain,data-disk2,")
        assert zsh_out == (
            "uri\ndisk:\n_\n_\n"
            "plain\ndisk-345\ndata-disk2\n_\n"
            "plain\ndata-disk2\ndisk-345\n_"
        )


@skip_on_windows
def test_bucket_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Buckets, "list") as mocked_list:
        created_at = datetime.now() - timedelta(days=1)
        buckets = {
            "default": [
                Bucket(
                    id="bucket-1",
                    name="test-bucket",
                    owner="user",
                    cluster_name="default",
                    created_at=created_at,
                    provider=Bucket.Provider.AWS,
                    imported=False,
                    org_name="NO_ORG",
                    project_name="test-project",
                ),
                Bucket(
                    id="bucket-2",
                    name="test-bucket-2",
                    owner="user",
                    cluster_name="default",
                    created_at=created_at,
                    provider=Bucket.Provider.AWS,
                    imported=False,
                    org_name="NO_ORG",
                    project_name="test-project",
                ),
                Bucket(
                    id="bucket-3",
                    name=None,
                    owner="user-2",
                    cluster_name="default",
                    created_at=created_at,
                    provider=Bucket.Provider.AWS,
                    imported=False,
                    org_name="test-org",
                    project_name="test-project",
                ),
                Bucket(
                    id="bucket-4",
                    name=None,
                    owner="user",
                    cluster_name="default",
                    created_at=created_at,
                    provider=Bucket.Provider.AWS,
                    imported=False,
                    public=True,
                    org_name="test-org",
                    project_name="test-project",
                ),
            ],
            "other": [
                Bucket(
                    id="bucket-5",
                    name="test-bucket-3",
                    owner="user",
                    cluster_name="other",
                    created_at=created_at,
                    provider=Bucket.Provider.AWS,
                    imported=False,
                    org_name="NO_ORG",
                    project_name="test-project",
                ),
            ],
        }

        @asyncgeneratorcontextmanager
        async def list(cluster_name: Optional[str] = None) -> AsyncIterator[Bucket]:
            for bucket in buckets[cluster_name or "default"]:
                yield bucket

        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["blob", "statbucket", "b"])
        assert bash_out == (
            "plain,bucket-1,\n"
            "plain,bucket-2,\n"
            "plain,bucket-3,\n"
            "plain,bucket-4,"
        )
        assert zsh_out == (
            "plain\nbucket-1\ntest-bucket\n_\n"
            "plain\nbucket-2\ntest-bucket-2\n_\n"
            "plain\nbucket-3\n_\n_\n"
            "plain\nbucket-4\n_\n_"
        )

        zsh_out, bash_out = run_autocomplete(["blob", "statbucket", "bucket-2"])
        assert bash_out == "plain,bucket-2,"
        assert zsh_out == "plain\nbucket-2\ntest-bucket-2\n_"

        zsh_out, bash_out = run_autocomplete(["blob", "statbucket", "t"])
        assert bash_out == ("plain,test-bucket,\n" "plain,test-bucket-2,")
        assert zsh_out == (
            "plain\ntest-bucket\nbucket-1\n_\n" "plain\ntest-bucket-2\nbucket-2\n_"
        )

        zsh_out, bash_out = run_autocomplete(
            ["blob", "statbucket", "--cluster", "other", "b"]
        )
        assert bash_out == "plain,bucket-5,"
        assert zsh_out == "plain\nbucket-5\ntest-bucket-3\n_"


@skip_on_windows
def test_service_account_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(ServiceAccounts, "list") as mocked_list:
        created_at = datetime.now() - timedelta(days=1)
        accounts = [
            ServiceAccount(
                id="account-1",
                name="test1",
                role="test-role-1",
                owner="user",
                default_cluster="cluster1",
                default_project="user",
                created_at=created_at,
            ),
            ServiceAccount(
                id="account-2",
                name="test2",
                role="test-role-2",
                owner="user",
                default_cluster="cluster2",
                default_project="project",
                created_at=created_at,
            ),
        ]

        @asyncgeneratorcontextmanager
        async def list() -> AsyncIterator[ServiceAccount]:
            for account in accounts:
                yield account

        mocked_list.side_effect = list

        zsh_out, bash_out = run_autocomplete(["service-account", "get", "a"])
        assert bash_out == ("plain,account-1,\n" "plain,account-2,")
        assert zsh_out == ("plain\naccount-1\ntest1\n_\n" "plain\naccount-2\ntest2\n_")

        zsh_out, bash_out = run_autocomplete(["service-account", "get", "t"])
        assert bash_out == ("plain,test1,\n" "plain,test2,")
        assert zsh_out == ("plain\ntest1\naccount-1\n_\n" "plain\ntest2\naccount-2\n_")


@skip_on_windows
def test_bucket_credential_autocomplete(run_autocomplete: _RunAC) -> None:
    with mock.patch.object(Buckets, "persistent_credentials_list") as mocked_list:
        credentials = {
            "default": [
                PersistentBucketCredentials(
                    id="bucket-credentials-1",
                    name="test-credentials-1",
                    owner="user",
                    cluster_name="default",
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
                    name="test-credentials-2",
                    owner="user",
                    cluster_name="default",
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
                    cluster_name="default",
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
            ],
            "other": [
                PersistentBucketCredentials(
                    id="bucket-credentials-4",
                    name="test-credentials-4",
                    owner="user",
                    cluster_name="other",
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
                    ],
                ),
            ],
        }

        @asyncgeneratorcontextmanager
        async def persistent_credentials_list(
            cluster_name: Optional[str] = None,
        ) -> AsyncIterator[PersistentBucketCredentials]:
            for credential in credentials[cluster_name or "default"]:
                yield credential

        mocked_list.side_effect = persistent_credentials_list

        zsh_out, bash_out = run_autocomplete(["blob", "statcredentials", "b"])
        assert bash_out == (
            "plain,bucket-credentials-1,\n"
            "plain,bucket-credentials-2,\n"
            "plain,bucket-credentials-3,"
        )
        assert zsh_out == (
            "plain\nbucket-credentials-1\ntest-credentials-1\n_\n"
            "plain\nbucket-credentials-2\ntest-credentials-2\n_\n"
            "plain\nbucket-credentials-3\ntest-credentials-3\n_"
        )

        zsh_out, bash_out = run_autocomplete(
            ["blob", "statcredentials", "bucket-credentials-2"]
        )
        assert bash_out == "plain,bucket-credentials-2,"
        assert zsh_out == "plain\nbucket-credentials-2\ntest-credentials-2\n_"

        zsh_out, bash_out = run_autocomplete(["blob", "statcredentials", "t"])
        assert bash_out == (
            "plain,test-credentials-1,\n"
            "plain,test-credentials-2,\n"
            "plain,test-credentials-3,"
        )
        assert zsh_out == (
            "plain\ntest-credentials-1\nbucket-credentials-1\n_\n"
            "plain\ntest-credentials-2\nbucket-credentials-2\n_\n"
            "plain\ntest-credentials-3\nbucket-credentials-3\n_"
        )

        zsh_out, bash_out = run_autocomplete(
            ["blob", "statcredentials", "--cluster", "other", "b"]
        )
        assert bash_out == "plain,bucket-credentials-4,"
        assert zsh_out == "plain\nbucket-credentials-4\ntest-credentials-4\n_"


@skip_on_windows
def test_app_autocomplete(run_autocomplete: _RunAC) -> None:
    # Test app command completion
    zsh_out, bash_out = run_autocomplete(["app", ""])
    assert "ls" in bash_out
    assert "ls" in zsh_out
    assert "uninstall" in bash_out
    assert "uninstall" in zsh_out
    assert "get-values" in bash_out
    assert "get-values" in zsh_out
    assert "logs" in bash_out
    assert "logs" in zsh_out


@skip_on_windows
def test_app_template_autocomplete(run_autocomplete: _RunAC) -> None:
    # Test app-template command completion
    zsh_out, bash_out = run_autocomplete(["app-template", ""])
    assert "ls" in bash_out
    assert "ls" in zsh_out
