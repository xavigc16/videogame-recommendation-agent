from langchain_core.documents import Document

from src.agent import SYSTEM_PROMPT
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
