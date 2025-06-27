import pytest


def test_mcp_command_import() -> None:
    from apolo_cli.mcp_command import mcp

    assert mcp is not None
    assert callable(mcp)


def test_mcp_integration_import() -> None:
    from apolo_cli.mcp_integration import ApoloMCPServer, run_mcp_server

    assert run_mcp_server is not None
    assert callable(run_mcp_server)
    assert ApoloMCPServer is not None


def test_mcp_command_available_in_cli() -> None:
    from apolo_cli.main import cli

    commands = cli.list_commands(None)
    assert "mcp" in commands
