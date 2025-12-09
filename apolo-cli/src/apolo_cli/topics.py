from collections.abc import Callable
from typing import Any, cast

import click
from click.utils import make_default_short_help
from rich.markdown import Markdown

from .root import Root


class Command(click.Command):
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if self.help is None:
            return
        formatter.write_paragraph()
        root = cast(Root, ctx.obj)
        with root.pager():
            root.print(Markdown(self.help, inline_code_lexer="bash"))

    def get_short_help_str(self, limit: int = 45) -> str:
        if self.help is None:
            return ""
        head, *tail = self.help.split("\n", 1)
        return make_default_short_help(head.strip(" *_.#"))


def command(
    name: str | None = None, cls: type[Command] = Command, **kwargs: Any
) -> Command:
    return click.command(name=name, cls=cls, **kwargs)  # type: ignore


class Group(click.Group):
    def command(  # type: ignore
        self, *args: Any, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Command]:
        def decorator(f: Callable[..., Any]) -> Command:
            cmd = command(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd

        return decorator

    def group(  # type: ignore
        self, *args: Any, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], "Group"]:
        def decorator(f: Callable[..., Any]) -> Group:
            cmd = group(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd

        return decorator


def group(name: str | None = None, **kwargs: Any) -> Group:
    kwargs.setdefault("cls", Group)
    return click.group(name=name, **kwargs)  # type: ignore


@group()
def topics() -> None:
    """Help topics."""


@topics.command()
async def ps_format() -> None:
    """\
    Format for column specification
    ================================

    This format is a sequence of column specifications separated
    by commas or spaces: `{id}, {status}, {when}`.

    A column specification contains a mandatory column ID and optional properties
    that indicate alignment, minimum and maximum column width,
    and the column's title: `{id;align=center;min=10;max=30;width=20;TITLE}`

    Here, **id** is the column's ID, **align**, **min**, **max**, and **width**
    are optional properties, and **TITLE** is the column's title.

    Alternatively, you can specify only the column's ID without additional properties
    and omit the curly brackets by using one of the following formats:

    * `id, status, when`
    * `id status when`

    Available properties:

    * **align**: Column alignment. Accepted values: left, right, center.
    * **min**: Minimum column width.
    * **max**: Maximum column width.
    * **width**: Default column width.

    If all of these properties are skipped, the default value is used for
    the specified column ID.

    Multiple values can be output on different lines in one cell if several
    column IDs are specified separated with "/":

    * `id/name {status/when;align=center;min=10;max=30;width=20;TITLE}`

    The system recognizes the following columns:

    * **id** (ID): Job id.
    * **name** (NAME): Job name.
    * **tags** (TAGS): Job tags.
    * **status** (STATUS): Job status.
    * **when** (WHEN): Time of the last update of job information.
    * **created** (CREATED): Job creation time.
    * **started** (STARTED): Job starting time.
    * **finished** (FINISHED): Job finishing time.
    * **image** (IMAGE): Job image.
    * **owner** (OWNER): Job owner.
    * **cluster_name** (CLUSTER): Job cluster name.
    * **org_name** (ORG): Job org name.
    * **description** (DESCRIPTION): Job description.
    * **command** (COMMAND): The command a job executes.
    * **life_span** (LIFE-SPAN): Job lifespan.
    * **workdir** (WORKDIR): Default working directory inside a job.
    * **preset** (PRESET): Resource configuration used for a job.

    These additional columns are only recognized in the `apolo top` command:

    * **cpu** (CPU): Number of used CPUs.
    * **memory** (MEMORY (MB)): Amount of used memory, in MB.
    * **gpu** (GPU (%)): Used GPUs, per cent.
    * **gpu_memory** (GPU_MEMORY (MB)): Amount of used GPU memory, in MB.

    By default, all columns are left-aligned and have no minimum and default widths.

    The column ID is case-insensitive, so it can be changed to any unambiguous shortened
    version of the full name.  For example, `{CLUSTER:max=20}` is a good column
    specificaton, while `{C:max=20}` is not, as it can be expanded both into
    `cluster_name` and `command` column IDs.

    """


@topics.command()
async def top_format() -> None:
    pass


top_format.help = ps_format.help


@topics.command()
async def user_config() -> None:
    """\
    User configuration files
    ========================

    The Apolo client supports custom configuration files that provide default values
    for particular command options, user-defined command aliases, etc.

    There are two types of configuration files that a project may have: **global** and
    **local**. Both of these are completely optional.

    The global file is located in the standard apolo config path. Apolo CLI uses the
    `~/.apolo` folder by default, so the full path for the global config file is
    `~/.apolo/user.toml`.

    The local config file is named `.apolo.toml` and the CLI searches for this file
    starting from the current folder up to the root directory.

    Local and global configurations that were found by the CLI are then merged.
    If a parameter is present both in the global and local versions, the local parameter
    take precedence.

    These configuration files must be written in the TOML format (which is a stricter
    version of the well-known INI format). See `https://en.wikipedia.org/wiki/TOML` and
    `https://github.com/toml-lang/toml#toml` for this format's specification details.

    Supported configuration sections and parameters:

    `[alias]` section
    -----------------

    A section for describing user-provided aliases.

    See `apolo help aliases` for details about avaiable section contents.

    `[job]` section
    ---------------

    A section for `apolo job` command group settings.

    **`cluster-name`**

    The name of active cluster which overrides the global cluster name set by
    `apolo config switch-cluster`.  Can only be specified in the **local**
    configuration file.

    **`org-name`**

    The name of active organization which overrides the global organization
    name set by `apolo config switch-org`.  Can only be specified in
    the **local** configuration file.

    **`ps-format`**

    Default value for the `apolo ps --format=XXX` option.

    See `apolo help ps-format` for information about the value's specification.

    **`top-format`**

    Default value for the `apolo top --format=XXX` option.

    See `apolo help top-format` for information about the value's specification.

    **`life-span`**

    Default job runtime limit for the `apolo run --life-span=XXX` option.

    The value is a string of the following format: `1d2h3m4s` (this example will set the
    limit to 1 day, 2 hours, 3 minutes, and 4 seconds). Some parts of the value can be
    omitted, for example: `1d6h`, `30m`, `4h30s`. No spaces are allowed between the
    parts of the value.

    `[storage]` section
    -------------------

    A section for `apolo storage` command group settings.

    **`cp-exclude`**

    Default value for the `apolo cp --exclude=XXX` and `apolo cp --include=YYY` options.

    The value is a list of shell wildcard patterns. Files and folders that match these
    patterns will be excluded from processing.

    The pattern can contain `*` and `?`. For example, `["*.jpg"]` will exclude all
    files with the `.jpg` extension.

    Exclamation mark `!` is used to negate the pattern. For example, `["*.jpg",
    "!main.jpg"]` will exclude all `.jpg` files except for `main.jpg`.

    **`cp-exclude-from-files`**

    Default value for the `apolo cp --exclude-from-files=XXX` option.

    The value is a list of filenames that contain patterns for excluding files
    and directories from being uploaded. For every processed folder,
    patterns from the matched exclusion files (e.g., ".apoloignore")
    are read and recursively applied to the directory content.

    Default is `[".apoloignore"]`.

    The format of these files is the same as the format of `.gitignore` files:
    every line contains a pattern, and the exclamation mark `!` is used to negate
    the pattern. Empty lines and lines which start with `#` are ignored.

    `[disk]` section
    ----------------

    A section for `apolo disk` command group settings.

    **`life-span`**

    Default disk lifetime limit for the `apolo disk create --life-span=XXX` option.

    The value is a string of the following format: `1d2h3m4s` (this example will set the
    limit to 1 day, 2 hours, 3 minutes, and 4 seconds). Some parts of the value can be
    omitted, for example: `1d6h`, `30m`, `4h30s`. No spaces are allowed between the
    parts of the value.

    *Example:*
    ```
      # jobs section
      [job]
      ps-format = "{id;max=30}, {status;max=10}"
      life-span = "1d6h"

      # storage section
      [storage]
      cp-exclude = ["*.jpg", "!main.jpg"]
      cp-exclude-from-files = [".apoloignore", ".gitignore"]

      # jobs section
      [disk]
      life-span = "7d"
    ```

    """


@topics.command()
async def aliases() -> None:
    """\
    Custom command aliases
    ======================

    Aliases provide a way to abbreviate system commands and
    add default arguments to commonly used commands.

    Aliases are described in user-config files
    (see `apolo help user-config` for details).

    `~/.apolo/user.toml` is used for **global** aliases, and
    `.apolo.toml` can be used for saving **project-specific** aliases.
    Project aliases overrides global ones if the same alias
    name exists in both configuration files.

    There are two types of aliases: **internal** and **external**.
    **Internal** aliases execute built-in apolo commands, and  **
    external** aliases execute **system OS** commands.

    Internal aliases
    ----------------

    Internal aliases are used for running existing apolo CLI commands under
    a different name and with optional overriden defaults (passed predefined
    command line options and arguments).

    For example, the following alias definition creates a `apolo lsl` command
    that executes `apolo storage ls -hl` to list the storage's content
    using a long output mode with human-readable file sizes.

    ```
      [alias.lsl]
      cmd = "ls -l --human-readable"
      help = "List directory contents in a long mode.
    ```

    Available configuration arguments:

    * `[alias.lsl]`: Defines a subgroup for a named alias,
                       `lsl` in this case.
    * `cmd`: The command to execute with provided overridden options,
      this key is **mandatory**.
      The `cmd` key in the alias section implies **internal alias** mode.
    * `help`: Help string displayed by the `apolo lsl --help`
      command (optional).

    Internal aliases accept additional command line options and agruments,
    and pass them to the underlying command as is.

    For example, `apolo lsl storage:directory` works as
    `apolo ls -l --human-readable storage:directory`


    External aliases
    ----------------

    External aliases spawn a subprocess with passing default options and
    arguments. All user-provided arguments are passed to the underlying
    program as well.

    For example, the following configuration defines `apolo du` command as
    an alias for the system `du --human-readable` command with an additional
    ability to specify a directory for analysis.

    ```
      [alias.du]
      exec = "du"
      args = "[FILE]..."
      options = [
        "-h, --human-readable   print sizes in powers of 1024 (e.g., 1024M)",
        "-d, --max-depth=N  max recursion level for subdirectories lookup",
      ]
      help = '''
        Summarize disk usage of the set of files,
        recursively for directories.
      '''
    ```

    Available configuration arguments:

    * `[alias.du]`: Defines a subgroup for a named alias,
      `du` in this case.
    * `exec`: External command to execute, this key is **mandatory**.
      The `exec` key in the alias section implies **external alias** mode.
    * `args`: Positional argumentss accepted by the alias,
      the format is described below (optional).
    * `options`: Options and flags accepted by the alias,
      the format is described below (optional).
    * `help`: Help string displayed by `apolo du --help`
      command (optional),

    **args** is a string with a sequence of arguments, e.g. `DIR SRC... [DST]`

    If an argument is enclosed in square brackets, it's **optional** (`[FILE]`).
    If an argument ends with an ellipsis, this argument accepts
    multiple values (`SRC...`)

    **options** is a list of strings specifying various options.

    Each string describes a single option. The option definitions should be separated
    from the option descriptions (help) by two or more spaces.

    An option definition can contain:
    * Short name (`-h`)
    * Long name (`--human-readable`)
    * Indication of the required value type (`-d, --max-depth=N`).
      If the required value indicator (`=NAME`) is absent,
      the option will be considered a boolean flag.

    **exec** defines an external system command to execute.

    The command is spawned in a subprocess. Apolo CLI waits for the subprocess
    to be finished, and then returns the exit code to the outer caller.

    The parameter may specify an executable file along with some options.
    For example, `exec = "du --human-readable"` enforces human-readable mode
    for the `du` command.

    `exec` can be used in **simplified** and **pattern** mode.

    Pattern mode
    ------------

    In **pattern mode**, the system command is used along with **substitutions**.
    For example, `exec = "du {human_readable} {max_depth} {file}"`.
    Substitution is enclosed in curly brackets and represents a variable name to expand,
    e.g. `{file}`.

    It's expanded with an option or positional argument specified
    by `args` or `options`.  The substitution name is automatically lowercased,
    and dashes (`-`) are replaced with underscores (`_`).
    For example, `args = "ARG-NAME"` matches to `{arg_name}`.

    If a substitution corresponds to an optional parameter not provided
    by the user, this substitution will be expanded to an empty string.

    If a substitution corresponds to multiple values, all of them are used.
    For example, `apolo du folder1 folder2` expands to `du folder1 folder2` since
    the `[FILE]...` argument matches to `folder1 folder2` values.

    Options are expanded using the longest form if provided,
    e.g. `apolo du -h` is expanded to `du --human-readable`.

    Options with values are expanded as well,
    e.g. `apolo du -d 1` is expanded to `du --max-depth 1`.
    `apolo du --max-depth 1` matches to the same command.

    Simplified mode
    ---------------

    In **simplified mode**, the `exec` value does not contain any **substitutions**.
    In this case, all parsed `options` and `args` are appended
    to the executed command automatically if provided.
    For example, `exec = "du"` is expanded to
    `exec = "du {human_readable} {max_depth} {file}"`

    """


@topics.command()
async def secrets() -> None:
    """\
    Using secrets
    =============

    A *secret* is a piece of encrypted named data stored in the Apolo Platform Cluster.

    Users can create secrets, list available secret names, and delete unused secrets.
    However, reading the secret's data back is impossible. Instead of plain reading,
    secrets can be accessed from a running job as an environment variable or a mounted
    file.

    Secrets are isolated and user-specific - a secret that belongs to user A cannot be
    accessed by user B.

    Managing secrets
    ----------------

    Use the `apolo secret` command group to manage secrets.

    `apolo secret ls` prints all available secret names.

    `apolo secret add key value` creates a secret named *key* with encrypted data
    *value*.

    To store a file's content as a secret, use the
    `apolo secret add KEY_NAME @path/to/file.txt` notation.

    `apolo secret rm key` removes the secret named *key*.

    Internally, the Apolo Platform uses the Kubernetes Cluster secrets subsystem to
    store secrets.

    Using secrets
    -------------

    As said above, you can't read a secret directly, but instead should pass it to a
    running job as an environment variable or a mounted file.

    To pass a secret named *key* as an environment variable, use `secret:key` as a value
    for `--env`.  For example, `apolo run --env VAR=secret:key ...`.

    To mount a secret as a file, use the `secret:` scheme of `--volume`.
    For example, `apolo run --volume secret:key:/mount/path/file.txt`.

    """


@topics.command()
async def sharing() -> None:
    """\
    Using the sharing functionality
    ===============================

    Understanding permissions
    -------------------------

    The Apolo platform supports five levels of access:
    * deny - No access
    * list - Permits listing entities, but not looking at their details
    * read - Read-only access to an entity
    * write - Read-write access to an entity (including deletion)
    * manage - Allows modification of an entity's permissions

    Please note that permissions are inclusive: *write* permission implies reading,
    and *manage* includes reading and writing, and so on.

    Permissions can be granted via `apolo acl grant` or `apolo share` and
    revoked via `apolo acl revoke`:
    ```
    apolo acl grant job:job-0a6d3f81-b5d2-45db-95e3-548cc1fac81a bob
    apolo acl revoke job:job-0a6d3f81-b5d2-45db-95e3-548cc1fac81a bob
    ```

    You can check entities owned by you and shared with you by running
    `apolo acl list`. This will show all entity URIs and their access levels.
    If you want to focus on a subset of entities, you can filter them with `-s`.
    For instance, `apolo acl list -s job` will only show you jobs you have access to.

    If the `apolo acl list` output contains a URI such as `secret:` or `storage:`,
    it means you have corresponding permissions for all entities of that type.

    Running `apolo acl list --shared` will show you entities shared by you
    along with users/roles you shared them with.

    Roles
    -----

    The Apolo platform supports role-based access control. Role is a packed set of
    permissions to multiple entities which can be shared together. There's several
    default roles in each cluster, and users may additionally create their own custom
    roles.

    Default roles are:
    * {cluster}/manager
    * {cluster}/admin
    * {cluster}/users/{username} - such roles are created for every cluster user and
        always contain a whole set of user's permissions.

    If you want to create a new role, run
    `apolo acl add-role {username}/roles/{rolename}`

    This will create a role "rolename" with an empty permission set. Then you may share
    resources with the new role via `apolo acl grant`:

    ```
    apolo acl grant image:IMAGE_NAME {username}/roles/{rolename}
    apolo acl grant job:JOB_NAME {username}/roles/{rolename}
    apolo acl grant job:ANOTHER_JOB_NAME {username}/roles/{rolename}
    apolo acl grant storage:/folder_name {username}/roles/{rolename}
    ```

    When ready, grant this permission set to another user (`bob` in this case):

    ```
    apolo acl grant role://{username}/roles/{rolename} bob
    ```

    From now on, `bob` will have access to all entities listed under
    the `{username}/roles/{rolename}` role. The list can be viewed by
    `apolo acl list -u {username}/roles/{rolename}`.

    If needed, a role can be revoked:
    `apolo acl revoke role://{username}/roles/{rolename} bob`

    Roles can be deleted by running `apolo acl remove-role {username}/roles/{rolename}`.

    """
