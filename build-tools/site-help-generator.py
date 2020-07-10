#!/usr/bin/env python3

import click
import re
import shlex
import sys
from click.formatting import wrap_text
from pathlib import Path

from neuromation.cli.main import cli, topics
from neuromation.cli.utils import split_examples


HERE = Path(sys.argv[0]).resolve().parent


def gen_command(out, cmd, parent_ctx):
    with click.Context(cmd, parent=parent_ctx, info_name=cmd.name) as ctx:
        out.append(f"### {cmd.name}")
        out.append("")

        out.append(cmd.get_short_help_str())
        out.append("")

        if cmd.deprecated:
            out.append("~~DEPRECATED~~")
            out.append("")

        out.append("#### Usage")
        out.append("")
        out.append("```bash")
        pieces = cmd.collect_usage_pieces(ctx)
        out.append(f"{ctx.command_path} " + " ".join(pieces))
        out.append("```")
        out.append("")

        help, *examples = split_examples(cmd.help)
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
                l4.append(", ".join(["`" + part2 + "`" for part2 in l2]))

            name2 = " / ".join(l4)
            descr2 = re.sub(r"(\[.+\])", r"_\1_", descr)

            w1 = max(w1, len(name2))
            w2 = max(w2, len(descr2))
            opts.append((name2, descr2))

        name_title = "Name".ljust(w1)
        descr_title = "Description".ljust(w2)
        name_sep = "-" * w1
        descr_sep = "-" * w2

        out.append("#### Options")
        out.append("")
        out.append(f"| {name_title} | {descr_title} |")
        out.append(f"| {name_sep} | {descr_sep} |")

        for name, descr in opts:
            name = name.ljust(w1)
            descr = descr.ljust(w2)
            out.append(f"| {name} | {descr} |")

        out.append("")


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
        out.append(f"neuro {group.name} " + " ".join(pieces))
        out.append("```")
        out.append("")

        out.append(click.unstyle(group.help))
        out.append("")

        commands = []
        for cmd_name in group.list_commands(ctx):
            cmd = group.get_command(ctx, cmd_name)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            commands.append(cmd)

        out.append("## Commands")
        out.append("")
        for cmd in commands:
            cmd_path = f"{group.name}.md#{cmd.name}"
            out.append(
                f"* [neuro {group.name} {cmd.name}]({cmd_path}): "
                f"{cmd.get_short_help_str()}"
            )
        out.append("")

        for index2, cmd in enumerate(commands, 1):
            gen_command(out, cmd, ctx)

        fname = target_path / f"{group.name}.md"
        fname.write_text("\n".join(out))


def gen_shortcuts(commands, target_path, ctx):
    out = ["# Shortcuts", "", "## Commands", ""]

    for cmd in commands:
        out.append(
            f"* [neuro {cmd.name}](shortcuts.md#{cmd.name}): "
            f"{cmd.get_short_help_str()}"
        )
    out.append("")

    for index2, cmd in enumerate(commands, 1):
        gen_command(out, cmd, ctx)

    fname = target_path / f"shortcuts.md"
    fname.write_text("\n".join(out))


def gen_topics(target_path, ctx):
    out = ["# Topics", ""]

    for name in topics.list_commands(ctx):
        topic = topics.get_command(ctx, name)
        out.append(
            f"* [neuro {topic.name}](topics.md#{topic.name}): "
            f"{topic.get_short_help_str()}"
        )
    out.append("")

    for name in topics.list_commands(ctx):
        topic = topics.get_command(ctx, name)
        out.append(f"## {topic.name}")
        out.append("")
        out.append(topic.help)

    fname = target_path / f"topics.md"
    fname.write_text("\n".join(out))


@click.command()
@click.option(
    "--target-dir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, writable=True, resolve_path=True
    ),
    help="Target dir in platform-web project",
    default=str(HERE.parent.parent / "platform-docs/references/cli-reference"),
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
        cli, info_name="neuro", color=False, terminal_width=80, max_content_width=80
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


if __name__ == "__main__":
    main()
