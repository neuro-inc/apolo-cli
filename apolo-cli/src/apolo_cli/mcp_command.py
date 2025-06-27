import asyncio

import click

from .mcp_integration import run_mcp_server
from .root import Root
from .utils import command


@command()
async def mcp(root: Root) -> None:
    """Start MCP server for AI agent integration."""
    from .main import cli
    
    await run_mcp_server(cli)