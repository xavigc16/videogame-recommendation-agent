import logging
from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder
from langchain_core.documents import Document

from src.config import (
    LOG_RETRIEVED_CONTENT_MAX_CHARS,
    RERANK_MODEL_NAME,
    RETRIEVER_CANDIDATE_K,
    RETRIEVER_K,
)
from src.qdrant_store import qdrant_vector_store

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def recommendation_reranker() -> TextCrossEncoder:
    logger.info("Loading recommendation reranker '%s'", RERANK_MODEL_NAME)
    return TextCrossEncoder(model_name=RERANK_MODEL_NAME)


def retrieve_recommendation_documents(query: str) -> list[Document]:
    """Retrieve hybrid candidates from Qdrant and rerank them for the query."""
    documents = qdrant_vector_store().similarity_search(
        query,
        k=RETRIEVER_CANDIDATE_K,
    )
    if not documents:
        return []

    scores = recommendation_reranker().rerank(
        query,
        [document.page_content for document in documents],
    )
    ranked = sorted(
        zip(scores, documents, strict=True),
        key=lambda item: item[0],
        reverse=True,
    )
    logger.info(
        "Reranked %s Qdrant candidates to %s recommendation fragments",
        len(documents),
        min(RETRIEVER_K, len(documents)),
    )
    return [document for _, document in ranked[:RETRIEVER_K]]


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
