"""FastAPI application for the Role Search Agent."""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from typing import Optional, List
from agent_manager import initialize_agent, get_agent, get_client, close

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources on startup/shutdown"""
    # Initialize agent on startup
    await initialize_agent()
    print("FastAPI server starting...\n")
    
    yield
    
    # Cleanup on shutdown
    await close()
    print("Shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Role Search Agent API",
    description="API for querying the role search agent with MCP tools",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    tools_available: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    tools_loaded: Optional[int] = None
    tools: Optional[List[str]] = None

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with health check"""
    try:
        client = await get_client()
        tools = await client.get_tools()
        return HealthResponse(
            status="ready",
            tools_loaded=len(tools),
            tools=[tool.name for tool in tools]
        )
    except Exception:
        return HealthResponse(status="initializing")

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return await root()

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Send a query to the agent and get a response.
    
    Args:
        request: QueryRequest containing the user's query string
        
    Returns:
        QueryResponse with the agent's response and available tools
    """
    agent = await get_agent()
    client = await get_client()
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Invoke the agent
        response = await agent.ainvoke({
            "messages": [HumanMessage(content=request.query)]
        })
        
        # Get the last message
        last_message = response["messages"][-1]
        
        # Get available tools for reference
        tools = await client.get_tools()
        tool_names = [tool.name for tool in tools]
        
        return QueryResponse(
            response=last_message.content,
            tools_available=tool_names
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/tools")
async def get_tools():
    """Get list of available tools from the MCP server"""
    try:
        client = await get_client()
        tools = await client.get_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in tools
            ],
            "count": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tools: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

