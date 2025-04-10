import asyncio
import functools
import io
import logging
import sys
import warnings
from importlib import import_module
from pathlib import Path
from textwrap import dedent
from typing import Any, List, Optional, Sequence, Tuple, Union, cast

import aiohttp
import click
from aiodocker.exceptions import DockerError
from click.exceptions import Abort as ClickAbort
from click.exceptions import Exit as ClickExit

import apolo_sdk

import apolo_cli

from . import file_logging
from .alias import find_alias
from .click_types import setup_shell_completion
from .const import (
    EX_DATAERR,
    EX_IOERR,
    EX_NOPERM,
    EX_OSFILE,
    EX_PLATFORMERROR,
    EX_PROTOCOL,
    EX_SOFTWARE,
    EX_TIMEOUT,
)
from .log_formatter import ConsoleHandler
from .root import Root
from .utils import (
    Context,
    Group,
    alias,
    argument,
    format_example,
    group,
    option,
    pager_maybe,
    print_help,
)


def setup_stdout(errors: str) -> None:
    if not isinstance(sys.stdout, io.TextIOWrapper):
        return
    sys.stdout.flush()
    sys.stdout.reconfigure(errors=errors)


setup_stdout(errors="replace")


log = logging.getLogger(__name__)


def setup_logging(verbosity: int, color: bool, show_traceback: bool) -> ConsoleHandler:
    root_logger = logging.getLogger()
    console_handler = ConsoleHandler(color=color, show_traceback=show_traceback)
    file_handler = file_logging.get_handler()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)

    if verbosity > 1:
        formatter = logging.Formatter("%(name)s.%(funcName)s: %(message)s")
        console_handler.setFormatter(formatter)

    if verbosity < -1:
        loglevel = logging.CRITICAL
    elif verbosity == -1:
        loglevel = logging.ERROR
    elif verbosity == 0:
        loglevel = logging.WARNING
    elif verbosity == 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    console_handler.setLevel(loglevel)

    return console_handler


class MainGroup(Group):
    skip_init = False  # use it for testing onlt

    def make_context(
        self,
        info_name: Optional[str],
        args: List[str],
        parent: Optional[click.Context] = None,
        **extra: Any,
    ) -> Context:
        ctx = super().make_context(info_name, args, parent, **extra)
        if self.skip_init:
            # Run from test suite
            return ctx

        kwargs = {}
        for param in self.params:
            if param.expose_value:
                val = ctx.params.get(param.name or "")
                if val is not None:
                    kwargs[param.name] = val
                else:
                    kwargs[param.name] = param.get_default(ctx)

        show_traceback = kwargs.get("show_traceback", False)
        tty = all(f.isatty() for f in [sys.stdin, sys.stdout, sys.stderr])
        COLORS = {"yes": True, "no": False, "auto": None}
        real_color: Optional[bool] = COLORS[kwargs["color"]]
        if real_color is None:
            real_color = tty
        ctx.color = real_color
        verbosity = kwargs["verbose"] - kwargs["quiet"]
        handler = setup_logging(
            verbosity=verbosity, color=real_color, show_traceback=show_traceback
        )
        if kwargs["hide_token"] is None:
            hide_token_bool = True
        else:
            if not kwargs["trace"]:
                option = "--hide-token" if kwargs["hide_token"] else "--no-hide-token"
                raise click.UsageError(f"{option} requires --trace")
            hide_token_bool = kwargs["hide_token"]

        config_path = kwargs["config_path"]
        if config_path == apolo_sdk.DEFAULT_CONFIG_PATH:
            # TODO: remove this fallback eventually
            config_path = kwargs["neuromation_config"]
            if config_path == apolo_sdk.DEFAULT_CONFIG_PATH:
                config_path = None

        root = Root(
            verbosity=verbosity,
            color=real_color,
            tty=tty,
            disable_pypi_version_check=kwargs["disable_pypi_version_check"],
            network_timeout=kwargs["network_timeout"],
            config_path=Path(config_path) if config_path is not None else None,
            trace=kwargs["trace"],
            force_trace_all=kwargs["x_trace_all"],
            trace_hide_token=hide_token_bool,
            command_path="",
            command_params=[],
            skip_gmp_stats=kwargs["skip_stats"],
            show_traceback=show_traceback,
            iso_datetime_format=kwargs["iso_datetime_format"],
            ctx=ctx,
        )
        handler.setConsole(root.err_console)
        ctx.obj = root
        ctx.call_on_close(root.close)

        logging.debug(f"Executing command {sys.argv}")
        return ctx

    def resolve_command(
        self, ctx: click.Context, args: List[str]
    ) -> Tuple[str, click.Command, List[str]]:
        cmd_name, *args = args

        # Get the command
        cmd = self.get_command(ctx, cmd_name)

        if cmd is None:
            # find alias
            root = cast(Root, ctx.obj)
            cmd = root.run(find_alias(root, cmd_name))

        # If we don't find the command we want to show an error message
        # to the user that it was not provided.  However, there is
        # something else we should do: if the first argument looks like
        # an option we want to kick off parsing again for arguments to
        # resolve things like --help which now should go to the main
        # place.
        if cmd is None and not ctx.resilient_parsing:
            if cmd_name and not cmd_name[0].isalnum():
                self.parse_args(ctx, ctx.args)
            ctx.fail(f'No such command or alias "{cmd_name}".')

        assert cmd is not None
        return cmd_name, cmd, args

    def _format_group(
        self,
        title: str,
        grp: Sequence[Tuple[str, click.Command]],
        formatter: click.HelpFormatter,
    ) -> None:
        # allow for 3 times the default spacing
        if not grp:
            return

        width = formatter.width
        assert width is not None
        limit = width - 6 - max(len(cmd[0]) for cmd in grp)

        rows = []
        for subcommand, cmd in grp:
            help = cmd.get_short_help_str(limit)
            rows.append((subcommand, help))

        if rows:
            with formatter.section(title):
                formatter.write_dl(rows)

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Extra format methods for multi methods that adds all the commands
        after the options.
        """
        commands: List[Tuple[str, click.Command]] = []
        groups: List[Tuple[str, click.MultiCommand]] = []
        topics: List[Tuple[str, click.Command]] = []
        from .topics import topics as topic_defs

        topics = [
            (name, topic_defs.get_command(ctx, name))
            for name in topic_defs.list_commands(ctx)
        ]

        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            if isinstance(cmd, click.MultiCommand):
                groups.append((subcommand, cmd))
            else:
                commands.append((subcommand, cmd))

        self._format_group("Commands", groups, formatter)
        self._format_group("Command Shortcuts", commands, formatter)
        self._format_group(
            f"Help topics ({ctx.info_name} help <topic>)", topics, formatter
        )

    def format_options(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        self.format_commands(ctx, formatter)
        formatter.write_paragraph()
        formatter.write_text(
            f'Use "{ctx.info_name} help <command>" for more information '
            "about a given command or topic."
        )
        formatter.write_text(
            f'Use "{ctx.info_name} --options" for a list of global command-line '
            "options (applies to all commands)."
        )

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        ret = self.commands.get(cmd_name)
        if ret is not None:
            return ret
        self._pre_load(name=cmd_name)
        return self.commands.get(cmd_name)

    def list_commands(self, ctx: click.Context) -> List[str]:
        self._pre_load()
        return sorted(self.commands)

    def _pre_load(self, name: Optional[str] = None) -> None:
        if name is None:
            for name in CMD_MAP:
                self._pre_load(name)
        else:
            path = CMD_MAP.get(name)
            if path is None:
                return
            # borrowed from EntryPoint.load()
            mod, attr = path.split(":")
            module = import_module(mod)
            attrs = filter(None, (attr or "").split("."))
            cmd = functools.reduce(getattr, attrs, module)
            assert isinstance(cmd, click.Command)
            if cmd.name == name:
                self.add_command(cmd)
            else:
                self.add_command(alias(cmd, name, deprecated=False, help=cmd.help))


CMD_MAP = {
    # groups
    "admin": "apolo_cli.admin:admin",
    "job": "apolo_cli.job:job",
    "storage": "apolo_cli.storage:storage",
    "image": "apolo_cli.image:image",
    "config": "apolo_cli.config:config",
    "completion": "apolo_cli.completion:completion",
    "acl": "apolo_cli.share:acl",
    "blob": "apolo_cli.blob_storage:blob_storage",
    "secret": "apolo_cli.secrets:secret",
    "disk": "apolo_cli.disks:disk",
    "service-account": "apolo_cli.service_accounts:service_account",
    "app": "apolo_cli.apps:app",
    "app-template": "apolo_cli.app_template:app_template",
    # shortcuts
    "run": "apolo_cli.job:run",
    "ps": "apolo_cli.job:ls",
    "status": "apolo_cli.job:status",
    "exec": "apolo_cli.job:exec",
    "port-forward": "apolo_cli.job:port_forward",
    "attach": "apolo_cli.job:attach",
    "logs": "apolo_cli.job:logs",
    "kill": "apolo_cli.job:kill",
    "top": "apolo_cli.job:top",
    "save": "apolo_cli.job:save",
    "login": "apolo_cli.config:login",
    "logout": "apolo_cli.config:logout",
    "cp": "apolo_cli.storage:cp",
    "ls": "apolo_cli.storage:ls",
    "rm": "apolo_cli.storage:rm",
    "mkdir": "apolo_cli.storage:mkdir",
    "mv": "apolo_cli.storage:mv",
    "images": "apolo_cli.image:ls",
    "push": "apolo_cli.image:push",
    "pull": "apolo_cli.image:pull",
    "share": "apolo_cli.share:grant",
}


def print_options(
    ctx: click.Context, param: Union[click.Option, click.Parameter], value: Any
) -> Any:
    if not value or ctx.resilient_parsing:
        return

    formatter = ctx.make_formatter()
    formatter.write_text("Options available for any command.")
    EXAMPLE = dedent(
        """\
        # Show config without colors
        apolo --color=no config show
    """
    )
    format_example(EXAMPLE, formatter)

    opts = []
    for parameter in ctx.command.get_params(ctx):
        rv = parameter.get_help_record(ctx)
        if rv is not None:
            opts.append(rv)

    with formatter.section("Options"):
        formatter.write_dl(opts)

    click.echo(formatter.getvalue())
    ctx.exit()


@group(cls=MainGroup)
@option(
    "-v",
    "--verbose",
    count=True,
    type=int,
    default=0,
    help="Give more output. Option is additive, and can be used up to 2 times.",
)
@option(
    "-q",
    "--quiet",
    count=True,
    type=int,
    default=0,
    help="Give less output. Option is additive, and can be used up to 2 times.",
)
@option(
    "--config-path",
    type=click.Path(dir_okay=True, file_okay=False),
    required=False,
    help="Path to config directory.",
    default=apolo_sdk.DEFAULT_CONFIG_PATH,
    metavar="PATH",
    envvar=apolo_sdk.CONFIG_ENV_NAME,
)
@option(
    "--neuromation-config",
    type=click.Path(dir_okay=True, file_okay=False),
    required=False,
    help="Path to config directory.",
    default=apolo_sdk.DEFAULT_CONFIG_PATH,
    metavar="PATH",
    envvar=apolo_sdk.CONFIG_ENV_NAME,
)
@option(
    "--show-traceback",
    is_flag=True,
    help="Show python traceback on error, useful for debugging the tool.",
)
@option(
    "--color",
    type=click.Choice(["yes", "no", "auto"]),
    default="auto",
    help="Color mode.",
)
@option(
    "--disable-pypi-version-check",
    is_flag=True,
    envvar="NEURO_CLI_DISABLE_PYPI_VERSION_CHECK",
    show_envvar=True,
    help="Don't periodically check PyPI to determine whether a new version of "
    "Apolo Platform CLI is available for download.",
)
@option(
    "--network-timeout", type=float, help="Network read timeout, seconds.", default=60.0
)
@click.version_option(
    version=apolo_cli.__version__, message="Apolo Platform Client %(version)s"
)
@option(
    "--options",
    is_flag=True,
    callback=print_options,
    expose_value=False,
    is_eager=True,
    hidden=True,
    help="Show common options.",
)
@option(
    "--trace",
    is_flag=True,
    help="Trace sent HTTP requests and received replies to stderr.",
)
@option(
    "--x-trace-all",
    hidden=True,
    is_flag=True,
    help="Force distribute tracing in all HTTP requests.",
)
@option(
    "--hide-token/--no-hide-token",
    is_flag=True,
    default=None,
    help=(
        "Prevent user's token sent in HTTP headers from being "
        "printed out to stderr during HTTP tracing. Can be used only "
        "together with option '--trace'. On by default."
    ),
)
@option(
    "--skip-stats/--no-skip-stats",
    is_flag=True,
    default=False,
    help=(
        "Skip sending usage statistics to apolo servers. "
        "Note: the statistics has no sensitive data, e.g. "
        "file, job, image, or user names, executed command lines, "
        "environment variables, etc."
    ),
)
@option(
    "--iso-datetime-format/--no-iso-datetime-format",
    is_flag=True,
    default=False,
    help=("Use ISO 8601 format for printing date and time"),
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: int,
    quiet: bool,
    config_path: str,
    neuromation_config: str,
    show_traceback: bool,
    color: str,
    disable_pypi_version_check: bool,
    network_timeout: float,
    trace: bool,
    x_trace_all: bool,
    hide_token: Optional[bool],
    skip_stats: bool,
    iso_datetime_format: bool,
) -> None:
    #   ▇ ◣
    #   ▇ ◥ ◣
    # ◣ ◥   ▇
    # ▇ ◣   ▇
    # ▇ ◥ ◣ ▇
    # ▇   ◥ ▇    Apolo Platform
    # ▇   ◣ ◥
    # ◥ ◣ ▇      Deep network training,
    #   ◥ ▇      inference and datasets
    #     ◥
    # Parameters parsing is done in MainGroup.make_context()
    pass


@cli.command(init_client=False)
@argument("command", type=click.UNPROCESSED, nargs=-1)
async def help(root: Root, command: Sequence[str]) -> None:
    """Get help on a command."""
    top_ctx = root.ctx

    if len(command) == 1:
        # try to find a topic
        from .topics import topics

        for name, topic in topics.commands.items():
            if name == command[0]:
                # Found a topic
                formatter = root.ctx.make_formatter()
                topic.format_help(top_ctx, formatter)
                pager_maybe(
                    formatter.getvalue().rstrip("\n").splitlines(),
                    root.tty,
                    root.terminal_size,
                )
                return

    not_found = 'No such command "apolo {}"'.format(" ".join(command))

    ctx_stack = [top_ctx]
    try:
        for cmd_name in command:
            current_cmd = ctx_stack[-1].command
            if isinstance(current_cmd, click.MultiCommand):
                sub_name, sub_cmd, args = current_cmd.resolve_command(
                    root.ctx, [cmd_name]
                )
                if sub_cmd is None or sub_cmd.hidden:
                    root.print(not_found)
                    break
                sub_ctx = Context(sub_cmd, parent=ctx_stack[-1], info_name=sub_name)
                ctx_stack.append(sub_ctx)
            else:
                root.print(not_found)
                break
        else:
            print_help(ctx_stack[-1])
    finally:
        for ctx in reversed(ctx_stack[1:]):
            ctx.close()


def _err_to_str(err: Exception) -> str:
    result = str(err)
    if result == "":
        result = type(err).__name__
    return result


def main(args: Optional[List[str]] = None) -> None:
    setup_shell_completion()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            cli.main(
                args=args,
                standalone_mode=False,
                windows_expand_args=False,
            )
    except ClickAbort:
        log.exception("Aborting.")
        sys.exit(130)
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except ClickExit as e:
        sys.exit(e.exit_code)

    except asyncio.TimeoutError:
        log.exception("Timeout")
        sys.exit(EX_TIMEOUT)

    except apolo_sdk.IllegalArgumentError as error:
        log.exception(f"Illegal argument(s) ({_err_to_str(error)})")
        sys.exit(EX_DATAERR)

    except apolo_sdk.ResourceNotFound as error:
        log.exception(f"{_err_to_str(error)}")
        sys.exit(EX_OSFILE)

    except apolo_sdk.AuthenticationError as error:
        log.exception(f"Cannot authenticate ({_err_to_str(error)})")
        sys.exit(EX_NOPERM)
    except apolo_sdk.AuthorizationError as error:
        log.exception(f"Not enough permissions ({_err_to_str(error)})")
        sys.exit(EX_NOPERM)

    except apolo_sdk.ClientError as error:
        log.exception(f"Application error ({_err_to_str(error)})")
        sys.exit(EX_SOFTWARE)

    except apolo_sdk.BadGateway as error:
        log.exception(f"Application error ({_err_to_str(error)})")
        sys.exit(EX_PLATFORMERROR)

    except apolo_sdk.ConfigError as error:
        log.exception(f"{_err_to_str(error)}")
        sys.exit(EX_SOFTWARE)

    except aiohttp.ClientError as error:
        log.exception(f"Connection error ({_err_to_str(error)})")
        sys.exit(EX_IOERR)

    except DockerError as error:
        log.exception(f"Docker API error: {error.message}")
        sys.exit(EX_PROTOCOL)

    except apolo_sdk.NotSupportedError as error:
        log.exception(f"{_err_to_str(error)}")
        sys.exit(EX_SOFTWARE)

    except NotImplementedError as error:
        log.exception(f"{_err_to_str(error)}")
        sys.exit(EX_SOFTWARE)

    except FileNotFoundError as error:
        log.exception(f"File not found ({_err_to_str(error)})")
        sys.exit(EX_OSFILE)

    except NotADirectoryError as error:
        log.exception(f"{_err_to_str(error)}")
        sys.exit(EX_OSFILE)

    except PermissionError as error:
        log.exception(f"Cannot access file ({_err_to_str(error)})")
        sys.exit(EX_NOPERM)

    except OSError as error:
        log.exception(f"I/O Error ({_err_to_str(error)})")
        sys.exit(EX_IOERR)

    except asyncio.CancelledError:
        log.exception("Cancelled")
        sys.exit(130)

    except KeyboardInterrupt:
        log.exception("Aborting.")
        sys.exit(130)

    except ValueError as e:
        log.exception(_err_to_str(e))
        sys.exit(127)

    except SystemExit:
        raise

    except Exception as e:
        log.exception(f"{_err_to_str(e)}")
        print(f"Full logs are available under {str(file_logging.get_log_file_path())}")
        sys.exit(1)
