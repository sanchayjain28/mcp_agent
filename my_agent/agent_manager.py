"""Shared agent manager for initializing and managing the MCP client and agent."""
import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

# Get Bright Data API token from environment variable
BRIGHT_DATA_API_KEY = os.getenv("BRIGHT_DATA_API_TOKEN", "937673d6077325f58c265d5e0e4fc28dfebbfb44afad624d3c87b724f34b3afe")
# Global variables for agent and client
_agent = None
_client = None
_initialized = False

async def initialize_agent(model: str = "gpt-5-nano"):
    """Initialize the MCP client and agent."""
    global _agent, _client, _initialized
    
    if _initialized:
        return _agent, _client
    
    # Get absolute path to the MCP server script
    server_script_path = Path(__file__).parent / "role_search_server.py"
    
    # Build server configuration dictionary
    servers_config = {
        "role_search": {
            "transport": "stdio",  # Local subprocess communication
            "command": "python",
            # Absolute path to your role_search_server.py file
            "args": [str(server_script_path)],
        }
    }
    
    # Add Bright Data server only if npx and node are available
    # Check for npx in PATH first, then check common nvm locations
    npx_path = shutil.which("npx")
    node_path = shutil.which("node")
    node_bin_dir = None
    
    if not npx_path or not node_path:
        # Check nvm directory if not in PATH
        nvm_node = Path.home() / ".nvm" / "versions" / "node"
        if nvm_node.exists():
            # Find the latest node version
            node_versions = sorted([d for d in nvm_node.iterdir() if d.is_dir()], reverse=True)
            if node_versions:
                node_bin_dir = node_versions[0] / "bin"
                if not npx_path and (node_bin_dir / "npx").exists():
                    npx_path = str(node_bin_dir / "npx")
                if not node_path and (node_bin_dir / "node").exists():
                    node_path = str(node_bin_dir / "node")
                    node_bin_dir = str(node_bin_dir)
    
    if npx_path and node_path:
        # Get the node bin directory for PATH
        if not node_bin_dir:
            node_bin_dir = str(Path(node_path).parent)
        
        # Get current environment and add node bin to PATH
        env = os.environ.copy()
        current_path = env.get("PATH", "")
        if node_bin_dir not in current_path:
            env["PATH"] = f"{node_bin_dir}:{current_path}"
        
        # Add Bright Data API token
        env["API_TOKEN"] = BRIGHT_DATA_API_KEY
        
        servers_config["Bright Data"] = {
            "transport": "stdio",
            "command": npx_path,
            "args": ["@brightdata/mcp"],
            "env": env
        }
        print(f"Bright Data MCP server will be initialized (npx: {npx_path}, node: {node_path})")
    else:
        print("Warning: npx or node not found. Bright Data MCP server will not be available.")
        print("To enable Bright Data, install Node.js/npm which includes npx and node.")
    
    # Create MCP client with available servers
    _client = MultiServerMCPClient(servers_config)
    
    # Get tools from MCP server
    print("Connecting to MCP server and loading tools...")
    tools = await _client.get_tools()
    print(f"Loaded {len(tools)} tools: {[tool.name for tool in tools]}\n")
    
    # Create agent with tools
    _agent = create_agent(model, tools)
    
    _initialized = True
    print("Agent initialized successfully!")
    
    return _agent, _client

async def get_agent():
    """Get the initialized agent, initializing if necessary."""
    global _agent, _client
    if not _initialized:
        await initialize_agent()
    return _agent

async def get_client():
    """Get the initialized client, initializing if necessary."""
    global _agent, _client
    if not _initialized:
        await initialize_agent()
    return _client

async def close():
    """Close the client and cleanup resources."""
    global _agent, _client, _initialized
    if _client:
        try:
            await _client.close()
        except Exception:
            pass  # Ignore errors during cleanup
    _agent = None
    _client = None
    _initialized = False

def is_initialized():
    """Check if the agent is initialized."""
    return _initialized

