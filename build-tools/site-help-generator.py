#!/usr/bin/env python3
from __future__ import annotations

import inspect
import re
import shlex
import sys
from pathlib import Path

import click
from click.formatting import wrap_text

from apolo_cli.main import cli
from apolo_cli.topics import topics
from apolo_cli.utils import split_examples

HERE = Path(sys.argv[0]).resolve().parent


def _process_help(help: str | None) -> str:
    return inspect.cleandoc(help or "").partition("\f")[0]


def gen_command(out, cmd, parent_ctx):
    with click.Context(cmd, parent=parent_ctx, info_name=cmd.name) as ctx:
        out.append(f"### {cmd.name}\n")

        descr = cmd.get_short_help_str()
        descr = re.sub(r"(?<!\n)\n(?!\n)", r" ", descr)
        out.append(descr)
        out.append("\n")

        if cmd.deprecated:
            out.append("~~DEPRECATED~~\n")

        out.append("#### Usage\n")
        out.append("```bash")
        pieces = cmd.collect_usage_pieces(ctx)
        out.append(f"{ctx.command_path} " + " ".join(pieces))
        out.append("```\n")

        help, *examples = split_examples(_process_help(cmd.help))
        help2 = click.unstyle(help)
        help3 = re.sub(r"([A-Z0-9\-]{3,60})", r"`\1`", help2)
        out.append(wrap_text(help3))
        out.append("")

        for example in examples:
            out.append("#### Examples")
            out.append("")
            out.append("```bash")
            example2 = click.unstyle(example)
            for line in example2.splitlines():
                line = line.strip()
                if line.startswith("#"):
                    out.append(line)
                else:
                    if line:
                        out.append("$ " + " ".join(shlex.split(line)))
                    else:
                        out.append("")
            out.append("```")
            out.append("")

        opts = []
        w1 = w2 = 0
        for param in cmd.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is None:
                continue
            name, descr = rv

            # dirty code for wrapping options with backticks
            l4 = []
            l1 = re.split(" ?/ ?", name)
            for part in l1:
                l2 = re.split(" ?, ?", part)
                l4.append(", ".join(l2))

            name2 = " / ".join(l4)
            descr2 = re.sub(r"(\[.+\])", r"_\1_", descr)

            w1 = max(w1, len(name2))
            w2 = max(w2, len(descr2))
            opts.append((name2, descr2))

        out.append("#### Options\n")
        out.append(f"| Name | Description |")
        out.append(f"| :--- | :--- |")

        for name, descr in opts:
            out.append(
                f"| _{escape_cell(name.replace('|', ' | '))}_ "
                f"| {escape_cell(descr)} |"
                f""
            )

        out.append("\n\n")


def simple_escape_line(text: str) -> str:
    escaped = re.sub(r"\*", r"\\*", text)
    escaped = re.sub(r"<(\S[^*]*)>", r"&lt;\1&gt;", escaped)
    escaped = re.sub(r"_", r"\\_", escaped)
    escaped = re.sub(r"\[(\S[^\]]*)\]", r"\\[\1\\]", escaped)
    escaped = re.sub(r"\((\S[^)]*)\)", r"\\(\1\\)", escaped)
    escaped = re.sub(r"\\_\\\[", r"_\[", escaped)
    escaped = re.sub(r"\\]\\_", r"\]_", escaped)

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
    return "\n".join(escaped)


def escape_cell(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\|", r"&#124;", escaped)
    return escaped


def gen_group(group, target_path, parent_ctx):
    out = []
    with click.Context(group, parent=parent_ctx, info_name=group.name) as ctx:
        out.append(f"# {group.name}")
        out.append("")

        out.append(group.get_short_help_str())
        out.append("")

        out.append("## Usage")
        out.append("")
        out.append("```bash")
        pieces = group.collect_usage_pieces(ctx)
        out.append(f"apolo {group.name} " + " ".join(pieces))
        out.append("```")
        out.append("")

        out.append(click.unstyle(_process_help(group.help)))
        out.append("")

        commands = []
        for cmd_name in group.list_commands(ctx):
            cmd = group.get_command(ctx, cmd_name)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            commands.append(cmd)

        out.append("**Commands:**")
        out.append("| Usage | Description |")
        out.append("| :--- | :--- |")
        for cmd in commands:
            anchor = cmd.name
            anchor = f"{group.name}.md#" + anchor.replace(" ", "-")
            out.append(
                f"| [_{escape_cell(cmd.name)}_]({anchor}) "
                f"| {escape_cell(cmd.get_short_help_str())} |"
            )

        out.append("\n")

        for index2, cmd in enumerate(commands, 1):
            gen_command(out, cmd, ctx)

        fname = target_path / f"{group.name}.md"
        fname.write_text("\n".join(out))


def gen_shortcuts(commands, target_path, ctx):
    out = ["# Shortcuts"]
    out.append("**Commands:**")
    out.append("| Usage | Description |")
    out.append("| :--- | :--- |")

    for cmd in commands:
        anchor = cmd.name
        anchor = f"shortcuts.md#" + anchor.replace(" ", "-")
        out.append(
            f"| [_apolo {escape_cell(cmd.name)}_]({anchor}) "
            f"| {escape_cell(cmd.get_short_help_str())} |"
        )
    out.append("\n")

    for index2, cmd in enumerate(commands, 1):
        gen_command(out, cmd, ctx)

    fname = target_path / f"shortcuts.md"
    fname.write_text("\n".join(out))


def gen_topics(target_path, ctx):
    for name in topics.list_commands(ctx):
        topic = topics.get_command(ctx, name)
        out = [_process_help(topic.help)]
        fname = target_path / f"topic-{topic.name}.md"
        fname.write_text("\n".join(out))


def gen_summary(target_path, groups, ctx):
    out = ["# Table of contents\n"]

    out.append("\n## Commands\n")
    for group in groups:
        out.append(f"* [{group.name}](apolo-cli/docs/{group.name}.md)")

    out.append("\n## Topics\n")
    for name in topics.list_commands(ctx):
        topic = topics.get_command(ctx, name)
        out.append(
            f"* [{topic.get_short_help_str()}](apolo-cli/docs/topic-{topic.name}.md)"
        )

    fname = target_path / "SUMMARY.md"
    fname.write_text("\n".join(out))


@click.command()
@click.option(
    "--target-dir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, writable=True, resolve_path=True
    ),
    help="Target dir in platform-web project",
    default=str(HERE.parent / "apolo-cli/docs"),
    show_default=True,
)
def main(target_dir):
    target_path = Path(target_dir)
    EXCLUDES = ("README.md", "CLI.md")
    for child in target_path.iterdir():
        if child.suffix != ".md":
            continue
        if child.name.startswith(EXCLUDES):
            continue
        child.unlink()

    groups = []
    shortcuts = []
    with click.Context(
        cli, info_name="apolo", color=False, terminal_width=80, max_content_width=80
    ) as ctx:
        for cmd_name in cli.list_commands(ctx):
            cmd = cli.get_command(ctx, cmd_name)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            if cmd.name == "help":
                continue

            if isinstance(cmd, click.MultiCommand):
                groups.append(cmd)
            else:
                shortcuts.append(cmd)

    gen_shortcuts(shortcuts, target_path, ctx)

    for i, group in enumerate(groups, 2):
        gen_group(group, target_path, ctx)

    # Topics generator produces ugly looking markdown, sorry
    gen_topics(target_path, ctx)

    # For summary
    groups.append(click.Group(name="shortcuts"))

    gen_summary(target_path, sorted(groups, key=lambda g: g.name), ctx)


if __name__ == "__main__":
    main()
