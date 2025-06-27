import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

import click
from mcp import Tool, types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Content, TextContent

from .root import Root


class ApoloMCPServer:
    def __init__(self, cli_group: click.Group):
        self.cli_group = cli_group
        self.server = Server("apolo-cli")
        self.tools: Dict[str, Tool] = {}
        self._register_handlers()
        self._generate_tools()

    def _register_handlers(self) -> None:
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return list(self.tools.values())

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]]
        ) -> List[Content]:
            if name not in self.tools:
                raise ValueError(f"Unknown tool: {name}")

            try:
                result = await self._invoke_command(name, arguments or {})
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _generate_tools(self) -> None:
        def _process_command(
            cmd: click.Command, path: str = "", is_root: bool = False
        ) -> None:
            # Don't include the root CLI name in the tool name
            if is_root:
                full_name = ""
            else:
                full_name = f"{path}_{cmd.name}" if path else cmd.name

            if isinstance(cmd, click.Group):
                for sub_cmd_name in cmd.list_commands(None):
                    sub_cmd = cmd.get_command(None, sub_cmd_name)
                    if sub_cmd and not sub_cmd.hidden:
                        _process_command(sub_cmd, full_name, is_root=False)
            else:
                # Only create tools for actual commands (not groups)
                if not is_root:  # Skip if this is the root group
                    schema = self._generate_schema(cmd)
                    tool = Tool(
                        name=full_name,
                        description=cmd.help
                        or f"Execute {full_name.replace('_', ' ')} command",
                        inputSchema=schema,
                    )
                    self.tools[full_name] = tool

        # Start with the root group
        _process_command(self.cli_group, "", is_root=True)

    def _generate_schema(self, cmd: click.Command) -> Dict[str, Any]:
        properties = {}
        required = []

        for param in cmd.params:
            if isinstance(param, click.Option):
                prop_name = param.name
                param_schema = {"type": "string"}

                if param.is_flag:
                    param_schema = {"type": "boolean"}
                elif param.multiple:
                    param_schema = {"type": "array", "items": {"type": "string"}}

                properties[prop_name] = {
                    "description": param.help or "",
                    **param_schema,
                }

                if param.required:
                    required.append(prop_name)

            elif isinstance(param, click.Argument):
                prop_name = param.name
                param_schema = {"type": "string"}

                if param.nargs != 1:
                    param_schema = {"type": "array", "items": {"type": "string"}}

                properties[prop_name] = {
                    "description": "",
                    **param_schema,
                }

                if param.required:
                    required.append(prop_name)

        return {"type": "object", "properties": properties, "required": required}

    async def _invoke_command(self, name: str, arguments: Dict[str, Any]) -> str:
        # Handle hyphens in command names by converting underscores back to the original format
        cmd_parts = name.split("_")
        cmd = self.cli_group

        for part in cmd_parts:
            if isinstance(cmd, click.Group):
                # Try the part as-is first, then try with hyphens
                found_cmd = cmd.get_command(None, part)
                if found_cmd is None and "_" not in part:
                    # Try converting underscores to hyphens for commands like service-account
                    hyphenated_part = part.replace("_", "-")
                    found_cmd = cmd.get_command(None, hyphenated_part)

                cmd = found_cmd
                if cmd is None:
                    raise ValueError(
                        f"Command not found: {name} (failed at part: {part})"
                    )
            else:
                raise ValueError(
                    f"Invalid command path: {name} (reached non-group at: {part})"
                )

        if cmd is None:
            raise ValueError(f"Command not found: {name}")

        args = []
        for param in cmd.params:
            if param.name in arguments:
                value = arguments[param.name]
                if isinstance(param, click.Option):
                    if param.is_flag:
                        if value:
                            args.append(f"--{param.name.replace('_', '-')}")
                    elif param.multiple and isinstance(value, list):
                        for v in value:
                            args.extend([f"--{param.name.replace('_', '-')}", str(v)])
                    else:
                        args.extend([f"--{param.name.replace('_', '-')}", str(value)])
                elif isinstance(param, click.Argument):
                    if param.nargs != 1 and isinstance(value, list):
                        args.extend([str(v) for v in value])
                    else:
                        args.append(str(value))

        import contextlib
        from io import StringIO

        output = StringIO()

        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                ctx = click.Context(self.cli_group)
                ctx.obj = Root(
                    verbosity=0,
                    color=False,
                    tty=False,
                    disable_pypi_version_check=True,
                    network_timeout=60.0,
                    config_path=None,
                    trace=False,
                    force_trace_all=False,
                    trace_hide_token=True,
                    command_path="",
                    command_params=[],
                    skip_gmp_stats=True,
                    show_traceback=False,
                    iso_datetime_format=False,
                    ctx=ctx,
                )

                result = await self._run_command_with_args(cmd_parts + args, ctx)
                return output.getvalue() or str(result)
        except Exception as e:
            error_output = output.getvalue()
            if error_output:
                return f"Error: {error_output}\n{str(e)}"
            return f"Error: {str(e)}"

    async def _run_command_with_args(self, args: List[str], ctx: click.Context) -> Any:
        from .main import cli

        try:
            with click.Context(cli, obj=ctx.obj) as new_ctx:
                return await asyncio.to_thread(cli.main, args, standalone_mode=False)
        except SystemExit:
            return "Command completed"

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            initialization_options = self.server.create_initialization_options()
            await self.server.run(
                read_stream,
                write_stream,
                initialization_options,
            )


async def run_mcp_server(cli_group: click.Group) -> None:
    server = ApoloMCPServer(cli_group)
    await server.run()
