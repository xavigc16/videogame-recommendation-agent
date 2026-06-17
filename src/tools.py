import logging

from langchain.tools import tool

from src.qdrant_store import reset_qdrant_vector_store
from src.retriever import (
    build_recommendation_retriever,
    format_recommendation_documents,
    log_retrieved_documents,
)

logger = logging.getLogger(__name__)


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
    retriever = _recommendation_retriever()
    search_kwargs = getattr(retriever, "search_kwargs", {})
    logger.info("Searching Qdrant recommendation evidence (k=%s)", search_kwargs.get("k"))
    logger.debug("Qdrant retrieval query: %s", query)
    try:
        documents = retriever.invoke(query)
    except Exception:
        logger.warning(
            "Qdrant recommendation retrieval failed; reconnecting and retrying",
            exc_info=True,
        )
        reset_qdrant_vector_store()
        try:
            documents = _recommendation_retriever().invoke(query)
        except Exception:
            logger.exception("Qdrant recommendation retrieval failed")
            raise

    logger.info("Retrieved %s recommendation evidence fragments from Qdrant", len(documents))
    log_retrieved_documents(documents)
    return format_recommendation_documents(documents)


tools = [search_game_recommendations]
