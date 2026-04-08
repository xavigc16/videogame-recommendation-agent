from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict, Annotated
import operator
from typing import Literal
from langgraph.graph import StateGraph, START, END
from src.tools import tools

model = init_chat_model(
    "claude-3-5-sonnet-20240620",
    temperature=0
).bind_tools(tools)

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

def llm_call(state: MessagesState):
    """LLM decides whether to call a tool or reply to the user"""
    response = model.invoke(
        [
            SystemMessage(
                content=(
                    "You are a knowledgeable and opinionated video game assistant. "
                    "When a user asks for opinions on a game, use the search_game_opinions tool "
                    "to retrieve reviews, then synthesize them into a helpful response."
                )
            )
        ]
        + state["messages"]
    )
    
    return {
        "messages": [response],
        "llm_calls": state.get('llm_calls', 0) + 1
    }

def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "tool_node"

    return END

agent_builder = StateGraph(MessagesState)

agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", ToolNode(tools)) 

agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
)
agent_builder.add_edge("tool_node", "llm_call")
agent = agent_builder.compile()




messages = [HumanMessage(content="What are people saying about Hollow Knight?")]
result = agent.invoke({"messages": messages, "llm_calls": 0})

for m in result["messages"]:
    m.pretty_print()