import logging

from langchain_core.documents import Document
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode

from src.config import (
    CONTENT_PAYLOAD_KEY,
    DENSE_MODEL_NAME,
    DENSE_VECTOR_NAME,
    LOG_RETRIEVED_CONTENT_MAX_CHARS,
    METADATA_PAYLOAD_KEY,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
    QDRANT_URL,
    RETRIEVER_K,
    SPARSE_MODEL_NAME,
    SPARSE_VECTOR_NAME,
)

logger = logging.getLogger(__name__)


def build_vector_store() -> QdrantVectorStore:
    """Connect to an existing Qdrant collection containing review chunks."""
    logger.info("Connecting to Qdrant collection '%s'", QDRANT_COLLECTION_NAME)
    dense_embeddings = FastEmbedEmbeddings(model_name=DENSE_MODEL_NAME)
    sparse_embeddings = FastEmbedSparse(model_name=SPARSE_MODEL_NAME)

    return QdrantVectorStore.from_existing_collection(
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=dense_embeddings,
        sparse_embedding=sparse_embeddings,
        retrieval_mode=RetrievalMode.HYBRID,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        vector_name=DENSE_VECTOR_NAME,
        sparse_vector_name=SPARSE_VECTOR_NAME,
        content_payload_key=CONTENT_PAYLOAD_KEY,
        metadata_payload_key=METADATA_PAYLOAD_KEY,
    )


def build_review_retriever(k: int = RETRIEVER_K) -> VectorStoreRetriever:
    """Return a LangChain retriever over the review-fragment collection."""
    logger.info("Building Qdrant review retriever (k=%s)", k)
    return build_vector_store().as_retriever(search_kwargs={"k": k})


def _truncate_content(content: str) -> str:
    max_chars = max(LOG_RETRIEVED_CONTENT_MAX_CHARS, 0)
    if len(content) <= max_chars:
        return content

    return f"{content[:max_chars]}... [truncated]"


def log_retrieved_documents(documents: list[Document]) -> None:
    """Log retrieved Qdrant documents without changing the tool response."""
    logger.debug("Qdrant returned %s review fragments", len(documents))
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


def format_review_documents(documents: list[Document]) -> str:
    """Format retrieved review chunks for an LLM tool response."""
    if not documents:
        return "No relevant review fragments were found in the Qdrant collection."

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
