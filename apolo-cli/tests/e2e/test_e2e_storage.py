import errno
import os
import subprocess
import sys
import textwrap
from pathlib import Path, PurePath
from typing import Tuple

import pytest

from apolo_cli.const import EX_OSFILE
from apolo_cli.formatters.storage import TreeFormatter

from tests.e2e import Helper
from tests.e2e.utils import FILE_SIZE_B

_Data = Tuple[str, str]


@pytest.mark.e2e
def test_e2e_storage(data: Tuple[Path, str], tmp_path: Path, helper: Helper) -> None:
    srcfile, checksum = data

    # Create directory for the test
    helper.mkdir("folder", parents=True)

    # Upload local file
    helper.check_upload_file_to_storage("foo", "folder", str(srcfile))

    # Confirm file has been uploaded
    helper.check_file_exists_on_storage("foo", "folder", FILE_SIZE_B)

    # Download into local file and confirm checksum
    helper.check_file_on_storage_checksum(
        "foo", "folder", checksum, str(tmp_path), "bar"
    )

    # Rename file on the storage
    helper.check_rename_file_on_storage("foo", "folder", "bar", "folder")
    helper.check_file_exists_on_storage("bar", "folder", FILE_SIZE_B)

    # Rename directory on the storage
    helper.check_rename_directory_on_storage("folder", "folder2")
    helper.check_file_exists_on_storage("bar", "folder2", FILE_SIZE_B)

    # Non-recursive removing should not have any effect
    with pytest.raises(IsADirectoryError, match=".+Target is a directory") as cm:
        helper.rm("folder2", recursive=False)
    assert cm.value.errno == errno.EISDIR
    helper.check_file_exists_on_storage("bar", "folder2", FILE_SIZE_B)


@pytest.mark.e2e
def test_empty_directory_ls_output(helper: Helper) -> None:
    helper.mkdir("")
    # Ensure output of ls - empty directory shall print nothing.
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage])
    assert not captured.out


@pytest.mark.e2e
def test_ls_directory_itself(helper: Helper) -> None:
    helper.mkdir("")
    captured = helper.run_cli(["storage", "ls", "--directory", helper.tmpstorage])
    _, _, name = helper.tmpstoragename.rpartition("/")
    assert captured.out.splitlines() == [name]


@pytest.mark.e2e
def test_e2e_mkdir(helper: Helper) -> None:
    helper.run_cli(["storage", "mkdir", "--parents", helper.tmpstorage / "folder"])
    helper.check_dir_exists_on_storage("folder", "")

    # Create existing directory
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "mkdir", helper.tmpstorage / "folder"])
    assert cm.value.returncode == EX_OSFILE
    helper.mkdir("folder", exist_ok=True)

    # Create a subdirectory in existing directory
    helper.run_cli(["storage", "mkdir", helper.tmpstorage / "folder/subfolder"])
    helper.check_dir_exists_on_storage("subfolder", "folder")

    # Create a subdirectory in non-existing directory
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "mkdir", helper.tmpstorage / "parent/child"])
    assert cm.value.returncode == EX_OSFILE
    helper.check_dir_absent_on_storage("parent", "")
    helper.run_cli(
        ["storage", "mkdir", "--parents", helper.tmpstorage / "parent/child"]
    )
    helper.check_dir_exists_on_storage("parent", "")
    helper.check_dir_exists_on_storage("child", "parent")


@pytest.mark.e2e
def test_copy_local_file_to_platform_directory(helper: Helper, data2: _Data) -> None:
    srcfile, checksum = data2
    file_name = str(PurePath(srcfile).name)

    helper.mkdir("folder", parents=True)
    # Upload local file to existing directory
    helper.run_cli(["storage", "cp", srcfile, helper.tmpstorage / "folder"])

    # Ensure file is there
    helper.check_file_exists_on_storage(file_name, "folder", FILE_SIZE_B // 3)


@pytest.mark.e2e
def test_copy_local_file_to_platform_directory_explicit(
    helper: Helper, data2: _Data
) -> None:
    srcfile, checksum = data2
    file_name = str(PurePath(srcfile).name)

    helper.mkdir("folder", parents=True)
    # Upload local file to existing directory
    helper.run_cli(["storage", "cp", "-t", helper.tmpstorage / "folder", srcfile])

    # Ensure file is there
    helper.check_file_exists_on_storage(file_name, "folder", FILE_SIZE_B // 3)


@pytest.mark.e2e
def test_copy_local_single_file_to_platform_file(helper: Helper, data: _Data) -> None:
    # case when copy happens with rename to 'different_name.txt'
    srcfile, checksum = data
    file_name = str(PurePath(srcfile).name)

    helper.mkdir("folder", parents=True)
    # Upload local file to platform
    helper.run_cli(
        ["storage", "cp", srcfile, helper.tmpstorage / "folder/different_name.txt"]
    )

    # Ensure file is there
    helper.check_file_exists_on_storage("different_name.txt", "folder", FILE_SIZE_B)
    helper.check_file_absent_on_storage(file_name, "folder")


@pytest.mark.e2e
def test_copy_local_single_file_to_platform_file_explicit(
    helper: Helper, data2: _Data
) -> None:
    # case when copy happens with rename to 'different_name.txt'
    srcfile, checksum = data2
    file_name = str(PurePath(srcfile).name)

    helper.mkdir("folder", parents=True)
    # Upload local file to platform
    helper.run_cli(
        [
            "storage",
            "cp",
            "-T",
            srcfile,
            helper.tmpstorage / "folder/different_name.txt",
        ]
    )

    # Ensure file is there
    helper.check_file_exists_on_storage(
        "different_name.txt", "folder", FILE_SIZE_B // 3
    )
    helper.check_file_absent_on_storage(file_name, "folder")


@pytest.mark.e2e
def test_copy_local_to_platform_single_file_3(helper: Helper, data: _Data) -> None:
    # case when copy happens with rename to 'different_name.txt'
    srcfile, checksum = data

    helper.mkdir("")

    # Upload local file to non existing directory
    with pytest.raises(subprocess.CalledProcessError, match=str(EX_OSFILE)):
        captured = helper.run_cli(
            ["storage", "cp", srcfile, helper.tmpstorage / "non_existing_dir/"]
        )
        assert not captured.err
        assert captured.out == ""

    # Ensure dir is not created
    helper.check_dir_absent_on_storage("non_existing_dir", "")


@pytest.mark.e2e
def test_e2e_copy_non_existing_platform_to_non_existing_local(
    helper: Helper, tmp_path: Path
) -> None:
    # Try downloading non existing file
    with pytest.raises(subprocess.CalledProcessError, match=str(EX_OSFILE)):
        helper.run_cli(
            [
                "storage",
                "cp",
                helper.tmpstorage / "not-exist-foo",
                str(tmp_path / "not-exist-bar"),
            ]
        )


@pytest.mark.e2e
def test_e2e_copy_non_existing_platform_to_____existing_local(
    helper: Helper, tmp_path: Path
) -> None:
    # Try downloading non existing file
    with pytest.raises(subprocess.CalledProcessError, match=str(EX_OSFILE)):
        helper.run_cli(["storage", "cp", helper.tmpstorage / "foo", str(tmp_path)])


@pytest.mark.e2e
def test_e2e_copy_no_sources_no_destination(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "cp"])
    assert 'Missing argument "DESTINATION"' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_copy_no_sources(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "cp", helper.tmpstorage])
    assert 'Missing argument "SOURCES..."' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_copy_no_sources_target_directory(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "cp", "-t", helper.tmpstorage])
    assert 'Missing argument "SOURCES..."' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_copy_target_directory_no_target_directory(
    helper: Helper, tmp_path: Path
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "cp", "-t", helper.tmpstorage, "-T", str(tmp_path)])
    assert "Cannot combine" in cm.value.stderr


@pytest.mark.e2e
def test_e2e_copy_no_target_directory_extra_operand(
    helper: Helper, tmp_path: Path
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            ["storage", "cp", "-T", str(tmp_path), helper.tmpstorage, str(tmp_path)]
        )
    assert "Extra operand after " in cm.value.stderr


@pytest.mark.e2e
def test_copy_and_remove_multiple_files(
    helper: Helper, data2: _Data, data3: _Data, tmp_path: Path
) -> None:
    helper.mkdir("")
    # case when copy happens with rename to 'different_name.txt'
    srcfile, checksum = data2
    srcfile2, checksum2 = data3
    srcname = os.path.basename(srcfile)
    srcname2 = os.path.basename(srcfile2)

    # Upload local files
    captured = helper.run_cli(["storage", "cp", srcfile, srcfile2, helper.tmpstorage])
    assert captured.out == ""

    # Confirm files has been uploaded
    helper.check_file_exists_on_storage(srcname, "", FILE_SIZE_B // 3)
    helper.check_file_exists_on_storage(srcname2, "", FILE_SIZE_B // 5)

    # Download into local directory and confirm checksum
    targetdir = tmp_path / "bar"
    targetdir.mkdir()
    helper.run_cli(
        [
            "storage",
            "cp",
            helper.tmpstorage / srcname,
            helper.tmpstorage / srcname2,
            str(targetdir),
        ]
    )
    assert helper.hash_hex(targetdir / srcname) == checksum
    assert helper.hash_hex(targetdir / srcname2) == checksum2

    # Remove the files from platform
    captured = helper.run_cli(
        [
            "storage",
            "rm",
            helper.tmpstorage / srcname,
            helper.tmpstorage / srcname2,
        ]
    )
    assert captured.out == ""

    # Ensure files are not there
    helper.check_file_absent_on_storage(srcname, "")
    helper.check_file_absent_on_storage(srcname2, "")


@pytest.mark.e2e
def test_e2e_copy_recursive_to_platform(
    helper: Helper, nested_data: Tuple[str, str, str], tmp_path: Path
) -> None:
    helper.mkdir("")
    srcfile, checksum, dir_path = nested_data
    target_file_name = Path(srcfile).name

    # Upload local file
    captured = helper.run_cli(["storage", "cp", "-r", dir_path, helper.tmpstorage])
    # stderr has logs like "Using path ..."
    # assert not captured.err
    assert not captured.out

    helper.check_file_exists_on_storage(
        target_file_name, f"nested/directory/for/test", FILE_SIZE_B // 3
    )

    # Download into local directory and confirm checksum
    targetdir = tmp_path / "bar"
    targetdir.mkdir()
    helper.run_cli(["storage", "cp", "-r", "-T", helper.tmpstorage, str(targetdir)])
    targetfile = targetdir / "nested" / "directory" / "for" / "test" / target_file_name
    print("source file", srcfile)
    print("target file", targetfile)
    assert helper.hash_hex(targetfile) == checksum


@pytest.mark.e2e
def test_e2e_copy_recursive_file(helper: Helper, tmp_path: Path) -> None:
    helper.mkdir("")
    srcfile = tmp_path / "testfile"
    dstfile = tmp_path / "copyfile"
    srcfile.write_bytes(b"abc")

    captured = helper.run_cli(["storage", "cp", "-r", str(srcfile), helper.tmpstorage])
    assert not captured.out

    captured = helper.run_cli(
        ["storage", "cp", "-r", helper.tmpstorage / "testfile", str(dstfile)]
    )
    assert not captured.out

    assert dstfile.read_bytes() == b"abc"


@pytest.mark.e2e
def test_e2e_rename(helper: Helper) -> None:
    helper.mkdir("folder", parents=True)
    helper.run_cli(
        [
            "storage",
            "mv",
            helper.tmpstorage / "folder",
            helper.tmpstorage / "otherfolder",
        ]
    )
    helper.check_dir_absent_on_storage("folder", "")
    helper.check_dir_exists_on_storage("otherfolder", "")


@pytest.mark.e2e
def test_e2e_move_to_directory(helper: Helper) -> None:
    helper.mkdir("folder", parents=True)
    helper.mkdir("otherfolder", parents=True)
    helper.run_cli(
        [
            "storage",
            "mv",
            helper.tmpstorage / "folder",
            helper.tmpstorage / "otherfolder",
        ]
    )
    helper.check_dir_absent_on_storage("folder", "")
    helper.check_dir_exists_on_storage("otherfolder", "")
    helper.check_dir_exists_on_storage("folder", "otherfolder")


@pytest.mark.e2e
def test_e2e_move_to_directory_explicitly(helper: Helper) -> None:
    helper.mkdir("folder", parents=True)
    helper.mkdir("otherfolder", parents=True)
    helper.run_cli(
        [
            "storage",
            "mv",
            "-t",
            helper.tmpstorage / "otherfolder",
            helper.tmpstorage / "folder",
        ]
    )
    helper.check_dir_absent_on_storage("folder", "")
    helper.check_dir_exists_on_storage("otherfolder", "")
    helper.check_dir_exists_on_storage("folder", "otherfolder")


@pytest.mark.e2e
def test_e2e_move_content_to_directory(helper: Helper) -> None:
    helper.mkdir("folder/subfolder", parents=True)
    helper.mkdir("otherfolder", parents=True)
    helper.run_cli(
        [
            "storage",
            "mv",
            "-T",
            helper.tmpstorage / "folder",
            helper.tmpstorage / "otherfolder",
        ]
    )
    helper.check_dir_absent_on_storage("folder", "")
    helper.check_dir_exists_on_storage("subfolder", "otherfolder")


@pytest.mark.e2e
def test_e2e_move_no_sources_no_destination(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "mv"])
    assert 'Missing argument "DESTINATION"' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_move_no_sources(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "mv", helper.tmpstorage])
    assert 'Missing argument "SOURCES..."' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_move_no_sources_target_directory(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["storage", "mv", "-t", helper.tmpstorage])
    assert 'Missing argument "SOURCES..."' in cm.value.stderr


@pytest.mark.e2e
def test_e2e_move_target_directory_no_target_directory(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            [
                "storage",
                "mv",
                "-t",
                helper.tmpstorage / "foo",
                "-T",
                helper.tmpstorage / "bar",
            ]
        )
    assert "Cannot combine" in cm.value.stderr


@pytest.mark.e2e
def test_e2e_move_no_target_directory_extra_operand(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            [
                "storage",
                "mv",
                "-T",
                helper.tmpstorage / "foo",
                helper.tmpstorage / "bar",
                helper.tmpstorage / "baz",
            ]
        )
    assert "Extra operand after " in cm.value.stderr


@pytest.mark.e2e
@pytest.mark.skip(
    reason=(
        "ERROR: AssertionError: "
        "Paths don't match between test and integration environments"
    )
)
def test_e2e_glob(tmp_path: Path, helper: Helper) -> None:
    # Create files and directories and copy them to storage
    helper.mkdir("")
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "subfolder").mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    (folder / "baz").write_bytes(b"baz")
    helper.run_cli(
        [
            "storage",
            "cp",
            "-r",
            tmp_path.as_uri() + "/f*",
            helper.tmpstorage / "folder",
        ]
    )
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage / "folder"])
    assert sorted(captured.out.splitlines()) == ["bar", "baz", "foo", "subfolder"]

    # Move files with pattern
    helper.run_cli(
        [
            "storage",
            "mv",
            helper.tmpstorage / "folder/[bf]*",
            helper.tmpstorage / "folder/subfolder",
        ]
    )
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage / "folder/subfolder"])
    assert sorted(captured.out.splitlines()) == ["bar", "baz", "foo"]

    # Download files with pattern
    download = tmp_path / "download"
    download.mkdir()
    helper.run_cli(["storage", "cp", helper.tmpstorage / "**/b*", str(download)])
    assert sorted(download.iterdir()) == [download / "bar", download / "baz"]

    # Remove files with pattern
    helper.run_cli(["storage", "rm", helper.tmpstorage / "**/b*"])
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage / "folder/subfolder"])
    assert sorted(captured.out.splitlines()) == ["foo"]

    # Test subcommand "glob"
    captured = helper.run_cli(["storage", "glob", helper.tmpstorage / "**"])
    prefix = f"storage://{helper.cluster_uri_base}/{helper.tmpstorage.path}"
    assert sorted(captured.out.splitlines()) == [
        prefix.rstrip("/"),
        prefix + "/folder",
        prefix + "/folder/subfolder",
        prefix + "/folder/subfolder/foo",
    ]


@pytest.mark.e2e
def test_e2e_no_glob(tmp_path: Path, helper: Helper) -> None:
    # Create files and directories and copy them to storage
    helper.mkdir("")
    dir = tmp_path / "[d]"
    dir.mkdir()
    (dir / "f").write_bytes(b"f")
    (dir / "[df]").write_bytes(b"[df]")
    helper.run_cli(
        [
            "storage",
            "cp",
            "-r",
            "--no-glob",
            tmp_path.as_uri() + "/[d]",
            helper.tmpstorage / "d",
        ]
    )

    # Move files with literal path
    helper.run_cli(
        ["storage", "mv", "--no-glob", helper.tmpstorage / "d/[df]", helper.tmpstorage]
    )
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage])
    assert sorted(captured.out.splitlines()) == ["[df]", "d"]

    # Download files with literal path
    download = tmp_path / "download"
    download.mkdir()
    helper.run_cli(
        ["storage", "cp", "--no-glob", helper.tmpstorage / "[df]", str(download)]
    )
    assert sorted(download.iterdir()) == [download / "[df]"]

    # Remove files with literal path
    helper.run_cli(["storage", "rm", "--no-glob", helper.tmpstorage / "[df]"])
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage])
    assert sorted(captured.out.splitlines()) == ["d"]


@pytest.mark.e2e
def test_e2e_cp_filter(tmp_path: Path, helper: Helper) -> None:
    # Create files and directories and copy them to storage
    helper.mkdir("")
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "subfolder").mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    (folder / "baz").write_bytes(b"baz")

    helper.run_cli(
        [
            "storage",
            "cp",
            "-r",
            "--exclude",
            "*",
            "--include",
            "b??",
            "--exclude",
            "*z",
            tmp_path.as_uri() + "/folder",
            helper.tmpstorage / "filtered",
        ]
    )
    captured = helper.run_cli(["storage", "ls", helper.tmpstorage / "filtered"])
    assert captured.out.splitlines() == ["bar"]

    # Copy all files to storage
    helper.run_cli(
        [
            "storage",
            "cp",
            "-r",
            tmp_path.as_uri() + "/folder",
            helper.tmpstorage / "folder",
        ]
    )

    # Copy filtered files from storage
    helper.run_cli(
        [
            "storage",
            "cp",
            "-r",
            "--exclude",
            "*",
            "--include",
            "b??",
            "--exclude",
            "*z",
            helper.tmpstorage / "folder",
            tmp_path.as_uri() + "/filtered",
        ]
    )
    assert os.listdir(tmp_path / "filtered") == ["bar"]


@pytest.mark.e2e
def test_e2e_ls_skip_hidden(tmp_path: Path, helper: Helper) -> None:
    # Create files and directories and copy them to storage
    helper.mkdir("")
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / ".bar").write_bytes(b"bar")

    helper.run_cli(
        ["storage", "cp", "-r", tmp_path.as_uri() + "/folder", helper.tmpstorage]
    )

    captured = helper.run_cli(["storage", "ls", helper.tmpstorage / "folder"])
    assert captured.out.splitlines() == ["foo"]


@pytest.mark.e2e
def test_e2e_ls_show_hidden(tmp_path: Path, helper: Helper) -> None:
    # Create files and directories and copy them to storage
    helper.mkdir("")
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / ".bar").write_bytes(b"bar")

    helper.run_cli(
        ["storage", "cp", "-r", tmp_path.as_uri() + "/folder", helper.tmpstorage]
    )

    captured = helper.run_cli(["storage", "ls", "--all", helper.tmpstorage / "folder"])
    assert captured.out.splitlines() == [".bar", "foo"]


@pytest.mark.e2e
def test_tree(helper: Helper, data: _Data, tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    subfolder = folder / "folder"
    subfolder.mkdir()
    (subfolder / "baz").write_bytes(b"baz")

    helper.run_cli(["storage", "cp", "-r", folder.as_uri(), helper.tmpstorage])

    capture = helper.run_cli(["storage", "tree", helper.tmpstorage])
    assert capture.err == ""

    expected = textwrap.dedent(
        f"""\
         {helper.tmpstorage}
         ├── bar
         ├── folder
         │   └── baz
         └── foo

         1 directories, 3 files"""
    )
    if sys.platform == "win32":
        trans = str.maketrans(
            "".join(TreeFormatter.ANSI_DELIMS), "".join(TreeFormatter.SIMPLE_DELIMS)
        )
        expected = expected.translate(trans)
    assert capture.out == expected


@pytest.mark.skipif(
    sys.platform == "win32", reason="Autocompletion is not supported on Windows"
)
@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: AssertionError: 'storage:' not in completion results")
def test_storage_autocomplete_remote(helper: Helper, tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    subfolder = folder / "folder"
    subfolder.mkdir()
    (subfolder / "baz").write_bytes(b"baz")

    helper.run_cli(["storage", "cp", "-r", folder.as_uri(), helper.tmpstorage])

    out = helper.autocomplete(["storage", "ls", "st"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "storage:" in completion_keys

    out = helper.autocomplete(["storage", "cp", f"{helper.tmpstorage}/"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "folder/" in completion_keys
    assert "foo" in completion_keys
    assert "bar" in completion_keys

    out = helper.autocomplete(["storage", "cp", f"{helper.tmpstorage}/fo"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "folder/" in completion_keys
    assert "foo" in completion_keys
    assert "bar" not in completion_keys

    out = helper.autocomplete(["storage", "cp", f"{helper.tmpstorage}/folder/"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "baz" in completion_keys


@pytest.mark.skipif(
    sys.platform == "win32", reason="Autocompletion is not supported on Windows"
)
@pytest.mark.e2e
@pytest.mark.skip(reason="ERROR: AssertionError: 'file:' not in completion results")
def test_storage_autocomplete_local(helper: Helper, tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "foo").write_bytes(b"foo")
    (folder / "bar").write_bytes(b"bar")
    subfolder = folder / "folder"
    subfolder.mkdir()
    (subfolder / "baz").write_bytes(b"baz")

    out = helper.autocomplete(["storage", "cp", "fi"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "file:" in completion_keys

    out = helper.autocomplete(["storage", "cp", f"{folder.as_uri()}/"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "folder/" in completion_keys
    assert "foo" in completion_keys
    assert "bar" in completion_keys

    out = helper.autocomplete(["storage", "cp", f"{folder.as_uri()}/fo"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "folder/" in completion_keys
    assert "foo" in completion_keys
    assert "bar" not in completion_keys

    out = helper.autocomplete(["storage", "cp", f"{folder.as_uri()}/folder/"])
    completions = helper.parse_completions(out)
    completion_keys = [key for _, key, _, _ in completions]
    assert "baz" in completion_keys
