import logging
from functools import lru_cache

from langchain.tools import tool

from src.retriever import build_review_retriever, format_review_documents, log_retrieved_documents

logger = logging.getLogger(__name__)


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
    retriever = _review_retriever()
    search_kwargs = getattr(retriever, "search_kwargs", {})
    logger.info("Searching Qdrant review fragments (k=%s)", search_kwargs.get("k"))
    logger.debug("Qdrant retrieval query: %s", query)
    try:
        documents = retriever.invoke(query)
    except Exception:
        logger.exception("Qdrant review retrieval failed")
        raise

    logger.info("Retrieved %s review fragments from Qdrant", len(documents))
    log_retrieved_documents(documents)
    return format_review_documents(documents)


tools = [search_game_opinions]
