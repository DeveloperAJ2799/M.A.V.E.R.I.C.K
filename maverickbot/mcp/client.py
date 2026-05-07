"""MCP Client for connecting to MCP servers."""

import asyncio
import os
import re
import subprocess
import traceback
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPServerConnection:
    """Represents a connection to an MCP server."""

    def __init__(self, name: str, process: Optional[subprocess.Popen] = None, session: Optional[Any] = None):
        self.name = name
        self.process = process
        self.session = session
        self.read_stream = None
        self.write_stream = None
        self.tools: List[MCPTool] = []
        self.connected = False
        self._last_error: Optional[str] = None

    async def close(self):
        """Close the connection."""
        if self.session:
            try:
                await self.session.close()
            except Exception as e:
                logger.debug(f"Error closing session: {e}")
            self.session = None

        if self.read_stream:
            try:
                await self.read_stream.aclose()
            except Exception:
                pass
            self.read_stream = None

        if self.write_stream:
            try:
                await self.write_stream.aclose()
            except Exception:
                pass
            self.write_stream = None

        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
        self.process = None
        self.connected = False

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    def set_error(self, error: str):
        """Set the last error message."""
        self._last_error = error


class MCPClient:
    """Client for connecting to MCP servers."""

    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}
        self._mcp_available = False
        self._check_mcp()

    def _check_mcp(self):
        """Check if MCP SDK is available."""
        try:
            import mcp
            self._mcp_available = True
            logger.info("MCP SDK available")
        except ImportError:
            logger.warning("MCP SDK not installed. Install with: pip install mcp[cli]")
            self._mcp_available = False

    async def connect_stdio(self, name: str, command: str, args: List[str], env: Dict[str, str] = None) -> Optional[MCPServerConnection]:
        """Connect to an MCP server using stdio transport."""
        if not self._mcp_available:
            logger.error("MCP SDK not installed. Run: pip install mcp[cli]")
            return None

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            full_env = os.environ.copy()
            if env:
                full_env = self._expand_env_vars(env, full_env)

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=full_env
            )

            logger.info(f"Connecting to MCP server: {name}")
            logger.debug(f"Command: {command} {' '.join(args)}")

            read, write = await stdio_client(server_params).__aenter__()
            session = ClientSession(read, write)
            await session.initialize()

            tools_result = await session.list_tools()
            tools = []
            for tool in tools_result.tools:
                tools.append(MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                ))

            connection = MCPServerConnection(name=name, session=session)
            connection.read_stream = read
            connection.write_stream = write
            connection.tools = tools
            connection.connected = True
            self.servers[name] = connection

            logger.info(f"Connected to MCP server: {name} with {len(tools)} tools")
            return connection

        except ImportError as e:
            logger.error(f"MCP import error: {e}. Install with: pip install mcp[cli]")
            return None
        except FileNotFoundError as e:
            logger.error(f"Command not found: {command}. Ensure the MCP server command is installed.")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {name}: {e}")
            logger.debug(traceback.format_exc())
            return None

    async def connect_http(self, name: str, url: str, headers: Dict[str, str] = None, timeout: float = 30.0) -> Optional[MCPServerConnection]:
        """Connect to an MCP server using HTTP/SSE transport."""
        if not self._mcp_available:
            logger.error("MCP SDK not installed. Run: pip install mcp[cli]")
            return None

        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            logger.info(f"Connecting to MCP server via HTTP: {name} at {url}")

            async with streamable_http_client(url, headers=headers or {}, timeout=timeout) as (read, write, get_next_message):
                session = ClientSession(read, write)
                await session.initialize()

                tools_result = await session.list_tools()
                tools = []
                for tool in tools_result.tools:
                    tools.append(MCPTool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    ))

                connection = MCPServerConnection(name=name, session=session)
                connection.read_stream = read
                connection.write_stream = write
                connection.tools = tools
                connection.connected = True
                self.servers[name] = connection

                logger.info(f"Connected to MCP server: {name} with {len(tools)} tools")
                return connection

        except ImportError as e:
            logger.error(f"MCP import error: {e}. Install with: pip install mcp[cli]")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {name}: {e}")
            logger.debug(traceback.format_exc())
            return None

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on an MCP server."""
        connection = self.servers.get(server_name)
        if not connection or not connection.connected:
            error_msg = f"Server not connected: {server_name}"
            connection.set_error(error_msg) if connection else None
            return {"error": error_msg}

        try:
            result = await connection.session.call_tool(tool_name, arguments)

            if hasattr(result, 'content') and result.content:
                texts = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        texts.append(content.text)
                    elif isinstance(content, dict):
                        texts.append(str(content))
                return "\n".join(texts) if texts else str(result)
            return str(result)

        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            connection.set_error(str(e))
            return {"error": str(e)}

    def _expand_env_vars(self, env: Dict[str, str], base_env: Dict[str, str] = None) -> Dict[str, str]:
        """Expand environment variable references in env dict.

        Supports ${VAR} and $VAR syntax.
        """
        result = (base_env or os.environ).copy()

        for key, value in env.items():
            if isinstance(value, str):
                def replace_var(match):
                    var_name = match.group(1) or match.group(2)
                    return os.environ.get(var_name, "")
                value = re.sub(r'\$\{(\w+)\}|\$(\w+)', replace_var, value)
            result[key] = value

        return result

    def get_all_tools(self) -> List[MCPTool]:
        """Get all tools from all connected servers."""
        tools = []
        for connection in self.servers.values():
            if connection.connected:
                for tool in connection.tools:
                    # Prefix with server name to avoid conflicts
                    tools.append(MCPTool(
                        name=f"{connection.name}_{tool.name}",
                        description=f"[{connection.name}] {tool.description}",
                        input_schema=tool.input_schema
                    ))
        return tools

    async def disconnect_all(self):
        """Disconnect all servers."""
        for connection in self.servers.values():
            await connection.close()
        self.servers.clear()

    def list_servers(self) -> List[str]:
        """List connected server names."""
        return list(self.servers.keys())

    def get_server_tools(self, server_name: str) -> List[MCPTool]:
        """Get tools for a specific server."""
        connection = self.servers.get(server_name)
        return connection.tools if connection else []