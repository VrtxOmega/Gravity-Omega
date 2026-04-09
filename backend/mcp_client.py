"""
mcp_client.py - VERITAS Ω MCP SDK Integration
Bridging Gravity Omega VTP router to the local omega-command-center MCP Server.
"""

import sys
import os
import json
import asyncio
from typing import Dict, Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

COMMAND_CENTER_SCRIPT = r"C:\Users\rlope\.gemini\antigravity\scratch\VERITAS_COMMAND_CENTER\omega_mcp_engine.py"

class OmegaMCPClient:
    """Manages synchronous execution bridging into async MCP environment."""
    
    def __init__(self):
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["OMEGA_MODE"] = "veritas"
        
        self.server_params = StdioServerParameters(
            command="python",
            args=[COMMAND_CENTER_SCRIPT],
            env=env
        )
        self._loop = asyncio.new_event_loop()
    
    async def _async_assess_file(self, path: str, mode: str = "veritas") -> Dict[str, Any]:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Run the 5-gate VERITAS pipeline on a Python file via MCP call
                result = await session.call_tool("omega_assess_file", arguments={"path": path, "mode": mode})
                
                # Parse standard MCP tool result format -> single text output
                if hasattr(result, "content") and len(result.content) > 0:
                    try:
                        return json.loads(result.content[0].text)
                    except Exception:
                        return {"verdict": "INCONCLUSIVE", "raw": result.content[0].text}
                return {"verdict": "INCONCLUSIVE", "raw": "No content returned"}
                
    def assess_file_sync(self, path: str, mode: str = "veritas") -> Dict[str, Any]:
        """Synchronously blocks and calls omega_assess_file over MCP."""
        # Note: If path doesn't exist yet, we still request an assessment? 
        # Typically the tool takes an absolute path.
        try:
            return self._loop.run_until_complete(self._async_assess_file(path, mode))
        except Exception as e:
            return {"error": str(e), "verdict": "INCONCLUSIVE", "isError": True}

_global_client = None

def get_mcp_client() -> OmegaMCPClient:
    global _global_client
    if _global_client is None:
        _global_client = OmegaMCPClient()
    return _global_client
