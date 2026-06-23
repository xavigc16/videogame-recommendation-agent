import logging
from functools import lru_cache

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode

from src.config import (
    CONTENT_PAYLOAD_KEY,
    DENSE_MODEL_NAME,
    DENSE_VECTOR_NAME,
    METADATA_PAYLOAD_KEY,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
    QDRANT_URL,
    SPARSE_MODEL_NAME,
    SPARSE_VECTOR_NAME,
)

logger = logging.getLogger(__name__)


def _build_qdrant_vector_store() -> QdrantVectorStore:
    settings = (
        ("QDRANT_URL", QDRANT_URL),
        ("QDRANT_COLLECTION_NAME", QDRANT_COLLECTION_NAME),
        ("DENSE_MODEL_NAME", DENSE_MODEL_NAME),
        ("SPARSE_MODEL_NAME", SPARSE_MODEL_NAME),
        ("DENSE_VECTOR_NAME", DENSE_VECTOR_NAME),
        ("SPARSE_VECTOR_NAME", SPARSE_VECTOR_NAME),
        ("CONTENT_PAYLOAD_KEY", CONTENT_PAYLOAD_KEY),
        ("METADATA_PAYLOAD_KEY", METADATA_PAYLOAD_KEY),
    )
    missing = [name for name, value in settings if not value]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing required Qdrant environment values: {names}")

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


@lru_cache(maxsize=1)
def qdrant_vector_store() -> QdrantVectorStore:
    return _build_qdrant_vector_store()


def reset_qdrant_vector_store() -> None:
    qdrant_vector_store.cache_clear()
