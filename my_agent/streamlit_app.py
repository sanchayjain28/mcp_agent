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

   

st.title("🔍 Role Search Agent")
st.markdown("Ask questions about IT roles and compensation data using natural language.")

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
    

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about roles..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    if st.session_state.agent_initialized:
        with st.chat_message("assistant"):
            try:
                agent = asyncio.run(get_agent())
                response = asyncio.run(agent.ainvoke({"messages": [HumanMessage(content=prompt)]}))
                last_message = response["messages"][-1]
                if hasattr(last_message, 'content'):
                    full_response = last_message.content
                else:
                    full_response = str(last_message)
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as fallback_error:
                    error_msg = f"Fallback error: {str(fallback_error)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    else:
        with st.chat_message("assistant"):
            st.warning("Agent is still initializing. Please wait...")

if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

