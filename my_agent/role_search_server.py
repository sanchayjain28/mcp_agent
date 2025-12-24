import os
from pathlib import Path
from fastmcp import FastMCP
from data_loader import DataLoader
from search_tool import SearchTool
from typing import List, Dict, Any, Optional

# Initialize the MCP server
mcp = FastMCP("Role Search Server")

# Global search tool instance
search_tool_instance: Optional[SearchTool] = None

def initialize_search_tool(db_path: Optional[str] = None):
    """Initialize the search tool with database"""
    global search_tool_instance
    data_loader = DataLoader(db_path=db_path)
    search_tool_instance = SearchTool(data_loader)

# Get database path (default to agent.db in current directory)
DB_PATH = os.getenv("ROLE_DATA_DB_PATH", None)
# Initialize on import
initialize_search_tool(DB_PATH)

@mcp.tool()
async def search_roles(
    role: Optional[str] = None,
    tower: Optional[str] = None,
    sub_tower: Optional[str] = None,
    location: Optional[str] = None,
    level: Optional[str] = None,
    min_experience: Optional[int] = None,
    max_experience: Optional[int] = None,
    fuzzy_threshold: int = 80,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    ["Use this tool to search for IT roles and compensation data with flexible filtering. Supports fuzzy role name matching, multiple filter criteria, and role aliases."]
    Search for IT roles and compensation data with flexible filtering.
    
    Supports:
    - Fuzzy role name matching (e.g., 'sde2' maps to 'Sr. Software Developer')
    - Multiple filter criteria (tower, location, experience, etc.)
    - Role aliases (sde2, senior sd, etc. automatically mapped)
    
    Args:
        role: Role name or alias (e.g., 'sde2', 'Sr. Software Developer', 'senior sd')
        tower: Filter by tower (e.g., 'Application Development')
        sub_tower: Filter by sub tower (e.g., 'Coding/Development')
        location: Filter by location (e.g., 'US TIER 2')
        level: Filter by level (e.g., 'Level 1', 'Level 2')
        min_experience: Minimum years of experience
        max_experience: Maximum years of experience
        fuzzy_threshold: Fuzzy match threshold (0-100, default 80)
        limit: Maximum number of results (default 50)
    
    Returns:
        List of matching role records with compensation data
    """
    if search_tool_instance is None:
        return [{"error": "Search tool not initialized"}]
    
    try:
        results = await search_tool_instance.search(
            role=role,
            tower=tower,
            sub_tower=sub_tower,
            location=location,
            level=level,
            min_experience=min_experience,
            max_experience=max_experience,
            fuzzy_threshold=fuzzy_threshold,    
            limit=limit
        )
        return results
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
async def get_role_suggestions(partial_role: str, limit: int = 10) -> List[str]:
    """
    ["Use this tool to get role name suggestions based on partial input. Useful for autocomplete or discovering available roles. Supports fuzzy matching for roles like "sde2", "senior sd", "tech lead", etc."]
    Get role name suggestions based on partial input.
    Useful for autocomplete or discovering available roles.
    
    Args:
        partial_role: Partial role name to search for
        limit: Maximum number of suggestions
    
    Returns:
        List of suggested role names
    """
    if search_tool_instance is None:
        return []
    
    try:
        return await search_tool_instance.get_role_suggestions(partial_role, limit)
    except Exception as e:
        return []

@mcp.tool()
async def get_location_suggestions(partial_location: str, limit: int = 10) -> List[str]:
    """
    ["Use this tool to get location name suggestions based on partial input. Useful for autocomplete or discovering available locations. Supports fuzzy matching for locations like "mexico", "india", "sweden", "us tier 2", etc."]
    Get location name suggestions based on partial input.
    Useful for autocomplete or discovering available locations.
    Supports fuzzy matching for locations like "mexico", "india", "sweden", "us tier 2", etc.
    
    Args:
        partial_location: Partial location name to search for
        limit: Maximum number of suggestions
    
    Returns:
        List of suggested location names
    """
    if search_tool_instance is None:
        return []
    
    try:
        return await search_tool_instance.get_location_suggestions(partial_location, limit)
    except Exception as e:
        return []

if __name__ == "__main__":
    mcp.run(transport="stdio")

