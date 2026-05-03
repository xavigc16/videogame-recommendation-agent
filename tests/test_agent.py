from src.agent import app
from langchain_core.messages import HumanMessage

def test_agent_can_respond():

    inputs = {"messages": [HumanMessage(content="Say the word 'Banana' and nothing else.")]}
    final_state = app.invoke(inputs)
    final_message = final_state["messages"][-1].content
    
    assert len(final_state["messages"]) > 1, "Agent did not add a message to the state"
    assert "banana" in final_message.lower(), f"Agent failed to follow instructions. It said: {final_message}"