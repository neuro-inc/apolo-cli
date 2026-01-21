from textwrap import dedent

from click.testing import CliRunner

from apolo_cli.root import Root
from apolo_cli.utils import DeprecatedGroup, command, group


def test_print_hidden() -> None:
    @group()
    def sub_command() -> None:
        pass

    @command(hidden=True)
    async def plain_cmd(root: Root) -> None:
        pass

    @group()
    def main() -> None:
        pass

    main.add_command(sub_command)
    main.add_command(plain_cmd)

    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Usage: main [OPTIONS] COMMAND [ARGS]...

        Commands:
          sub-command
    """)


def test_print_deprecated_group() -> None:
    @group()
    def sub_command() -> None:
        """
        Sub-command.
        """

    @group()
    def main() -> None:
        pass

    main.add_command(sub_command)
    main.add_command(DeprecatedGroup(sub_command, name="alias"))

    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Usage: main [OPTIONS] COMMAND [ARGS]...

        Commands:
          alias        (Deprecated) Alias for sub-command
          sub-command  Sub-command
    """)


def test_print_deprecated_group_content() -> None:
    @group()
    def sub_command() -> None:
        """
        Sub-command.
        """

    @sub_command.command()
    async def cmd(root: Root) -> None:
        """Command.

        Detailed description is here.
        """

    @group()
    def main() -> None:
        pass

    main.add_command(sub_command)
    main.add_command(DeprecatedGroup(sub_command, name="alias"))
    main.skip_init = True

    runner = CliRunner()
    result = runner.invoke(main, ["alias"])
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Usage: main alias [OPTIONS] COMMAND [ARGS]...

          Alias for sub-command (DEPRECATED)

        Commands:
          cmd  Command
    """)


def test_print_deprecated_no_help() -> None:
    @command(deprecated=True)
    async def main(root: Root) -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Usage: main [OPTIONS]

           (DEPRECATED)

        Options:
          --help  Show this message and exit.
    """)


def test_print_deprecated_with_help() -> None:
    @command(deprecated=True)
    async def main(root: Root) -> None:
        """Main help."""

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Usage: main [OPTIONS]

          Main help. (DEPRECATED)

        Options:
          --help  Show this message and exit.
    """)


def test_print_help_with_examples() -> None:
    @command()
    async def main(root: Root) -> None:
        """
        Main help.

        Examples:

        # comment
        example

        """

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Usage: main [OPTIONS]

          Main help.

        Examples:
          # comment
          example

        Options:
          --help  Show this message and exit.
    """)
