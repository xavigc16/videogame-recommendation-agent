import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing_extensions import Annotated, NotRequired, TypedDict

from src.config import AGENT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from src.tools import get_game_details, search_game_recommendations

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """Classify the user's request.

Return:
- out_of_scope: not about video games.
- agent_info: greets the assistant or asks what this assistant can do.
- game_details: asks for factual information, metadata, or frontend-ready details about one exact game name.
- recommendation: asks what to play, similar games, fit, taste, or comparison.

For game_details, set game_name to the exact game name from the user.
For recommendation, set query to the user's full request.
"""

RECOMMENDATION_PROMPT = """You are a video game recommendation assistant.

- Base recommendation answers only on retrieved recommendation evidence.
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
)


class RouteDecision(BaseModel):
    intent: Literal["out_of_scope", "agent_info", "game_details", "recommendation"]
    game_name: str | None = None
    query: str | None = None


router_model = model.with_structured_output(RouteDecision)


class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: NotRequired[str]
    query: NotRequired[str]
    game_name: NotRequired[str]
    frontend_payload: NotRequired[dict | None]


def route_intent(state: MessagesState) -> dict:
    query = _last_user_text(state)
    logger.info("Agent graph entering node: route_intent")
    decision = _classify_intent(query)
    logger.info("Agent routed intent: %s", decision.intent)
    logger.info("Agent graph exiting node: route_intent")
    return {
        "intent": decision.intent,
        "query": decision.query or query,
        "game_name": decision.game_name,
    }


def _classify_intent(query: str) -> RouteDecision:
    normalized_query = query.strip().lower().strip("!?., ")
    if normalized_query.startswith(("hi", "hello", "hey")) or normalized_query in {
        "help",
        "what can you do",
        "who are you",
    }:
        return RouteDecision(intent="agent_info")
    return router_model.invoke(
        [SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=query)]
    )


def route_by_intent(
    state: MessagesState,
) -> Literal[
    "out_of_scope_node", "agent_info_node", "game_details_node", "recommendation_node"
]:
    intent = state.get("intent")
    if intent == "agent_info":
        return "agent_info_node"
    if intent == "game_details":
        return "game_details_node"
    if intent == "recommendation":
        return "recommendation_node"
    return "out_of_scope_node"


def out_of_scope_node(state: MessagesState) -> dict:
    logger.info("Agent graph entering node: out_of_scope_node")
    message = AIMessage(
        content="I only answer video game recommendation or game detail questions."
    )
    logger.info("Agent graph exiting node: out_of_scope_node")
    return {"messages": [message], "frontend_payload": None}


def agent_info_node(state: MessagesState) -> dict:
    logger.info("Agent graph entering node: agent_info_node")
    user_text = _last_user_text(state).strip().lower()
    prefix = "Hi. " if user_text.startswith(("hi", "hello", "hey")) else ""
    message = AIMessage(
        content=(
            f"{prefix}I can recommend video games from retrieved evidence and give "
            "details about a specific game in the recommendation database."
        )
    )
    logger.info("Agent graph exiting node: agent_info_node")
    return {"messages": [message], "frontend_payload": None}


def game_details_node(state: MessagesState) -> dict:
    logger.info("Agent graph entering node: game_details_node")
    game_name = state.get("game_name") or state.get("query") or _last_user_text(state)
    result = json.loads(get_game_details.invoke({"game_name": game_name}))
    payload = result.get("frontend_payload")
    logger.info("Agent graph exiting node: game_details_node")
    return {
        "messages": [AIMessage(content=_game_details_answer(result))],
        "frontend_payload": payload,
    }


def recommendation_node(state: MessagesState) -> dict:
    logger.info("Agent graph entering node: recommendation_node")
    query = state.get("query") or _last_user_text(state)
    evidence = search_game_recommendations.invoke({"query": query})
    answer = _answer_recommendation(query, evidence)
    logger.info("Agent graph exiting node: recommendation_node")
    return {"messages": [AIMessage(content=answer)], "frontend_payload": None}


def _answer_recommendation(query: str, evidence: str) -> str:
    response = model.invoke(
        [
            SystemMessage(content=RECOMMENDATION_PROMPT),
            HumanMessage(content=f"User request: {query}\n\nEvidence:\n{evidence}"),
        ]
    )
    return str(response.content)


def _game_details_answer(result: dict) -> str:
    return result.get("message", "Game not found.")


def _last_user_text(state: MessagesState) -> str:
    return str(state["messages"][-1].content)


agent_builder = StateGraph(MessagesState)

agent_builder.add_node("route_intent", route_intent)
agent_builder.add_node("out_of_scope_node", out_of_scope_node)
agent_builder.add_node("agent_info_node", agent_info_node)
agent_builder.add_node("game_details_node", game_details_node)
agent_builder.add_node("recommendation_node", recommendation_node)

agent_builder.add_edge(START, "route_intent")
agent_builder.add_conditional_edges(
    "route_intent",
    route_by_intent,
)
agent_builder.add_edge("out_of_scope_node", END)
agent_builder.add_edge("agent_info_node", END)
agent_builder.add_edge("game_details_node", END)
agent_builder.add_edge("recommendation_node", END)
agent = agent_builder.compile()
app = agent


def ask_agent(query: str) -> str:
    """Invoke the recommendation agent and return the final answer text."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    logger.info("Finished agent invocation")
    return result["messages"][-1].content


def ask_agent_with_payload(query: str) -> dict:
    """Invoke the agent and return answer text plus any frontend payload."""
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    logger.info("Finished agent invocation")
    return {
        "answer": result["messages"][-1].content,
        "frontend_payload": result.get("frontend_payload"),
    }


if __name__ == "__main__":
    print(ask_agent("Recommend a game like Hollow Knight."))
