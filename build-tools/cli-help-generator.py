#!/usr/bin/env python3

import os
import re
import sys
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any

import click

from apolo_cli.main import cli


@dataclass()
class Option:
    pattern: str = None
    description: str = None


@dataclass()
class CommandInfo:
    name: str = None
    usage: str = None
    short: str = None
    description: str = None
    options: list[Option] = field(default_factory=list)
    examples: str = None
    children: list[Any] = field(default_factory=list)  # CommandInfo
    is_group: bool = False


def parse_doc(ctx, command, stack) -> CommandInfo:
    name = " ".join(stack)
    formatter = ctx.make_formatter()
    command.format_usage(ctx, formatter)
    usage = click.unstyle(formatter.getvalue())
    usage = re.split(r"usage\s*:", usage, maxsplit=2, flags=re.IGNORECASE)[1].strip()
    short = click.unstyle(command.get_short_help_str(80))
    is_group = isinstance(command, click.MultiCommand)
    info = CommandInfo(name=name, usage=usage, short=short, is_group=is_group)

    formatter = ctx.make_formatter()
    command.format_help_text(ctx, formatter)
    help = click.unstyle(formatter.getvalue())
    parts = re.split(r"examples:", help, flags=re.IGNORECASE)
    info.description = dedent(parts[0])
    if len(parts) > 1:
        assert len(parts) == 2
        info.examples = dedent(parts[1])

    for param in command.get_params(ctx):
        ret = param.get_help_record(ctx)
        if ret:
            info.options.append(Option(click.unstyle(ret[0]), click.unstyle(ret[1])))

    return info


def parse_command(parent_ctx, command, stack) -> CommandInfo:
    """
    Walk given command and all subcommands and create corresponding CommandInfo
    """

    with click.Context(
        command,
        info_name=stack[-1],
        color=False,
        terminal_width=80,
        max_content_width=80,
        parent=parent_ctx,
    ) as ctx:
        info = parse_doc(ctx, command, stack)

        if info.is_group:
            for command_name in command.list_commands(ctx):
                sub_cmd = command.get_command(ctx, command_name)
                if sub_cmd is None:
                    continue
                if sub_cmd.hidden:
                    continue
                info.children.append(
                    parse_command(ctx, sub_cmd, stack + [command_name])
                )

    return info


def generate_markdown(info: CommandInfo, header_prefix: str = "#") -> str:
    def simple_escape_line(text: str) -> str:
        escaped = re.sub(r"\*(\S[^*]*)\*", r"\\*\1*", text)
        escaped = re.sub(r"\-(\S[^*]*)\-", r"\\-\1-", escaped)
        escaped = re.sub(r"\_(\S[^*]*)\_", r"\\_\1_", escaped)
        escaped = re.sub(r"\[(\S[^\]]*)\]", r"\\[\1]", escaped)
        escaped = re.sub(r"\((\S[^)]*)\)", r"\\(\1)", escaped)

        return escaped

    def escape(text: str) -> str:
        # escaped = text.replace('\\', '\\\\')
        escaped = []
        lines = text.splitlines()
        for line in lines:
            before = line
            after = simple_escape_line(line)
            while before != after:
                before = after
                after = simple_escape_line(line)
            escaped.append(after)
        return "<br/>".join(escaped)

    def escape_cell(text: str) -> str:
        escaped = escape(text)
        escaped = re.sub(r"\|", r"&#124;", escaped)
        return escaped

    md = ""
    md += f"{header_prefix}# {info.name}"
    md += "\n\n"

    if info.description:
        md += escape(info.description)
        md += "\n\n"

    if info.usage:
        md += f"**Usage:**\n\n"
        md += "```bash\n"
        md += info.usage
        md += "\n```\n\n"

    if info.examples:
        md += f"**Examples:**\n\n"
        md += "```bash\n"
        md += info.examples
        md += "\n```\n\n"

    if info.options:
        md += "**Options:**\n\n"
        md += "Name | Description|\n"
        md += "|----|------------|\n"
        for option in info.options:
            md += (
                f"|_{escape_cell(option.pattern.replace('|', ' | '))}_"
                f"|{escape_cell(option.description)}|"
                f"\n"
            )

        md += "\n\n"

    groups = [child for child in info.children if child.is_group]
    if groups:
        md += "**Command Groups:**\n\n"
        md += "|Usage|Description|\n"
        md += "|---|---|\n"
        for group in groups:
            anchor = group.name
            anchor = "#" + anchor.replace(" ", "-")
            md += (
                f"| _[{escape_cell(group.name)}]({anchor})_"
                f"| {escape_cell(group.short)} |\n"
            )
        md += "\n\n"

    commands = [child for child in info.children if not child.is_group]
    if commands:
        md += "**Commands:**\n\n"
        md += "|Usage|Description|\n"
        md += "|---|---|\n"
        for command in commands:
            anchor = command.name
            anchor = "#" + anchor.replace(" ", "-")
            md += (
                f"| _[{escape_cell(command.name)}]({anchor})_"
                f"| {escape_cell(command.short)} |\n"
            )
        md += "\n\n"

    return md


def generate_command_markdown(info: CommandInfo, header_prefix="") -> str:
    md = generate_markdown(info, header_prefix)
    if info.children:
        groups = [child for child in info.children if child.is_group]
        commands = [child for child in info.children if not child.is_group]
        md += "\n\n" + "\n\n".join(
            generate_command_markdown(item, header_prefix + "#")
            for item in groups + commands
        )
    return md


def main():
    if len(sys.argv) != 3:
        print("Usage cli-help-generator.py input_file output_file")
        exit(os.EX_USAGE)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    with open(input_file) as input, open(output_file, "w") as output:
        template = input.read()
        info = parse_command(None, cli, ["apolo"])
        cli_doc = generate_command_markdown(info, "")
        generated_md = template.format(cli_doc=cli_doc)
        output.write(generated_md)


if __name__ == "__main__":
    main()
