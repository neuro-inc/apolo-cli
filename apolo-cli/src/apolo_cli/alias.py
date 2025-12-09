import re
import shlex
import subprocess
import sys
from typing import Any, cast

import click
from click.utils import make_default_short_help

from apolo_sdk import ConfigError

from .root import Root
from .utils import NeuroClickMixin, Option


class InternalAlias(NeuroClickMixin, click.Command):
    ignore_unknown_options = True
    allow_interspersed_args = False
    allow_extra_args = True

    def __init__(self, name: str, alias: dict[str, str]) -> None:
        super().__init__(name)
        assert "cmd" in alias
        self.alias = alias

    def invoke(self, ctx: click.Context) -> None:
        parent = ctx.parent
        assert parent is not None
        sub_cmd, *sub_args = shlex.split(self.alias["cmd"])
        parent_cmd = parent.command
        assert isinstance(parent_cmd, click.MultiCommand)
        cmd = parent_cmd.get_command(parent, sub_cmd)
        if cmd is None:
            ctx.fail(f'Alias {self.name} refers to unknown command "{sub_cmd}"')
        with ctx:
            ctx.invoked_subcommand = self.name
            sub_ctx = cmd.make_context(self.name, sub_args + ctx.args, parent=ctx)
            with sub_ctx:
                sub_ctx.command.invoke(sub_ctx)

    def get_short_help_str(self, limit: int = 45) -> str:
        txt = self.alias.get("help") or "apolo " + self.alias["cmd"]
        return make_default_short_help(txt)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        self.format_usage(ctx, formatter)
        formatter.write_paragraph()
        assert ctx.parent is not None
        alias_cmd = self.alias["cmd"]
        formatter.write(
            "Alias for "
            + click.style(f'"{ctx.parent.info_name} {alias_cmd}"', bold=True)
        )
        formatter.write_paragraph()

        help = self.alias.get("help")
        if help is not None:
            formatter.write_paragraph()
            formatter.write_text(help)

        self.format_options(ctx, formatter)


class ExternalAlias(NeuroClickMixin, click.Command):
    ignore_unknown_options = True
    allow_interspersed_args = False
    allow_extra_args = True

    def __init__(self, name: str, alias: dict[str, Any]) -> None:
        assert "exec" in alias
        options = _parse_options(alias.get("options", ""))
        args = _parse_args(alias.get("args", ""))
        simplified = _validate_exec(
            alias["exec"],
            {param.name for param in options if param.name},
            {param.name for param in args if param.name},
        )
        super().__init__(name, params=options + args)
        self.alias = alias
        self.simplified = simplified

    def invoke(self, ctx: click.Context) -> None:
        if self.simplified:
            args = self._build_simplified(ctx)
        else:
            args = self._build_pattern(ctx)
        ret = subprocess.run(args)
        if ret.returncode:
            sys.exit(ret.returncode)

    def _build_simplified(self, ctx: click.Context) -> list[str]:
        cmd = self.alias["exec"]
        ret = shlex.split(cmd)
        for param in self.params:
            val = ctx.params[param.name or ""]
            ret.extend(_process_param(param, val))
        return ret

    def _build_pattern(self, ctx: click.Context) -> list[str]:
        cmd = self.alias["exec"]
        replaces = {}
        matches = re.findall(r"{\w+}", cmd)
        for match in matches:
            name = match[1:-1]  # drop curly brackets
            name = name.lower().replace("-", "_")

            for param in self.params:
                if param.name == name:
                    break
            else:  # pragma: no cover
                # Unreachable code, _validate_exec()
                # makes sure that all param names are handled
                raise ConfigError(f'Unknown parameter {name} in "{cmd}"')
            val = ctx.params[name]
            replaces[match] = " ".join(
                shlex.quote(arg) for arg in _process_param(param, val)
            )

        for name, val in replaces.items():
            cmd = cmd.replace(name, val)

        return shlex.split(cmd)

    def get_short_help_str(self, limit: int = 45) -> str:
        txt = self.alias.get("help") or self.alias["exec"]
        return make_default_short_help(txt)

    def format_help_text(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        formatter.write_paragraph()
        alias_cmd = self.alias["exec"]
        formatter.write_text("Alias for " + click.style(f'"{alias_cmd}"', bold=True))

        help = self.alias.get("help")
        if help is not None:
            formatter.write("\n")
            formatter.write_text(help)


async def find_alias(root: Root, cmd_name: str) -> click.Command | None:
    config = await root.get_user_config()
    alias = config.get("alias", {}).get(cmd_name)
    if alias is None:
        # Command not found
        return None
    if "cmd" in alias:
        return InternalAlias(cmd_name, alias)
    elif "exec" in alias:
        return ExternalAlias(cmd_name, alias)
    else:  # pragma: no cover
        # This branch is unreachable,
        # Config file validator should prevent unknown alias type
        raise click.UsageError(f"Invalid alias description type for {cmd_name}")


async def list_aliases(root: Root) -> list[click.Command]:
    config = await root.get_user_config()
    ret: list[click.Command] = []
    for cmd_name, alias in config.get("alias", {}).items():
        if "cmd" in alias:
            ret.append(InternalAlias(cmd_name, alias))
        elif "exec" in alias:
            ret.append(ExternalAlias(cmd_name, alias))
        else:  # pragma: no cover
            # This branch is unreachable,
            pass
    return ret


def _parse_options(descr: list[str]) -> list[click.Parameter]:
    ret = []
    for od in descr:
        opts = []
        is_flag = True
        metavar = None
        options, _, description = od.strip().partition("  ")
        options = options.replace(",", " ").replace("=", " ")
        for s in options.split():
            if s.startswith("--"):
                if not s[2:].replace("-", "_").isidentifier():
                    raise ConfigError(f"Cannot parse option {od}")
                opts.append(s)
            elif s.startswith("-"):
                if not s[1:].isidentifier():
                    raise ConfigError(f"Cannot parse option {od}")
                opts.append(s)
            else:
                is_flag = False
                metavar = s
                metavar = metavar.upper()
                if not metavar.isidentifier():
                    raise ConfigError(f"Cannot parse option {od}")
        description = description.strip()
        kwargs = {}
        if is_flag:
            kwargs["count"] = True
        else:
            kwargs["multiple"] = True
        ret.append(
            Option(
                opts,
                metavar=metavar,
                help=description,
                **kwargs,
            )
        )
    return ret  # type: ignore


def _parse_args(source: str) -> list[click.Parameter]:
    ret = []
    src1 = re.sub(r"([\[\]]|\.\.\.)", r" \1 ", source)
    src2 = [s for s in re.split(r"\s+|(\S*<.*?>)", src1) if s]
    required = True
    multiple = False
    brackets = False
    arg = None
    for item in src2:
        if item == "]":
            if not brackets:
                raise ConfigError(f'Missing open bracket in "{source}"')
            if arg is None:
                raise ConfigError(f'Missing argument inside brackets in "{source}"')
            brackets = False
            required = False
        elif item == "...":
            if arg is None:
                raise ConfigError(
                    f'Ellipsis (...) should follow an argument in "{source}"'
                )
            if brackets:
                raise ConfigError(f'Ellipsis (...) inside of brackets in "{source}"')
            if multiple:
                raise ConfigError(f'Successive ellipsis (...) in "{source}"')
            multiple = True
        else:
            if arg is not None:
                if brackets:
                    raise ConfigError(f'Missing close bracket in "{source}"')
                ret.append(
                    click.Argument(
                        [arg],
                        required=required,
                        nargs=-1 if multiple else 1,
                        type=click.UNPROCESSED,
                    )
                )
                required = True
                multiple = False
                brackets = False
                arg = None
            if item == "[":
                if brackets:
                    raise ConfigError(f'Nested brackets in "{source}"')
                brackets = True
            else:
                arg = item.upper()
    if arg is not None:
        if brackets:
            raise ConfigError(f'Missing close bracket in "{source}"')
        ret.append(
            click.Argument(
                [arg],
                required=required,
                nargs=-1 if multiple else 1,
                type=click.UNPROCESSED,
            )
        )
    return ret  # type: ignore


def _validate_exec(cmd: str, options: set[str], args: set[str]) -> bool:
    # Return True for simplified form, False otherwise
    if args & options:
        overlapped = ",".join(args & options)
        raise ConfigError(
            "The following names are present in both "
            f"positional and optional arguments: {overlapped}"
        )
    params = args | options
    matches = re.findall(r"{\w*}", cmd)
    if not matches:
        return True
    for match in matches:
        name = match[1:-1]  # drop curly brackets
        if not name:
            raise ConfigError(f'Empty substitution is not allowed in "{cmd}"')

        if not name.isidentifier():
            raise ConfigError(f'Parameter {name} is not a valid identifier in "{cmd}"')

        if not name.islower():
            raise ConfigError(f'Parameter {name} should be lowercased in "{cmd}"')

        if name not in params:
            raise ConfigError(f'Unknown parameter {name} in "{cmd}"')

    return False


def _longest(opts: list[str]) -> str:
    # group long options first
    possible_opts = sorted(opts, key=lambda x: -len(x))
    return possible_opts[0]


def _process_param(param: click.Parameter, val: str | tuple[str] | None) -> list[str]:
    if isinstance(param, click.Argument):
        if not param.required:
            if not val:
                return []
        assert val is not None
        if param.nargs != 1:
            assert isinstance(val, tuple)
            return list(val)
        else:
            assert isinstance(val, str)
            return [val]
    elif isinstance(param, click.Option):
        if not val:
            # empty tuple
            return []
        if param.is_flag:
            # parser generates bool flags only
            assert param.is_bool_flag
            # parser doesn't allow --true / --false flags
            assert not param.secondary_opts
            vals = []
            for isset in val:
                if isset:
                    vals.append(_longest(param.opts))
            return vals
        elif param.count:
            vals = [_longest(param.opts)] * cast(int, val)
            return vals
        else:
            vals = []
            for item in val:
                vals.append(_longest(param.opts))
                vals.append(item)
            return vals
    else:  # pragma: no cover
        # Unreachable branch
        raise RuntimeError(f"Unsupported parameter type {type(param)}")
