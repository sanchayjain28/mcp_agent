# LangGraph MCP Adapter System for Role Data Search

A system using LangGraph with MCP adapters to search and filter IT role compensation data with fuzzy matching and role name mappings. Data is stored in SQLite database for fast queries.

## Features

- **Database-Backed**: SQLite database for fast and efficient queries
- **Fuzzy Search**: Find roles even with typos or partial matches
- **Role Mapping**: Automatic mapping of aliases (e.g., 'sde2' → 'Sr. Software Developer')
- **Multiple Filters**: Filter by role, tower, location, experience, level, etc.
- **LangGraph Integration**: Agent-based system with tool calling
- **MCP Compatible**: Tools exposed via FastMCP server for MCP adapter integration

## Installation

This project uses `uv` for dependency management. Install dependencies:

```bash
uv sync
```

Or if you prefer pip:

```bash
pip install -r requirements.txt
```

## Setup

1. Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add:
   - `OPENAI_API_KEY` (if using OpenAI models)
   - `ANTHROPIC_API_KEY` (if using Claude models)
   - `ROLE_DATA_DB_PATH` (optional, defaults to `agent.db` in current directory)

3. Import CSV data into the database:
   ```bash
   uv run python import_csv.py [path_to_csv_file]
   ```
   
   The default CSV path is `../HEX Cloud Format_latest (1) - Cloud Format_ITO.csv`
   
   This will create `agent.db` with all the compensation data.

## Usage

### Interactive Mode

Run the main application:

```bash
uv run python main.py
```

Or with Python directly:

```bash
python main.py
```

### Example Queries

```bash
uv run python example_usage.py
```

### Direct Tool Usage

```python
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

# Create MCP client
client = MultiServerMCPClient({
    "role_search": {
        "transport": "stdio",
        "command": "python",
        "args": [str(Path(__file__).parent / "role_search_server.py")],
    }
})

# Get tools and create agent
tools = await client.get_tools()
agent = create_agent("claude-sonnet-4-5-20250929", tools)

# Query
response = await agent.ainvoke({
    "messages": [HumanMessage(content="Find all sde2 roles in US TIER 2")]
})
```

## Role Mappings

The system supports common role aliases:
- `sde2` → Sr. Software Developer
- `sde1` → Software Developer
- `sde3` → Tech Lead
- `senior sd` → Sr. Software Developer
- `tech lead` → Tech Lead
- `sr ba` → Sr. Business Analyst
- `dba` → DBA
- `devops` → DevOps Consultant
- And many more...

## Architecture

- **`db_helper.py`**: SQLite database helper for managing compensation data
- **`import_csv.py`**: Script to import CSV data into the database
- **`data_loader.py`**: Loads data from SQLite database
- **`role_mapper.py`**: Handles role alias mappings
- **`search_tool.py`**: Core search functionality with fuzzy matching (queries database)
- **`role_search_server.py`**: FastMCP server exposing tools via stdio
- **`main.py`**: Main application using MultiServerMCPClient
- **`example_usage.py`**: Example queries
- **`logger.py`**: Logging configuration

## MCP Server

The MCP server (`role_search_server.py`) exposes three tools:

1. **`search_roles`**: Main search function with multiple filters
2. **`get_role_suggestions`**: Autocomplete for role names
3. **`get_role_mapping_info`**: Get available role mappings

## Example Queries

- "Find all sde2 roles"
- "Show me senior software developers in US TIER 2"
- "What are the compensation ranges for tech leads with 5-7 years experience?"
- "Search for business analyst roles in Application Development tower"

## Development

The project structure follows:
- Uses `uv` for dependency management
- FastMCP for MCP server implementation
- LangChain MCP adapters for client integration
- TheFuzz for fuzzy string matching

