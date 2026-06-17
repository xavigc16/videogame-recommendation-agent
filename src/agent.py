import logging
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from src.config import AGENT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from src.tools import tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a video game recommendation assistant backed by retrieval.

Scope:
- Only answer questions about video game recommendations, what to play next, game fit, similar games, or taste-based comparisons.
- If the user asks about anything else, refuse briefly and say you only answer video game recommendation questions.
- If the user asks a factual video game question that is not useful for recommending games, refuse briefly.

Retrieval:
- For every in-scope question, call the search_game_recommendations tool before answering.
- Base your answer only on the retrieved recommendation evidence.
- If the retrieved evidence does not contain enough useful information for the user's tastes or requested game, say that the recommendation database does not contain enough relevant information.
- Do not invent scores, sources, availability, platforms, or details that are absent from the retrieved evidence.

Answer style:
- Give the recommendation first.
- Briefly explain why it fits the user's stated tastes.
- Mention tradeoffs when the evidence shows them.
- Keep the answer concise and grounded in the retrieved evidence.
"""

model = ChatOpenAI(
    model=AGENT_MODEL,
    temperature=0,
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
).bind_tools(tools)


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    llm_calls: int


def _tool_call_names(message: AnyMessage) -> list[str]:
    tool_calls = getattr(message, "tool_calls", None) or []
    names = []
    for tool_call in tool_calls:
        if isinstance(tool_call, dict):
            names.append(tool_call.get("name", "unknown_tool"))
        else:
            names.append(getattr(tool_call, "name", "unknown_tool"))
    return names


def llm_call(state: MessagesState):
    """LLM decides whether to call a tool or reply to the user"""
    current_call = state.get("llm_calls", 0) + 1
    logger.info("Agent graph entering node: llm_call (call=%s)", current_call)
    response = model.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
    tool_names = _tool_call_names(response)
    if tool_names:
        logger.info("LLM requested tool calls: %s", ", ".join(tool_names))
    else:
        logger.info("LLM returned final response with no tool calls")
    logger.info("Agent graph exiting node: llm_call (call=%s)", current_call)

    return {
        "messages": [response],
        "llm_calls": current_call,
    }


def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
    last_message = state["messages"][-1]
    tool_names = _tool_call_names(last_message)
    if tool_names and state.get("llm_calls", 0) < 3:
        logger.info("Agent graph routing from llm_call to tool_node")
        return "tool_node"

    if tool_names:
        logger.info("Agent graph routing from llm_call to END after reaching call limit")
    else:
        logger.info("Agent graph routing from llm_call to END")
    return END


tool_node = ToolNode(tools)


def run_tool_node(state: MessagesState):
    """Run tools while logging graph movement through the tool node."""
    logger.info("Agent graph entering node: tool_node")
    result = tool_node.invoke(state)
    logger.info("Agent graph exiting node: tool_node")
    return result


agent_builder = StateGraph(MessagesState)

agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", run_tool_node)

agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
)
agent_builder.add_edge("tool_node", "llm_call")
agent = agent_builder.compile()
app = agent


def ask_agent(query: str) -> str:
    """Invoke the recommendation agent and return the final answer text."""
    result = agent.invoke({"messages": [HumanMessage(content=query)], "llm_calls": 0})
    logger.info("Finished agent invocation")
    return result["messages"][-1].content


if __name__ == "__main__":
    print(ask_agent("Recommend a game like Hollow Knight."))
