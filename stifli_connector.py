#!/usr/bin/env python3
"""
Stifli MCP Connector for WordPress Automation

Uses the stifli-flex-mcp WordPress plugin to automate tasks.
Requires: STIFLI_PASSWORD environment variable (WordPress App Password)
Username is typically your WordPress admin email or username.

Usage:
    export STIFLI_USERNAME="shan.simmons@gmail.com"
    export STIFLI_PASSWORD="your-app-password-here"
    python3 -c "from stifli_connector import StifliMCP; mcp = StifliMCP(); print(mcp.list_tools())"
"""

import os
import json
import base64
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict


class StifliMCP:
    """
    Connector for stifli-flex-mcp WordPress plugin.
    
    Uses JSON-RPC 2.0 over REST API.
    """
    
    def __init__(self, site_url: str = "https://kylosarc.com", username: str = None, password: str = None):
        self.site_url = site_url.rstrip("/")
        self.username = username or os.environ.get("STIFLI_USERNAME", "")
        self.password = password or os.environ.get("STIFLI_PASSWORD", "")
        
        if not self.username or not self.password:
            raise ValueError("STIFLI_USERNAME and STIFLI_PASSWORD must be set")
        
        auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        self.auth_header = f"Basic {auth}"
        
        self.messages_url = f"{self.site_url}/wp-json/stifli-flex-mcp/v1/messages"
        self.sse_url = f"{self.site_url}/wp-json/stifli-flex-mcp/v1/sse"
    
    def _post(self, method: str, params: Dict = None) -> Dict:
        """Send JSON-RPC request."""
        import urllib.request
        import urllib.error
        
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }).encode()
        
        req = urllib.request.Request(
            self.messages_url,
            data=payload,
            headers={
                "Authorization": self.auth_header,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"HTTP {e.code}: {error_body}")
    
    def list_tools(self) -> List[MCPTool]:
        """List all available MCP tools."""
        result = self._post("tools/list")
        
        tools = []
        # Handle nested result structure
        tools_data = result.get("result", {})
        if isinstance(tools_data, dict):
            tools_data = tools_data.get("tools", [])
        
        for tool in tools_data:
            tools.append(MCPTool(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {})
            ))
        
        return tools
    
    def call_tool(self, tool_name: str, arguments: Dict = None) -> Dict:
        """Call a specific MCP tool with arguments."""
        result = self._post("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })
        return result
    
    def execute(self, method: str, params: Dict = None) -> Dict:
        """Execute any JSON-RPC method."""
        return self._post(method, params)
    
    def get_current_user(self) -> Dict:
        """Get current WordPress user info."""
        return self._post("wp.getCurrentUser")
    
    def __repr__(self) -> str:
        return f"StifliMCP(site={self.site_url}, user={self.username})"


def main():
    """Test the connector."""
    import sys
    
    try:
        mcp = StifliMCP()
        print(f"Connected to: {mcp}")
        print("\nAvailable tools:")
        tools = mcp.list_tools()
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
    except ValueError as e:
        print(f"Error: {e}")
        print("Set environment variables:")
        print("  export STIFLI_USERNAME='your-email@example.com'")
        print("  export STIFLI_PASSWORD='your-app-password'")
        sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()