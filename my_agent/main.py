import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agent_manager import initialize_agent, get_agent, close

# Load environment variables
load_dotenv()

async def main():
    """Main CLI application for interactive role search."""
    # Initialize agent
    await initialize_agent()
    
    print("Agent ready! Type 'quit' to exit.\n")
    
    try:
        while True:
            user_input = input("You: ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                agent = await get_agent()
                # Invoke the agent
                response = await agent.ainvoke({
                    "messages": [HumanMessage(content=user_input)]
                })
                
                # Get the last message
                last_message = response["messages"][-1]
                print(f"\nAgent: {last_message.content}\n")
            except Exception as e:
                print(f"\nError: {e}\n")
    finally:
        # Cleanup on exit
        await close()

if __name__ == "__main__":
    asyncio.run(main())
