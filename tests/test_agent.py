import json
import logging
from types import SimpleNamespace

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.agent import (
    RECOMMENDATION_PROMPT,
    ROUTER_PROMPT,
    RouteDecision,
    ask_agent,
    ask_agent_with_payload,
    game_details_node,
    out_of_scope_node,
    recommendation_node,
    route_by_intent,
    route_intent,
)
from src.data_pipeline.steam_store import fetch_steam_app
from src.retriever import format_recommendation_documents
from src.tools import get_game_details, search_game_recommendations, tools
from tests.test_steam_store import FakeResponse, _app_payload


def test_agent_routes_recommendations_and_game_details():
    assert "out_of_scope" in ROUTER_PROMPT
    assert "game_details" in ROUTER_PROMPT
    assert "recommendation" in ROUTER_PROMPT
    assert "retrieved recommendation evidence" in RECOMMENDATION_PROMPT
    assert tools == [search_game_recommendations, get_game_details]


def test_recommendation_formatter_includes_game_and_source():
    result = format_recommendation_documents(
        [
            Document(
                page_content="Tight platforming and exploration.",
                metadata={"game": "Hollow Knight", "source": "sample"},
            )
        ]
    )

    assert "[1] Hollow Knight (sample)" in result
    assert "Tight platforming and exploration." in result


def test_route_intent_records_router_decision(caplog, monkeypatch):
    import src.agent as agent_module

    monkeypatch.setattr(
        agent_module,
        "_classify_intent",
        lambda query: RouteDecision(
            intent="game_details",
            game_name="Hades",
            query=query,
        ),
    )

    with caplog.at_level(logging.INFO, logger="src.agent"):
        result = route_intent({"messages": [HumanMessage(content="Tell me about Hades")]})

    assert result == {
        "intent": "game_details",
        "query": "Tell me about Hades",
        "game_name": "Hades",
    }
    assert "Agent routed intent: game_details" in caplog.text


def test_route_by_intent_selects_answer_node():
    assert route_by_intent({"intent": "out_of_scope"}) == "out_of_scope_node"
    assert route_by_intent({"intent": "game_details"}) == "game_details_node"
    assert route_by_intent({"intent": "recommendation"}) == "recommendation_node"


def test_retrieved_documents_are_logged_with_truncated_content(caplog, monkeypatch):
    import src.retriever as retriever

    monkeypatch.setattr(retriever, "LOG_RETRIEVED_CONTENT_MAX_CHARS", 12)
    documents = [
        Document(
            page_content="Strong combat, sharp pacing, and memorable bosses.",
            metadata={"game": "Hades", "source": "sample-db", "title": "Hades"},
        )
    ]

    with caplog.at_level(logging.DEBUG, logger="src.retriever"):
        retriever.log_retrieved_documents(documents)

    assert "Qdrant returned 1 recommendation evidence fragments" in caplog.text
    assert "game='Hades'" in caplog.text
    assert "source='sample-db'" in caplog.text
    assert "Strong comba... [truncated]" in caplog.text
    assert "memorable bosses" not in caplog.text


def test_search_game_recommendations_logs_query_and_result_count(caplog, monkeypatch):
    import src.tools as tools_module

    documents = [
        Document(
            page_content="Players praise the combat and progression.",
            metadata={"game": "Hades", "source": "sample-db"},
        )
    ]

    class FakeRetriever:
        search_kwargs = {"k": 1}

        def invoke(self, query):
            assert query == "games like Hades"
            return documents

    monkeypatch.setattr(tools_module, "_recommendation_retriever", lambda: FakeRetriever())

    with caplog.at_level(logging.DEBUG):
        result = tools_module.search_game_recommendations.invoke({"query": "games like Hades"})

    assert "Searching Qdrant recommendation evidence (k=1)" in caplog.text
    assert "Qdrant retrieval query: games like Hades" in caplog.text
    assert "Retrieved 1 recommendation evidence fragments from Qdrant" in caplog.text
    assert "Players praise the combat and progression." in result


def test_search_game_recommendations_retries_after_qdrant_failure(monkeypatch):
    import src.tools as tools_module

    documents = [
        Document(
            page_content="Fast runs and strong build variety.",
            metadata={"game": "Hades", "source": "sample-db"},
        )
    ]
    attempts = []
    resets = []

    class FakeRetriever:
        search_kwargs = {"k": 1}

        def invoke(self, query):
            assert query == "games like Hades"
            attempts.append(query)
            if len(attempts) == 1:
                raise RuntimeError("closed connection")
            return documents

    monkeypatch.setattr(tools_module, "_recommendation_retriever", FakeRetriever)
    monkeypatch.setattr(
        tools_module, "reset_qdrant_vector_store", lambda: resets.append(True)
    )

    result = tools_module.search_game_recommendations.invoke({"query": "games like Hades"})

    assert len(attempts) == 2
    assert resets == [True]
    assert "Fast runs and strong build variety." in result


def test_get_game_details_returns_frontend_payload(monkeypatch):
    import src.tools as tools_module

    monkeypatch.setattr(
        tools_module, "load_steam_games_by_name", lambda name: [_cyberpunk_game()]
    )

    result = json.loads(get_game_details.invoke({"game_name": "Cyberpunk 2077"}))

    assert result["status"] == "found"
    assert result["message"] == "Found Cyberpunk 2077."
    assert result["frontend_payload"]["name"] == "Cyberpunk 2077"
    assert result["frontend_payload"]["app_id"] == 1091500


def test_get_game_details_returns_not_found(monkeypatch):
    import src.tools as tools_module

    monkeypatch.setattr(tools_module, "load_steam_games_by_name", lambda name: [])

    result = json.loads(get_game_details.invoke({"game_name": "Missing Game"}))

    assert result == {
        "status": "not_found",
        "message": "Missing Game not found.",
        "frontend_payload": None,
        "choices": [],
    }


def test_get_game_details_returns_ambiguous_choices(monkeypatch):
    import src.tools as tools_module

    cyberpunk = _cyberpunk_game()
    other = cyberpunk.model_copy(update={"app_id": 1, "name": "Cyberpunk 2077"})
    monkeypatch.setattr(
        tools_module, "load_steam_games_by_name", lambda name: [other, cyberpunk]
    )

    result = json.loads(get_game_details.invoke({"game_name": "Cyberpunk 2077"}))

    assert result == {
        "status": "ambiguous",
        "message": "Multiple games named Cyberpunk 2077 were found. Ask the user which one they mean.",
        "frontend_payload": None,
        "choices": [
            {"app_id": 1, "name": "Cyberpunk 2077"},
            {"app_id": 1091500, "name": "Cyberpunk 2077"},
        ],
    }


def test_out_of_scope_node_redirects_without_payload():
    result = out_of_scope_node({"messages": [HumanMessage(content="What is Python?")]})

    assert result["frontend_payload"] is None
    assert "only answer video game" in result["messages"][0].content


def test_game_details_node_returns_answer_and_payload(monkeypatch):
    import src.agent as agent_module

    payload = {
        "app_id": 1091500,
        "name": "Cyberpunk 2077",
        "type": "game",
        "short_description": "Open-world RPG.",
    }

    monkeypatch.setattr(
        agent_module,
        "get_game_details",
        SimpleNamespace(
            invoke=lambda args: json.dumps(
                {
                    "status": "found",
                    "message": "Found Cyberpunk 2077.",
                    "frontend_payload": payload,
                    "choices": [],
                }
            )
        ),
    )

    result = game_details_node(
        {
            "messages": [HumanMessage(content="Tell me about Cyberpunk 2077")],
            "game_name": "Cyberpunk 2077",
        }
    )

    assert result["frontend_payload"] == payload
    assert result["messages"][0].content == "Found Cyberpunk 2077."


def test_recommendation_node_uses_rag_evidence(monkeypatch):
    import src.agent as agent_module

    monkeypatch.setattr(
        agent_module,
        "search_game_recommendations",
        SimpleNamespace(invoke=lambda args: "Hades evidence"),
    )
    monkeypatch.setattr(
        agent_module,
        "_answer_recommendation",
        lambda query, evidence: f"{query} -> {evidence}",
    )

    result = recommendation_node(
        {"messages": [HumanMessage(content="Recommend games like Hades")]}
    )

    assert result["frontend_payload"] is None
    assert result["messages"][0].content == "Recommend games like Hades -> Hades evidence"


def test_ask_agent_with_payload_returns_answer_and_latest_frontend_payload(monkeypatch):
    import src.agent as agent_module

    payload = {"app_id": 1091500, "name": "Cyberpunk 2077"}

    monkeypatch.setattr(
        agent_module,
        "agent",
        SimpleNamespace(
            invoke=lambda state: {
                "frontend_payload": payload,
                "messages": [
                    AIMessage(content="Cyberpunk 2077 is an open-world RPG."),
                ],
            }
        ),
    )

    result = ask_agent_with_payload("Tell me about Cyberpunk 2077")

    assert result == {
        "answer": "Cyberpunk 2077 is an open-world RPG.",
        "frontend_payload": payload,
    }


def test_ask_agent_keeps_string_response(monkeypatch):
    import src.agent as agent_module

    monkeypatch.setattr(
        agent_module,
        "agent",
        SimpleNamespace(
            invoke=lambda state: {"messages": [AIMessage(content="Play Hades.")]}
        ),
    )

    assert ask_agent("Recommend a game") == "Play Hades."


def _cyberpunk_game():
    return fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
