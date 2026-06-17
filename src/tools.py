from functools import lru_cache

from langchain.tools import tool

from src.retriever import build_recommendation_retriever, format_recommendation_documents


@lru_cache(maxsize=1)
def _recommendation_retriever():
    return build_recommendation_retriever()


@tool
def search_game_recommendations(query: str) -> str:
    """
    Search the Qdrant recommendation database for video game matches.

    Use this for questions about what to play next, games similar to a title,
    genre/platform preferences, strengths and weaknesses, or whether a game fits
    the user's taste. Do not use this for non-video-game questions.
    """
    documents = _recommendation_retriever().invoke(query)
    return format_recommendation_documents(documents)


tools = [search_game_recommendations]
