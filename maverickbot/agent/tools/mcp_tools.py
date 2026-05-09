from typing import Any, Dict, List, Optional
import json
import asyncio
from pathlib import Path

from maverickbot.mcp import MCPClient
from .base import Tool, ToolResult


class AddMCPServerTool(Tool):
    name = "add_mcp_server"
    description = "Add and connect to an MCP server from a URL. Returns success message with available tools."
    
    def __init__(self):
        super().__init__(name=self.name, description=self.description)
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Unique name for this server connection"},
                "url": {"type": "string", "description": "URL of the MCP server (HTTP/SSE endpoint)"},
                "headers": {"type": "object", "description": "Optional dict of HTTP headers"}
            },
            "required": ["name", "url"]
        }
    
    async def execute(self, name: str, url: str, headers: Optional[Dict[str, str]] = None) -> ToolResult:
        try:
            client = MCPClient()
            connection = await client.connect_http(name=name, url=url, headers=headers or {})
            
            if connection and connection.connected:
                tool_names = [t.name for t in connection.tools]
                return ToolResult(
                    success=True, 
                    message=f"Connected to MCP server '{name}'. Available tools: {', '.join(tool_names)}"
                )
            else:
                return ToolResult(
                    success=False, 
                    message=f"Failed to connect to MCP server '{name}'. Check URL and try again."
                )
                
        except Exception as e:
            return ToolResult(success=False, message=f"Error connecting to MCP server '{name}': {str(e)}")


class AddMCPServerStdioTool(Tool):
    name = "add_mcp_server_stdio"
    description = "Add and connect to an MCP server using stdio transport (local command)."
    
    def __init__(self):
        super().__init__(name=self.name, description=self.description)
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Unique name for this server connection"},
                "command": {"type": "string", "description": "Command to run (e.g., 'npx', 'python')"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments"},
                "env": {"type": "object", "description": "Environment variables"}
            },
            "required": ["name", "command", "args"]
        }
    
    async def execute(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> ToolResult:
        try:
            client = MCPClient()
            connection = await client.connect_stdio(name=name, command=command, args=args, env=env or {})
            
            if connection and connection.connected:
                tool_names = [t.name for t in connection.tools]
                return ToolResult(
                    success=True, 
                    message=f"Connected to MCP server '{name}'. Available tools: {', '.join(tool_names)}"
                )
            else:
                return ToolResult(
                    success=False, 
                    message=f"Failed to connect to MCP server '{name}'."
                )
                
        except Exception as e:
            return ToolResult(success=False, message=f"Error connecting to MCP server '{name}': {str(e)}")


class ListMCPServersTool(Tool):
    name = "list_mcp_servers"
    description = "List all connected MCP servers and their available tools."
    
    def __init__(self):
        super().__init__(name=self.name, description=self.description)
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}
    
    async def execute(self) -> ToolResult:
        try:
            client = MCPClient()
            servers = client.list_servers()
            
            if not servers:
                return ToolResult(success=True, message="No MCP servers connected.")
            
            result = ["Connected MCP Servers:\n"]
            for server_name in servers:
                tools = client.get_server_tools(server_name)
                result.append(f"  - {server_name}: {len(tools)} tools")
                for tool in tools[:5]:
                    result.append(f"    • {tool.name}")
                if len(tools) > 5:
                    result.append(f"    ... and {len(tools) - 5} more")
            
            return ToolResult(success=True, message="\n".join(result))
            
        except Exception as e:
            return ToolResult(success=False, message=f"Error listing MCP servers: {str(e)}")


class RemoveMCPServerTool(Tool):
    name = "remove_mcp_server"
    description = "Disconnect from a specific MCP server."
    
    def __init__(self):
        super().__init__(name=self.name, description=self.description)
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the server to remove"}
            },
            "required": ["name"]
        }
    
    async def execute(self, name: str) -> ToolResult:
        try:
            client = MCPClient()
            connection = client.servers.get(name)
            
            if connection:
                await connection.close()
                del client.servers[name]
                return ToolResult(success=True, message=f"Disconnected from MCP server '{name}'")
            else:
                return ToolResult(success=False, message=f"Server '{name}' not found")
                
        except Exception as e:
            return ToolResult(success=False, message=f"Error disconnecting from '{name}': {str(e)}")


class CallMCPToolTool(Tool):
    name = "call_mcp_tool"
    description = "Call a tool from an MCP server."
    
    def __init__(self):
        super().__init__(name=self.name, description=self.description)
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Name of the connected server"},
                "tool_name": {"type": "string", "description": "Name of the tool to call"},
                "arguments": {"type": "object", "description": "Arguments to pass to the tool"}
            },
            "required": ["server_name", "tool_name"]
        }
    
    async def execute(self, server_name: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            client = MCPClient()
            args = arguments or {}
            result = await client.call_tool(server_name, tool_name, args)
            
            if isinstance(result, dict) and "error" in result:
                return ToolResult(success=False, message=f"Tool error: {result['error']}")
            
            return ToolResult(success=True, message=str(result))
                
        except Exception as e:
            return ToolResult(success=False, message=f"Error calling {tool_name} on {server_name}: {str(e)}")


def add_mcp_server_from_url(url: str, name: Optional[str] = None) -> str:
    """Convenience function to add an MCP server from just a URL."""
    if not name:
        name = url.split("/")[-1].replace(".git", "").split("?")[0]
    
    return asyncio.run(AddMCPServerTool().execute(name=name, url=url))
