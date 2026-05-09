import logging

from langchain_core.documents import Document
from langchain_core.messages import AIMessage


def test_should_continue_logs_tool_route(caplog):
    from src.agent import should_continue

    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_game_opinions",
                "args": {"query": "Hades reviews"},
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
            metadata={"game": "Hades", "source": "IGN", "title": "Hades Review"},
        )
    ]

    with caplog.at_level(logging.DEBUG, logger="src.retriever"):
        retriever.log_retrieved_documents(documents)

    assert "Qdrant returned 1 review fragments" in caplog.text
    assert "game='Hades'" in caplog.text
    assert "source='IGN'" in caplog.text
    assert "Strong comba... [truncated]" in caplog.text
    assert "memorable bosses" not in caplog.text


def test_search_game_opinions_logs_query_and_result_count(caplog, monkeypatch):
    import src.tools as tools

    documents = [
        Document(
            page_content="Players praise the combat and progression.",
            metadata={"game": "Hades", "source": "review-db"},
        )
    ]

    class FakeRetriever:
        search_kwargs = {"k": 1}

        def invoke(self, query):
            assert query == "Hades opinion"
            return documents

    monkeypatch.setattr(tools, "_review_retriever", lambda: FakeRetriever())

    with caplog.at_level(logging.DEBUG):
        result = tools.search_game_opinions.invoke({"query": "Hades opinion"})

    assert "Searching Qdrant review fragments (k=1)" in caplog.text
    assert "Qdrant retrieval query: Hades opinion" in caplog.text
    assert "Retrieved 1 review fragments from Qdrant" in caplog.text
    assert "Players praise the combat and progression." in result
