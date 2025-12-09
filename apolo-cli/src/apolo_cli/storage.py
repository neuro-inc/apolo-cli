import asyncio
import dataclasses
import glob as globmodule  # avoid conflict with subcommand "glob"
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import click
from rich.text import Text
from yarl import URL

from apolo_sdk import (
    Client,
    FileFilter,
    FileStatusType,
    IllegalArgumentError,
    ResourceNotFound,
)

from .click_types import PlatformURIType
from .const import EX_OSFILE
from .formatters.storage import (
    BaseFilesFormatter,
    DeleteProgress,
    DiskUsageFormatter,
    FilesSorter,
    LongFilesFormatter,
    SimpleFilesFormatter,
    Tree,
    TreeFormatter,
    VerticalColumnsFilesFormatter,
    create_storage_progress,
    get_painter,
)
from .root import Root
from .utils import Option, argument, command, group, option, parse_file_resource

APOLOIGNORE_FILENAME = ".apoloignore"
NEUROIGNORE_FILENAME = ".neuroignore"

log = logging.getLogger(__name__)


@group()
def storage() -> None:
    """
    Storage operations.
    """


@command()
@argument(
    "paths",
    nargs=-1,
    required=True,
    type=PlatformURIType(allowed_schemes=["storage"]),
)
@option(
    "--recursive",
    "-r",
    is_flag=True,
    help="remove directories and their contents recursively",
)
@option(
    "--glob/--no-glob",
    is_flag=True,
    default=True,
    show_default=True,
    help="Expand glob patterns in PATHS",
)
@option(
    "-p/-P",
    "--progress/--no-progress",
    is_flag=True,
    default=None,
    help="Show progress, on by default in TTY mode, off otherwise.",
)
async def rm(
    root: Root,
    paths: Sequence[URL],
    recursive: bool,
    glob: bool,
    progress: bool | None,
) -> None:
    """
    Remove files or directories.

    Examples:

    apolo rm storage:foo/bar
    apolo rm storage:/{project}/foo/bar
    apolo rm storage://{cluster}/{project}/foo/bar
    apolo rm --recursive storage:/{project}/foo/
    apolo rm 'storage:foo/**/*.tmp'
    """
    errors = False
    show_progress = root.tty if progress is None else progress

    for uri in await _expand(paths, root, glob):
        try:
            progress_obj = DeleteProgress(root) if show_progress else None
            await root.client.storage.rm(
                uri, recursive=recursive, progress=progress_obj
            )
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot remove {uri}: {error}")
            errors = True
        else:
            if root.verbosity > 0:
                painter = get_painter(root.color)
                uri_text = painter.paint(str(uri), FileStatusType.FILE)
                root.print(Text.assemble(f"removed ", uri_text))
    if errors:
        sys.exit(EX_OSFILE)


@command()
@argument(
    "paths",
    nargs=-1,
    type=PlatformURIType(allowed_schemes=["storage"], complete_file=False),
)
@option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="do not ignore entries starting with .",
)
@option(
    "-d",
    "--directory",
    is_flag=True,
    help="list directories themselves, not their contents.",
)
@option(
    "--human-readable",
    "-h",
    is_flag=True,
    help="with -l print human readable sizes (e.g., 2K, 540M).",
)
@option("-l", "format_long", is_flag=True, help="use a long listing format.")
@option(
    "--sort",
    type=click.Choice(["name", "size", "time"]),
    default="name",
    help="sort by given field, default is name.",
)
async def ls(
    root: Root,
    paths: Sequence[URL],
    human_readable: bool,
    format_long: bool,
    sort: str,
    directory: bool,
    show_all: bool,
) -> None:
    """
    List directory contents.

    By default PATH is equal project's dir (storage:)
    """
    if not paths:
        paths = [URL("storage:")]
    errors = False
    for uri in paths:
        try:
            if directory:
                files = [await root.client.storage.stat(uri)]
            else:
                if root.verbosity > 0:
                    painter = get_painter(root.color)
                    uri_text = painter.paint(str(uri), FileStatusType.DIRECTORY)
                    root.print(Text.assemble("List of ", uri_text, ":"))

                async with root.client.storage.list(uri) as it:
                    files = [file async for file in it]
                files.sort(key=FilesSorter(sort).key())
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot access {uri}: {error}")
            errors = True
        else:
            if format_long:
                formatter: BaseFilesFormatter = LongFilesFormatter(
                    human_readable=human_readable, color=root.color
                )
            else:
                if root.tty and not root.quiet:
                    formatter = VerticalColumnsFilesFormatter(
                        width=root.terminal_size[0], color=root.color
                    )
                else:
                    formatter = SimpleFilesFormatter(False)

            if not show_all:
                files = [item for item in files if not item.name.startswith(".")]
            with root.pager():
                root.print(formatter(files))

    if errors:
        sys.exit(EX_OSFILE)


@command()
@argument(
    "patterns",
    nargs=-1,
    required=False,
    type=PlatformURIType(allowed_schemes=["storage"]),
)
async def glob(root: Root, patterns: Sequence[URL]) -> None:
    """
    List resources that match PATTERNS.
    """
    for uri in patterns:
        if root.verbosity > 0:
            painter = get_painter(root.color)
            uri_text = painter.paint(str(uri), FileStatusType.FILE)
            root.print(Text.assemble("Using pattern ", uri_text, ":"))
        async with root.client.storage.glob(uri) as it:
            async for file in it:
                root.print(file)


@command()
@argument(
    "path",
    required=False,
    type=PlatformURIType(allowed_schemes=["storage"], complete_file=False),
)
async def df(root: Root, path: URL | None) -> None:
    """
    Show current storage usage.

    If PATH is specified, show storage usage of which path is a part.
    """
    usage = await root.client.storage.disk_usage(uri=path)
    root.print(DiskUsageFormatter()(usage))


class FileFilterParserOption(click.parser.Option):
    def process(self, value: str, state: click.parser.ParsingState) -> None:
        assert self.action == "append"
        state.opts.setdefault(self.dest, []).append((self.const, value))  # type: ignore
        state.order.append(self.obj)


class FileFilterOption(Option):
    def __init__(self, *args: Any, is_exclude: bool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._is_exclude = is_exclude

    def add_to_parser(self, parser: click.parser.OptionParser, ctx: Any) -> None:
        option = FileFilterParserOption(
            opts=self.opts,
            dest=self.name,
            action="append",
            nargs=self.nargs,
            const=self._is_exclude,
            obj=self,
        )
        parser._opt_prefixes.update(option.prefixes)
        for opt in option._short_opts:
            parser._short_opt[opt] = option
        for opt in option._long_opts:
            parser._long_opt[opt] = option


def filter_option(
    optname: str, varname: str, is_exclude: bool, help: str
) -> Callable[[Any], Any]:
    return option(
        optname,
        varname,
        multiple=True,
        cls=FileFilterOption,
        is_exclude=is_exclude,
        type=click.UNPROCESSED,
        help=help,
        secure=True,
    )


@command()
@argument(
    "sources",
    nargs=-1,
    required=False,
    type=PlatformURIType(allowed_schemes=["storage", "file"]),
)
@argument(
    "destination",
    required=False,
    type=PlatformURIType(allowed_schemes=["storage", "file"]),
)
@option("-r", "--recursive", is_flag=True, help="Recursive copy, off by default")
@option(
    "--glob/--no-glob",
    is_flag=True,
    default=True,
    show_default=True,
    help="Expand glob patterns in SOURCES with explicit scheme.",
)
@option(
    "-t",
    "--target-directory",
    metavar="DIRECTORY",
    default=None,
    type=PlatformURIType(allowed_schemes=["storage", "file"], complete_file=False),
    help="Copy all SOURCES into DIRECTORY.",
)
@option(
    "-T",
    "--no-target-directory",
    is_flag=True,
    help="Treat DESTINATION as a normal file.",
)
@option(
    "-u",
    "--update",
    is_flag=True,
    help="Copy only when the SOURCE file is newer than the destination file "
    "or when the destination file is missing.",
)
@option(
    "--continue",
    "continue_",
    is_flag=True,
    help="Continue copying partially-copied files.",
)
@filter_option(
    "--exclude",
    "filters",
    is_exclude=True,
    help=("Exclude files and directories that match the specified pattern."),
)
@filter_option(
    "--include",
    "filters",
    is_exclude=False,
    help=("Don't exclude files and directories that match the specified pattern."),
)
@option(
    "--exclude-from-files",
    metavar="FILES",
    help=(
        "A list of file names that contain patterns for exclusion files "
        "and directories. Used only for uploading. "
        "The default can be changed using the storage.cp-exclude-from-files "
        'configuration variable documented in "apolo help user-config"'
    ),
)
@option(
    "-p/-P",
    "--progress/--no-progress",
    is_flag=True,
    default=True,
    help="Show progress, on by default in TTY mode, off otherwise.",
)
async def cp(
    root: Root,
    sources: Sequence[URL],
    destination: URL | None,
    recursive: bool,
    glob: bool,
    target_directory: URL | None,
    no_target_directory: bool,
    update: bool,
    continue_: bool,
    filters: tuple[tuple[bool, str], ...] | None,
    exclude_from_files: str,
    progress: bool,
) -> None:
    """
    Copy files and directories.

    Either SOURCES or DESTINATION should have storage:// scheme.
    If scheme is omitted, file:// scheme is assumed.

    Use /dev/stdin and /dev/stdout file names to copy a file from terminal
    and print the content of file on the storage to console.

    Any number of --exclude and --include options can be passed.  The
    filters that appear later in the command take precedence over filters
    that appear earlier in the command.  If neither --exclude nor
    --include options are specified the default can be changed using the
    storage.cp-exclude configuration variable documented in
    "apolo help user-config".

    Examples:

    # copy local files into remote storage root
    apolo cp foo.txt bar/baz.dat storage:
    apolo cp foo.txt bar/baz.dat -t storage:

    # copy local directory `foo` into existing remote directory `bar`
    apolo cp -r foo -t storage:bar

    # copy the content of local directory `foo` into existing remote
    # directory `bar`
    apolo cp -r -T storage:foo storage:bar

    # download remote file `foo.txt` into local file `/tmp/foo.txt` with
    # explicit file:// scheme set
    apolo cp storage:foo.txt file:///tmp/foo.txt
    apolo cp -T storage:foo.txt file:///tmp/foo.txt
    apolo cp storage:foo.txt file:///tmp
    apolo cp storage:foo.txt -t file:///tmp

    # download other project's remote file into the current directory
    apolo cp storage:/{project}/foo.txt .

    # download only files with extension `.out` into the current directory
    apolo cp storage:results/*.out .
    """
    if target_directory:
        if no_target_directory:
            raise click.UsageError(
                "Cannot combine --target-directory (-t) and --no-target-directory (-T)"
            )
        if destination is None:
            raise click.MissingParameter(
                param_type="argument", param_hint='"SOURCES..."'
            )
        sources = *sources, destination
        destination = None
    else:
        if destination is None:
            raise click.MissingParameter(
                param_type="argument", param_hint='"DESTINATION"'
            )
        if not sources:
            raise click.MissingParameter(
                param_type="argument", param_hint='"SOURCES..."'
            )
        if no_target_directory or not await _is_dir(root, destination):
            target_directory = None
        else:
            target_directory = destination
            destination = None

    ignore_file_names = await calc_ignore_file_names(root.client, exclude_from_files)
    filters = await calc_filters(root.client, filters)
    srcs = await _expand(sources, root, glob, allow_file=True)
    if no_target_directory and len(srcs) > 1:
        raise click.UsageError(f"Extra operand after {str(srcs[1])!r}")

    file_filter = FileFilter()
    for exclude, pattern in filters:
        log.debug("%s %s", "Exclude" if exclude else "Include", pattern)
        file_filter.append(exclude, pattern)

    show_progress = root.tty and progress

    errors = False
    for src in srcs:
        if target_directory:
            destination = target_directory / Path(src.path).name
        assert destination

        progress_obj = create_storage_progress(root, show_progress)
        try:
            with progress_obj.begin(src, destination):
                if src.scheme == "file" and destination.scheme == "storage":
                    if recursive and await _is_dir(root, src):
                        await root.client.storage.upload_dir(
                            src,
                            destination,
                            update=update,
                            continue_=continue_,
                            filter=file_filter.match,
                            ignore_file_names=frozenset(ignore_file_names),
                            progress=progress_obj,
                        )
                    else:
                        await root.client.storage.upload_file(
                            src,
                            destination,
                            update=update,
                            continue_=continue_,
                            progress=progress_obj,
                        )
                elif src.scheme == "storage" and destination.scheme == "file":
                    if recursive and await _is_dir(root, src):
                        await root.client.storage.download_dir(
                            src,
                            destination,
                            update=update,
                            continue_=continue_,
                            filter=file_filter.match,
                            progress=progress_obj,
                        )
                    else:
                        await root.client.storage.download_file(
                            src,
                            destination,
                            update=update,
                            continue_=continue_,
                            progress=progress_obj,
                        )
                else:
                    raise RuntimeError(
                        f"Copy operation of the file with scheme '{src.scheme}'"
                        f" to the file with scheme '{destination.scheme}'"
                        f" is not supported."
                        " Checkout 'apolo-extras data --help',"
                        " maybe it will suite your use-case?"
                    )
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot copy {src} to {destination}: {error}")
            errors = True

    if errors:
        sys.exit(EX_OSFILE)


@command()
@argument(
    "paths",
    nargs=-1,
    required=True,
    type=PlatformURIType(allowed_schemes=["storage"], complete_file=False),
)
@option(
    "-p",
    "--parents",
    is_flag=True,
    help="No error if existing, make parent directories as needed",
)
async def mkdir(root: Root, paths: Sequence[URL], parents: bool) -> None:
    """
    Make directories.
    """
    errors = False
    for uri in paths:
        try:
            await root.client.storage.mkdir(uri, parents=parents, exist_ok=parents)
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot create directory {uri}: {error}")
            errors = True
        else:
            if root.verbosity > 0:

                painter = get_painter(root.color)
                uri_text = painter.paint(str(uri), FileStatusType.DIRECTORY)
                root.print(Text.assemble("created directory ", uri_text))

    if errors:
        sys.exit(EX_OSFILE)


@command()
@argument(
    "sources",
    nargs=-1,
    required=False,
    type=PlatformURIType(allowed_schemes=["storage"]),
)
@argument(
    "destination",
    type=PlatformURIType(allowed_schemes=["storage"]),
    required=False,
)
@option(
    "--glob/--no-glob",
    is_flag=True,
    default=True,
    show_default=True,
    help="Expand glob patterns in SOURCES",
)
@option(
    "-t",
    "--target-directory",
    metavar="DIRECTORY",
    default=None,
    type=PlatformURIType(allowed_schemes=["storage"], complete_file=False),
    help="Copy all SOURCES into DIRECTORY",
)
@option(
    "-T",
    "--no-target-directory",
    is_flag=True,
    help="Treat DESTINATION as a normal file",
)
async def mv(
    root: Root,
    sources: Sequence[URL],
    destination: URL | None,
    glob: bool,
    target_directory: URL | None,
    no_target_directory: bool,
) -> None:
    """
    Move or rename files and directories.

    SOURCE must contain path to the
    file or directory existing on the storage, and DESTINATION must contain
    the full path to the target file or directory.

    Examples:

    # move and rename remote file
    apolo mv storage:foo.txt storage:bar/baz.dat
    apolo mv -T storage:foo.txt storage:bar/baz.dat

    # move remote files into existing remote directory
    apolo mv storage:foo.txt storage:bar/baz.dat storage:dst
    apolo mv storage:foo.txt storage:bar/baz.dat -t storage:dst

    # move the content of remote directory into other existing
    # remote directory
    apolo mv -T storage:foo storage:bar

    # move remote file into other project's directory
    apolo mv storage:foo.txt storage:/{project}/bar.dat

    # move remote file from other project's directory
    apolo mv storage:/{project}/foo.txt storage:bar.dat
    """
    if target_directory:
        if no_target_directory:
            raise click.UsageError(
                "Cannot combine --target-directory (-t) and --no-target-directory (-T)"
            )
        if destination is None:
            raise click.MissingParameter(
                param_type="argument", param_hint='"SOURCES..."'
            )
        sources = *sources, destination
        destination = None
    else:
        if destination is None:
            raise click.MissingParameter(
                param_type="argument", param_hint='"DESTINATION"'
            )
        if not sources:
            raise click.MissingParameter(
                param_type="argument", param_hint='"SOURCES..."'
            )
        if no_target_directory or not await _is_dir(root, destination):
            target_directory = None
        else:
            target_directory = destination
            destination = None

    srcs = await _expand(sources, root, glob)
    if no_target_directory and len(srcs) > 1:
        raise click.UsageError(f"Extra operand after {str(srcs[1])!r}")

    errors = False
    for src in srcs:
        if target_directory:
            destination = target_directory / src.name
        assert destination
        try:
            if root.verbosity > 0:
                painter = get_painter(root.color)
                src_status = await root.client.storage.stat(src)
            await root.client.storage.mv(src, destination)
        except (OSError, ResourceNotFound, IllegalArgumentError) as error:
            log.error(f"cannot move {src} to {destination}: {error}")
            errors = True
        else:
            if root.verbosity > 0:
                src_text = painter.paint(str(src), src_status.type)
                dst_text = painter.paint(str(destination), src_status.type)
                root.print(Text.assemble(src_text, " -> ", dst_text))

    if errors:
        sys.exit(EX_OSFILE)


@command()
@click.argument(
    "path",
    required=False,
    type=PlatformURIType(allowed_schemes=["storage"], complete_file=False),
)
@option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="do not ignore entries starting with .",
)
@option(
    "--human-readable",
    "-h",
    is_flag=True,
    help="Print the size in a more human readable way.",
)
@option(
    "--size",
    "-s",
    is_flag=True,
    help="Print the size in bytes of each file.",
)
@option(
    "--sort",
    type=click.Choice(["name", "size", "time"]),
    default="name",
    help="sort by given field, default is name",
)
async def tree(
    root: Root, path: URL, size: bool, human_readable: bool, sort: str, show_all: bool
) -> None:
    """
    List storage in a tree-like format

    Tree is a recursive directory listing program that produces a depth indented listing
    of files, which is colorized ala dircolors if the LS_COLORS environment variable is
    set and output is to tty.  With no arguments, tree lists the files in the storage:
    directory.  When directory arguments are given, tree lists all the files and/or
    directories found in the given directories each in turn.  Upon completion of listing
    all files/directories found, tree returns the total number of files and/or
    directories listed.

    By default PATH is equal project's dir (storage:)

    """
    if not path:
        path = URL("storage:")

    errors = False
    try:
        tree = await fetch_tree(root.client, path, show_all)
        name = root.client.parse.uri_to_str(
            root.client.parse.normalize_uri(path, short=True)
        )
        tree = dataclasses.replace(
            tree,
            name=name,
        )
    except (OSError, ResourceNotFound) as error:
        log.error(f"cannot fetch tree for {path}: {error}")
        errors = True
    else:
        formatter = TreeFormatter(
            color=root.color, size=size, human_readable=human_readable, sort=sort
        )
        with root.pager():
            root.print(formatter(tree))

    if errors:
        sys.exit(EX_OSFILE)


async def _expand(
    paths: Sequence[str | URL], root: Root, glob: bool, allow_file: bool = False
) -> list[URL]:
    uris = []
    for path in paths:
        if isinstance(path, URL):
            # URL may be in relative form, normalization is required anyway
            path = str(path)
        uri = parse_file_resource(path, root)
        if root.verbosity > 0:
            painter = get_painter(root.color)
            uri_text = painter.paint(str(uri), FileStatusType.FILE)
            root.print(Text.assemble("Expand ", uri_text))
        uri_path = (
            str(root.client.parse.uri_to_path(uri))
            if uri.scheme == "file"
            else uri.path
        )
        if glob and globmodule.has_magic(uri_path):
            if uri.scheme == "storage":
                async with root.client.storage.glob(uri) as it:
                    async for file in it:
                        uris.append(file)
            elif allow_file and path.startswith("file:"):
                for p in globmodule.iglob(uri_path, recursive=True):
                    uris.append(uri.with_path(p))
            else:
                uris.append(uri)
        else:
            uris.append(uri)
    return uris


async def _is_dir(root: Root, uri: URL) -> bool:
    if uri.scheme == "storage":
        try:
            stat = await root.client.storage.stat(uri)
            return stat.is_dir()
        except ResourceNotFound:
            pass
    elif uri.scheme == "file":
        path = root.client.parse.uri_to_path(uri)
        return path.is_dir()
    return False


storage.add_command(cp)
storage.add_command(ls)
storage.add_command(glob)
storage.add_command(rm)
storage.add_command(mkdir)
storage.add_command(mv)
storage.add_command(tree)
storage.add_command(df)


async def calc_filters(
    client: Client, filters: tuple[tuple[bool, str], ...] | None
) -> tuple[tuple[bool, str], ...]:
    ret = []
    config = await client.config.get_user_config()
    section = config.get("storage")
    if section is not None:
        for flt in section.get("cp-exclude", ()):
            if flt.startswith("!"):
                ret.append((False, flt[1:]))
            else:
                ret.append((True, flt))
    if filters is not None:
        ret.extend(filters)
    return tuple(ret)


async def calc_ignore_file_names(
    client: Client, exclude_from_files: str | None
) -> list[str]:
    if exclude_from_files is not None:
        return exclude_from_files.split()
    config = await client.config.get_user_config()
    section = config.get("storage")
    ignore_file_names = [APOLOIGNORE_FILENAME, NEUROIGNORE_FILENAME]
    if section is not None:
        ignore_file_names = section.get("cp-exclude-from-files", ignore_file_names)
    return ignore_file_names


async def fetch_tree(client: Client, uri: URL, show_all: bool) -> Tree:
    loop = asyncio.get_event_loop()
    folders = []
    files = []
    tasks = []
    size = 0
    async with client.storage.list(uri) as it:
        async for item in it:
            if not show_all and item.name.startswith("."):
                continue
            if item.is_dir():
                tasks.append(
                    loop.create_task(fetch_tree(client, uri / item.name, show_all))
                )
            else:
                files.append(item)
                size += item.size
    for task in tasks:
        subtree = await task
        folders.append(subtree)
        size += subtree.size
    return Tree(uri.name, size, folders, files)
