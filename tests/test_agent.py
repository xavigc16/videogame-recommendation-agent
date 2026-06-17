import logging

from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from src.agent import SYSTEM_PROMPT, should_continue
from src.retriever import format_recommendation_documents
from src.tools import search_game_recommendations, tools


def test_agent_is_recommendation_focused():
    assert "video game recommendation assistant" in SYSTEM_PROMPT
    assert "search_game_recommendations" in SYSTEM_PROMPT
    assert tools == [search_game_recommendations]


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


def test_should_continue_logs_tool_route(caplog):
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_game_recommendations",
                "args": {"query": "games like Hades"},
                "id": "call_1",
            }
        ],
    )

    with caplog.at_level(logging.INFO, logger="src.agent"):
        route = should_continue({"messages": [message], "llm_calls": 1})

    assert route == "tool_node"
    assert "Agent graph routing from llm_call to tool_node" in caplog.text


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
