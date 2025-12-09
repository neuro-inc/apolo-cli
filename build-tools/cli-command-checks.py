#!/usr/bin/env python3
import abc
import os
import sys
from dataclasses import dataclass

import click

from apolo_cli.main import cli

SHORT_LEN_LIMIT = 45


@dataclass(frozen=True)
class Error:
    message: str


class CommandChecker(abc.ABC):
    def __init__(self, errors: list[Error]) -> None:
        self._errors = errors

    def _add_error(self, message: str) -> None:
        self._errors.append(Error(message))

    def __call__(self, command: click.Command, name: str) -> None:
        pass


class ShortDocLen(CommandChecker):
    def __init__(self, len_limit: int, errors: list[Error]):
        super().__init__(errors)
        self._len_limit = len_limit

    def __call__(self, command: click.Command, name: str) -> None:
        short_help = command.get_short_help_str(1000)
        if len(short_help) > SHORT_LEN_LIMIT:
            self._add_error(
                f"Command '{name}' short help is longer then "
                f"{SHORT_LEN_LIMIT} characters"
            )


class UniqueShortDocInGroup(CommandChecker):
    def __init__(self, errors: list[Error]):
        super().__init__(errors)
        self._short_docs_to_command: dict[(str, str), str] = {}

    def __call__(self, command: click.Command, name: str) -> None:
        group_name = name.rsplit(" ", 1)[0]
        short_help = command.get_short_help_str(1000)
        key = (group_name, short_help)
        if key in self._short_docs_to_command:
            another_name = self._short_docs_to_command[key]
            self._add_error(
                f"Commands '{name}' and '{another_name}' have same short doc"
                f" in the same group, it may brake autocomplete."
            )
        self._short_docs_to_command[key] = name


def check_commands_tree(
    parent_ctx: click.Context | None,
    command: click.Command,
    stack: list[str],
    checkers: list[CommandChecker],
) -> None:
    """
    Walk given command and all subcommands and check predicate
    """

    with click.Context(
        command,
        info_name=stack[-1],
        color=False,
        terminal_width=80,
        max_content_width=80,
        parent=parent_ctx,
    ) as ctx:

        for checker in checkers:
            checker(command=command, name=" ".join(stack))

        if isinstance(command, click.MultiCommand):
            for command_name in command.list_commands(ctx):
                sub_cmd = command.get_command(ctx, command_name)
                if sub_cmd is None:
                    continue
                if sub_cmd.hidden:
                    continue
                check_commands_tree(ctx, sub_cmd, stack + [command_name], checkers)


def main():
    if len(sys.argv) != 1:
        print("Usage cli-command-short-doc-len-check.py")
        exit(os.EX_USAGE)

    errors: list[Error] = []

    check_commands_tree(
        None,
        cli,
        ["apolo"],
        [
            ShortDocLen(SHORT_LEN_LIMIT, errors),
            UniqueShortDocInGroup(errors),
        ],
    )

    if errors:
        for error in errors:
            print(error.message)
        exit(1)


if __name__ == "__main__":
    main()
