"""Shared agent manager for initializing and managing the MCP client and agent."""
import os
import shutil
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from logger import logger
from dotenv import load_dotenv

load_dotenv()

BRIGHT_DATA_API_KEY = os.getenv("BRIGHT_DATA_API_TOKEN")
if not BRIGHT_DATA_API_KEY:
    raise ValueError("BRIGHT_DATA_API_TOKEN is not set")

# Global variables for agent and client
_agent = None
_client = None
_initialized = False


async def initialize_agent(model: str = "gpt-5-nano"):
    """Initialize the MCP client and agent."""
    global _agent, _client, _initialized
    
    if _initialized:
        return _agent, _client
    
    server_script_path = Path(__file__).parent / "role_search_server.py"
    
    servers_config = {
        "role_search": {
            "transport": "stdio", 
            "command": "python",
            "args": [str(server_script_path)],
        }
    }
    
    npx_path = shutil.which("npx")
    node_path = shutil.which("node")
    node_bin_dir = None
    
    if not npx_path or not node_path:
        nvm_node = Path.home() / ".nvm" / "versions" / "node"
        if nvm_node.exists():
            node_versions = sorted([d for d in nvm_node.iterdir() if d.is_dir()], reverse=True)
            if node_versions:
                node_bin_dir = node_versions[0] / "bin"
                if not npx_path and (node_bin_dir / "npx").exists():
                    npx_path = str(node_bin_dir / "npx")
                if not node_path and (node_bin_dir / "node").exists():
                    node_path = str(node_bin_dir / "node")
                    node_bin_dir = str(node_bin_dir)
    

    # Check for Memora server
    memora_path = shutil.which("memora-server")
    try:
        memora_env = os.environ.copy()
        # Set default database path if not already set
        if "MEMORA_DB_PATH" not in memora_env:
            memora_db_path = Path.home() / ".local" / "share" / "memora" / "memories.db"
            memora_db_path.parent.mkdir(parents=True, exist_ok=True)
            memora_env["MEMORA_DB_PATH"] = str(memora_db_path)
        # Enable graph server on default port if not set
        if "MEMORA_GRAPH_PORT" not in memora_env:
            memora_env["MEMORA_GRAPH_PORT"] = "8765"
        # Allow any tags by default
        if "MEMORA_ALLOW_ANY_TAG" not in memora_env:
            memora_env["MEMORA_ALLOW_ANY_TAG"] = "1"
        
        memora_abs_path = str(Path(memora_path).resolve())
        
        servers_config["memora"] = {
            "transport": "stdio",
            "command": memora_abs_path,
            "args": [],
            "env": memora_env
        }
        logger.info(f"Memora MCP server will be initialized (path: {memora_path}, db: {memora_env.get('MEMORA_DB_PATH')})")
    except Exception as e:
        logger.warning(f"Error initializing Memora MCP server: {e}")
        logger.warning("Continuing without Memora server...")
    else:
        logger.info("Warning: memora-server not found. Memora MCP server will not be available.")
        logger.info("To enable Memora, install it via: pip install git+https://github.com/agentic-mcp-tools/memora.git")
    
    # Check for Bright Data server (requires Node.js/npm)
    if npx_path and node_path:
        try:
            if not node_bin_dir:
                node_bin_dir = str(Path(node_path).parent)
            
            env = os.environ.copy()
            # Ensure Node.js bin directory is in PATH
            current_path = env.get("PATH", "")
            if node_bin_dir and node_bin_dir not in current_path:
                env["PATH"] = f"{node_bin_dir}:{current_path}"
            
            env["API_TOKEN"] = BRIGHT_DATA_API_KEY
            
            # Use absolute path to npx to ensure it's found
            npx_abs_path = str(Path(npx_path).resolve())
            
            servers_config["Bright Data"] = {
                "transport": "stdio",
                "command": npx_abs_path,
                "args": ["@brightdata/mcp"],
                "env": env
            }
            logger.info(f"Bright Data MCP server will be initialized (npx: {npx_path}, node: {node_path})")
        except Exception as e:
            logger.warning(f"Error initializing Bright Data MCP server: {e}")
            logger.warning("Continuing without Bright Data server...")
    else:
        logger.info("Warning: npx or node not found. Bright Data MCP server will not be available.")
        logger.info("To enable Bright Data:")
        logger.info("  1. Install Node.js (v20+): https://nodejs.org/")
        logger.info("     Or use nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash")
        logger.info("  2. Install the Bright Data MCP package: npx @brightdata/mcp")
    
    _client = MultiServerMCPClient(servers_config)
    
    try:
        logger.info(f"Initializing {len(servers_config)} MCP server(s): {list(servers_config.keys())}")
        tools = await _client.get_tools()
        logger.info(f"Successfully loaded {len(tools)} tool(s) from all servers")

        tool_names = [tool.name for tool in tools]
        logger.info(f"Available tools: {', '.join(tool_names)}")
        
    except Exception as e:
        logger.error(f"Error getting tools from MCP servers: {e}")
        logger.error(f"Server config: {servers_config}")

        if len(servers_config) > 1:
            logger.warning("One or more servers failed. Testing servers individually...")

            other_servers = {k: v for k, v in servers_config.items() if k != "role_search"}
            working_servers = {"role_search": servers_config["role_search"]}
            
            for server_name, server_config in other_servers.items():
                try:
                    logger.info(f"Testing {server_name} server...")
                    test_config = {server_name: server_config}
                    test_client = MultiServerMCPClient(test_config)
                    test_tools = await test_client.get_tools()
                    logger.info(f"✓ {server_name} server OK - {len(test_tools)} tools")
                    working_servers[server_name] = server_config
                except Exception as server_error:
                    logger.warning(f"✗ {server_name} server failed: {server_error}")
                    logger.warning(f"  Continuing without {server_name} server...")
        else:
            raise
    
    _agent = create_agent(model, tools)
    
    _initialized = True
    logger.info("Agent initialized successfully!")
    
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

