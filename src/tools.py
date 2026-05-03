from functools import lru_cache

from langchain.tools import tool

from src.retriever import build_review_retriever, format_review_documents


@lru_cache(maxsize=1)
def _review_retriever():
    return build_review_retriever()


@tool
def search_game_opinions(query: str) -> str:
    """
    Search the Qdrant review-fragment database for video game opinions.

    Use this for questions about player/critic sentiment, reviews, praise,
    criticism, recommendations, or whether a specific video game is worth playing.
    Do not use this for non-video-game questions or factual questions unrelated to
    review opinions.
    """
    documents = _review_retriever().invoke(query)
    return format_review_documents(documents)


tools = [search_game_opinions]
