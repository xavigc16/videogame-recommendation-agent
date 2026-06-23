import logging

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from src.config import (
    LOG_RETRIEVED_CONTENT_MAX_CHARS,
    RETRIEVER_K,
)
from src.qdrant_store import qdrant_vector_store

logger = logging.getLogger(__name__)


def build_recommendation_retriever(k: int = RETRIEVER_K) -> VectorStoreRetriever:
    """Return a LangChain retriever over the game recommendation collection."""
    logger.info("Building Qdrant recommendation retriever (k=%s)", k)
    return qdrant_vector_store().as_retriever(search_kwargs={"k": k})


def _truncate_content(content: str) -> str:
    max_chars = max(LOG_RETRIEVED_CONTENT_MAX_CHARS, 0)
    if len(content) <= max_chars:
        return content

    return f"{content[:max_chars]}... [truncated]"


def log_retrieved_documents(documents: list[Document]) -> None:
    """Log retrieved Qdrant documents without changing the tool response."""
    logger.debug("Qdrant returned %s recommendation evidence fragments", len(documents))
    for index, document in enumerate(documents, start=1):
        metadata = document.metadata
        logger.debug(
            "Qdrant fragment %s metadata: game=%r source=%r title=%r",
            index,
            metadata.get("game") or metadata.get("game_name"),
            metadata.get("source"),
            metadata.get("title"),
        )
        logger.debug(
            "Qdrant fragment %s content: %s",
            index,
            _truncate_content(document.page_content),
        )


def format_recommendation_documents(documents: list[Document]) -> str:
    """Format retrieved recommendation evidence for an LLM tool response."""
    if not documents:
        return "No relevant recommendation evidence was found in the Qdrant collection."

    formatted_chunks = []
    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("source") or document.metadata.get("title") or "unknown source"
        game = document.metadata.get("game") or document.metadata.get("game_name")
        heading = f"[{index}]"
        if game:
            heading += f" {game}"
        heading += f" ({source})"
        formatted_chunks.append(f"{heading}\n{document.page_content}")

    return "\n\n".join(formatted_chunks)
