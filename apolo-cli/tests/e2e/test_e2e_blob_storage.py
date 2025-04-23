import os
import subprocess
import sys
from pathlib import Path, PurePath
from typing import Tuple

import pytest

from apolo_cli.const import EX_OSFILE

from tests.e2e import Helper
from tests.e2e.utils import FILE_SIZE_B

_Data = Tuple[str, str]


@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: apolo_sdk.BadGateway: Bad Gateway")
def test_e2e_blob_storage_upload_download(
    data: Tuple[Path, str], tmp_path: Path, helper: Helper, tmp_bucket: str
) -> None:
    srcfile, checksum = data
    key = "folder/foo"

    # Upload local file
    helper.upload_blob(bucket_name=tmp_bucket, key=key, file=srcfile)

    # Confirm file has been uploaded
    helper.check_blob_size(tmp_bucket, key, FILE_SIZE_B)

    # Download into local file and confirm checksum
    helper.check_blob_checksum(tmp_bucket, key, checksum, tmp_path / "bar")


@pytest.mark.e2e
def test_e2e_blob_storage_ls_buckets(helper: Helper, tmp_bucket: str) -> None:
    # Ensure output of ls - empty directory shall print nothing.
    captured = helper.run_cli(["blob", "ls"])
    assert "blob:" + tmp_bucket in captured.out


@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: apolo_sdk.BadGateway: Bad Gateway")
def test_e2e_blob_storage_ls_blobs_empty_bucket(
    helper: Helper, tmp_bucket: str
) -> None:
    # Ensure output of ls - empty directory shall print nothing.
    captured = helper.run_cli(["blob", "ls", "blob:" + tmp_bucket])
    assert not captured.out


@pytest.mark.e2e
@pytest.mark.skip(
    reason=(
        "ERROR: apolo_sdk.IllegalArgumentError: Unexpected exception: "
        "[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]"
    )
)
def test_e2e_blob_storage_copy_file_implicit_directory(
    helper: Helper, data: _Data, tmp_bucket: str
) -> None:
    srcfile, checksum = data
    file_name = str(PurePath(srcfile).name)
    key = f"folder/{file_name}"

    # Upload local file to a directory defined by trailing slash
    helper.run_cli(["blob", "cp", srcfile, f"blob:{tmp_bucket}/folder/"])

    # Ensure file is there
    helper.check_blob_size(tmp_bucket, key, FILE_SIZE_B)


@pytest.mark.e2e
@pytest.mark.skip(
    reason=(
        "ERROR: apolo_sdk.IllegalArgumentError: Unexpected exception: "
        "Remote end closed connection without response"
    )
)
def test_e2e_blob_storage_copy_file_explicit_directory(
    helper: Helper, data: _Data, tmp_bucket: str
) -> None:
    srcfile, checksum = data
    file_name = str(PurePath(srcfile).name)
    key = f"folder/{file_name}"

    # Upload local file to existing directory with explicit -t param
    helper.run_cli(["blob", "cp", "-t", f"blob:{tmp_bucket}/folder", srcfile])

    # Ensure file is there
    helper.check_blob_size(tmp_bucket, key, FILE_SIZE_B)


@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: apolo_sdk.BadGateway: Bad Gateway")
def test_e2e_blob_storage_copy_file_to_folder_key(
    helper: Helper, data: _Data, tmp_bucket: str
) -> None:
    srcfile, checksum = data
    file_name = str(PurePath(srcfile).name)
    stub_key = "folder/bar"
    key = f"folder/{file_name}"
    folder_uri = f"blob:{tmp_bucket}/folder"

    # First upload to a nested path
    helper.upload_blob(bucket_name=tmp_bucket, key=stub_key, file=srcfile)

    # Second will succeed, but upload the file `under` the `folder`,
    # as it's a folder key
    helper.run_cli(["blob", "cp", srcfile, folder_uri])
    helper.check_blob_size(tmp_bucket, stub_key, FILE_SIZE_B)
    helper.check_blob_size(tmp_bucket, key, FILE_SIZE_B)

    # Second we do the same command, but with -T that should raise an error
    with pytest.raises(
        subprocess.CalledProcessError,
        match=f"returned non-zero exit status {EX_OSFILE}",
    ):
        helper.run_cli(["blob", "cp", "-T", srcfile, folder_uri])


@pytest.mark.e2e
def test_e2e_blob_storage_copy_no_sources_no_destination(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["blob", "cp"])
    assert 'Missing argument "DESTINATION"' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_blob_storage_copy_no_sources(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["blob", "cp", "blob:foo"])
    assert 'Missing argument "SOURCES..."' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_blob_storage_copy_no_sources_target_directory(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["blob", "cp", "-t", "blob:foo"])
    assert 'Missing argument "SOURCES..."' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_blob_storage_copy_target_directory_no_target_directory(
    helper: Helper, tmp_path: Path
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["blob", "cp", "-t", "blob:foo", "-T", str(tmp_path)])
    assert "Cannot combine" in cm.value.stderr


@pytest.mark.e2e
def test_e2e_blob_storage_copy_no_target_directory_extra_operand(
    helper: Helper, tmp_path: Path
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["blob", "cp", "-T", str(tmp_path), "blob:foo", str(tmp_path)])
    assert "Extra operand after " in cm.value.stderr


@pytest.mark.e2e
@pytest.mark.skip(
    reason="Unexpected exception: [SSL: WRONG_VERSION_NUMBER] wrong version number"
)
def test_e2e_blob_storage_copy_recursive_folder(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path, tmp_bucket: str
) -> None:
    srcfile, checksum, dir_path = nested_data
    target_file_name = Path(srcfile).name

    # Upload local folder .../nested_data/nested to bucket root
    helper.run_cli(["blob", "cp", "-r", dir_path, f"blob:{tmp_bucket}"])

    helper.check_blob_size(
        tmp_bucket, f"nested/directory/for/test/{target_file_name}", FILE_SIZE_B // 3
    )

    # Download into local directory and confirm checksum
    targetdir = tmp_path / "bar"
    targetdir.mkdir()
    helper.run_cli(["blob", "cp", "-r", f"blob:{tmp_bucket}/", str(targetdir)])
    targetfile = targetdir / "nested" / "directory" / "for" / "test" / target_file_name
    assert helper.hash_hex(targetfile) == checksum


@pytest.mark.e2e
@pytest.mark.skip(
    reason="Unexpected exception: [SSL: WRONG_VERSION_NUMBER] wrong version number"
)
def test_e2e_blob_storage_copy_recursive_file(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path, tmp_bucket: str
) -> None:
    srcfile = tmp_path / "testfile"
    dstfile = tmp_path / "copyfile"
    srcfile.write_bytes(b"abc")

    captured = helper.run_cli(["blob", "cp", "-r", str(srcfile), f"blob:{tmp_bucket}"])
    assert not captured.out

    captured = helper.run_cli(
        ["blob", "cp", "-r", f"blob:{tmp_bucket}/testfile", str(dstfile)]
    )
    assert not captured.out

    assert dstfile.read_bytes() == b"abc"


@pytest.mark.e2e
def test_e2e_blob_storage_glob_copy(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path, tmp_bucket: str
) -> None:
    # Create files and directories and copy them with pattern
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "subfolder").mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    (folder / "baz").write_bytes(b"baz")
    helper.run_cli(
        ["blob", "cp", "-r", tmp_path.as_uri() + "/f*", f"blob:{tmp_bucket}/folder"]
    )
    captured = helper.run_cli(["blob", "ls", f"blob:{tmp_bucket}/folder/"])
    prefix = f"blob:{tmp_bucket}/folder/"
    assert sorted(captured.out.splitlines()) == [
        prefix,
        prefix + "bar",
        prefix + "baz",
        prefix + "foo",
        prefix + "subfolder/",
    ]

    # Test subcommand "glob"
    captured = helper.run_cli(["blob", "glob", f"blob:{tmp_bucket}/folder/*o*"])
    assert sorted(captured.out.splitlines()) == [
        prefix + "foo",
        prefix + "subfolder/",
    ]

    # Download files with pattern
    download = tmp_path / "download"
    download.mkdir()
    helper.run_cli(["blob", "cp", f"blob:{tmp_bucket}/**/b*" + "", str(download)])
    assert sorted(download.iterdir()) == [download / "bar", download / "baz"]


@pytest.mark.e2e
@pytest.mark.skip(
    reason="Unexpected exception: [SSL: WRONG_VERSION_NUMBER] wrong version number"
)
def test_e2e_blob_storage_cp_filter(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path, tmp_bucket: str
) -> None:
    # Create files and directories and copy them to storage
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "subfolder").mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    (folder / "baz").write_bytes(b"baz")

    helper.run_cli(
        [
            "blob",
            "cp",
            "-r",
            "--exclude",
            "*",
            "--include",
            "b??",
            "--exclude",
            "*z",
            tmp_path.as_uri() + "/folder",
            f"blob:{tmp_bucket}/filtered",
        ]
    )
    captured = helper.run_cli(["blob", "ls", f"blob:{tmp_bucket}/filtered/"])
    prefix = f"blob:{tmp_bucket}/filtered/"
    assert sorted(captured.out.splitlines()) == [prefix, prefix + "bar"]

    # Copy all files to storage
    helper.run_cli(
        [
            "blob",
            "cp",
            "-r",
            tmp_path.as_uri() + "/folder",
            f"blob:{tmp_bucket}/folder",
        ]
    )

    # Copy filtered files from storage
    helper.run_cli(
        [
            "blob",
            "cp",
            "-r",
            "--exclude",
            "*",
            "--include",
            "b??",
            "--exclude",
            "*z",
            f"blob:{tmp_bucket}" + "/folder",
            tmp_path.as_uri() + "/filtered",
        ]
    )
    assert os.listdir(tmp_path / "filtered") == ["bar"]


@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: apolo_sdk.BadGateway: Bad Gateway")
def test_e2e_blob_storage_rm_file(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path, tmp_bucket: str
) -> None:
    srcfile = tmp_path / "testfile"
    srcfile.write_bytes(b"abc")

    captured = helper.run_cli(["blob", "cp", str(srcfile), f"blob:{tmp_bucket}"])
    assert not captured.out

    helper.run_cli(["blob", "rm", f"blob:{tmp_bucket}/testfile"])

    captured = helper.run_cli(["blob", "ls", f"blob:{tmp_bucket}/testfile"])
    assert not captured.out


@pytest.mark.e2e
def test_e2e_blob_storage_rm_dir(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path, tmp_bucket: str
) -> None:
    srcfile = tmp_path / "testfile"
    srcfile.write_bytes(b"abc")

    captured = helper.run_cli(
        ["blob", "cp", str(srcfile), f"blob:{tmp_bucket}/some_dir/"]
    )
    assert not captured.out

    helper.run_cli(["blob", "rm", "-r", f"blob:{tmp_bucket}/some_dir/"])

    captured = helper.run_cli(["blob", "ls", f"blob:{tmp_bucket}/some_dir/"])
    assert not captured.out


@pytest.mark.skipif(
    sys.platform == "win32", reason="Autocompletion is not supported on Windows"
)
@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: apolo_sdk.BadGateway: Bad Gateway")
def test_blob_autocomplete(helper: Helper, tmp_path: Path, tmp_bucket: str) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    subfolder = folder / "folder"
    subfolder.mkdir()
    (subfolder / "baz").write_bytes(b"baz")

    base_blob_uri = f"blob:{tmp_bucket}/some_dir"

    helper.run_cli(["blob", "cp", "-r", folder.as_uri(), base_blob_uri])

    out = helper.autocomplete(["blob", "ls", "bl"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "blob:" in completion_keys

    out = helper.autocomplete(["blob", "cp", f"{base_blob_uri}/"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "folder/" in completion_keys
    assert "foo" in completion_keys
    assert "bar" in completion_keys

    out = helper.autocomplete(["blob", "cp", f"{base_blob_uri}/fo"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "folder/" in completion_keys
    assert "foo" in completion_keys
    assert "bar" not in completion_keys

    out = helper.autocomplete(["blob", "cp", f"{base_blob_uri}/folder/"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "baz" in completion_keys
