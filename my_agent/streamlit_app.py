"""Streamlit application for the Role Search Agent."""
import asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agent_manager import initialize_agent, get_agent, get_client

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Role Search Agent",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = False
if "messages" not in st.session_state:
    st.session_state.messages = []

async def initialize():
    """Initialize the agent asynchronously."""
    if not st.session_state.agent_initialized:
        with st.spinner("Connecting to MCP server and loading tools..."):
            await initialize_agent()
            st.session_state.agent_initialized = True
            st.rerun()

async def producer(user_query: str, queue: asyncio.Queue):
    """
    Producer: Put chunks into the queue as they arrive from the agent.
    """
    from langchain_core.messages import AIMessage  # noqa: F401
    
    try:
        agent = await get_agent()
        seen_content = set()  # Track seen content to avoid duplicates
        
        # Use astream instead of ainvoke for streaming
        async for chunk in agent.astream({
            "messages": [HumanMessage(content=user_query)]
        }):
            # Extract content from the chunk
            # Chunk structure: {'model': {'messages': [...]}} or {'tools': {'messages': [...]}}
            messages = None
            
            # Check for nested structure
            if "model" in chunk and "messages" in chunk["model"]:
                messages = chunk["model"]["messages"]
            elif "tools" in chunk and "messages" in chunk["tools"]:
                # Skip tool messages, we only want the final model response
                continue
            elif "messages" in chunk:
                messages = chunk["messages"]
            
            if messages:
                for message in messages:
                    # Only process content from AIMessage (final response)
                    if isinstance(message, AIMessage) and hasattr(message, "content") and message.content:
                        current_content = ""
                        
                        if isinstance(message.content, str):
                            current_content = message.content
                        elif isinstance(message.content, list):
                            # Extract text from content blocks
                            text_parts = []
                            for block in message.content:
                                if isinstance(block, dict) and "text" in block:
                                    text_parts.append(block["text"])
                                elif isinstance(block, str):
                                    text_parts.append(block)
                            current_content = "".join(text_parts)
                        
                        # Put content into queue if it's new and not empty
                        if current_content and current_content.strip() and current_content not in seen_content:
                            # For incremental content, extract only new parts
                            # Check if any seen content is a prefix of current (iterate over copy)
                            is_new = True
                            for seen in list(seen_content):
                                if current_content.startswith(seen):
                                    # This is incremental, put only the new part
                                    new_part = current_content[len(seen):]
                                    if new_part:
                                        await queue.put(new_part)
                                        seen_content.add(current_content)
                                        is_new = False
                                        break
                            
                            # If it's completely new content, put it all
                            if is_new:
                                await queue.put(current_content)
                                seen_content.add(current_content)
        
        # Signal completion by putting None
        await queue.put(None)
    except Exception as e:
        # Put error in queue and signal completion
        await queue.put(("error", str(e)))
        await queue.put(None)

async def consumer(queue: asyncio.Queue, response_placeholder):
    """
    Consumer: Pop chunks from the queue and display them.
    """
    chunks = []
    while True:
        # Wait for item from queue
        item = await queue.get()
        
        # Check for completion signal
        if item is None:
            break
        
        # Check for error
        if isinstance(item, tuple) and item[0] == "error":
            raise Exception(item[1])
        
        # Process chunk
        if item and item.strip():
            chunks.append(item)
            current_text = "".join(chunks)
            response_placeholder.markdown(current_text + "▌")
    
    # Return full response
    return "".join(chunks)

# Main UI
st.title("🔍 Role Search Agent")
st.markdown("Ask questions about IT roles and compensation data using natural language.")

# Initialize agent on first load
if not st.session_state.agent_initialized:
    asyncio.run(initialize())

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This agent can help you search for IT roles and compensation data.
    
    **Example queries:**
    - "Find all sde2 roles in US TIER 2"
    - "Show me senior software developers"
    - "What are the compensation ranges for tech leads?"
    """)
    
    if st.session_state.agent_initialized:
        try:
            client = asyncio.run(get_client())
            tools = asyncio.run(client.get_tools())
            st.header("🛠️ APP is running and ready to answer your questions")
        except Exception as e:
            st.error(f"Error loading tools: {e}")
    st.header("Your Chats")
    

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about roles..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response with streaming
    if st.session_state.agent_initialized:
        with st.chat_message("assistant"):
            try:
                response_placeholder = st.empty()
                
                async def stream_and_display():
                    """Async function to handle streaming and display using queue."""
                    try:
                        # Create queue for producer-consumer pattern
                        queue = asyncio.Queue()
                        
                        # Start producer task (puts chunks into queue)
                        producer_task = asyncio.create_task(producer(prompt, queue))
                        
                        # Start consumer (pops from queue and displays)
                        full_response = await consumer(queue, response_placeholder)
                        
                        # Wait for producer to complete
                        await producer_task
                        
                        # If no chunks were received, fallback to non-streaming
                        if not full_response:
                            raise Exception("No content received from streaming")
                        
                        # Remove cursor for final display
                        response_placeholder.markdown(full_response)
                        return full_response
                    except Exception as stream_error:
                        # Fallback to non-streaming on any error
                        try:
                            agent = await get_agent()
                            response = await agent.ainvoke({
                                "messages": [HumanMessage(content=prompt)]
                            })
                            last_message = response["messages"][-1]
                            # Handle both string content and message objects
                            if hasattr(last_message, 'content'):
                                full_response = last_message.content
                            else:
                                full_response = str(last_message)
                            response_placeholder.markdown(full_response)
                            return full_response
                        except Exception as fallback_error:
                            # If fallback also fails, show the original error
                            error_msg = f"Streaming error: {str(stream_error)}. Fallback error: {str(fallback_error)}"
                            response_placeholder.error(error_msg)
                            raise stream_error
                
                full_response = asyncio.run(stream_and_display())
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
    else:
        with st.chat_message("assistant"):
            st.warning("Agent is still initializing. Please wait...")

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

