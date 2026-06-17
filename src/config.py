from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_URL") or None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-needed")
AGENT_MODEL = os.getenv("AGENT_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv(
    "LLM_MODEL", "gpt-4o-mini"
)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "video_game_recommendations")

DENSE_MODEL_NAME = os.getenv("DENSE_MODEL_NAME", "BAAI/bge-small-en-v1.5")
SPARSE_MODEL_NAME = os.getenv("SPARSE_MODEL_NAME", "Qdrant/bm25")
DENSE_VECTOR_NAME = os.getenv("DENSE_VECTOR_NAME", "")
SPARSE_VECTOR_NAME = os.getenv("SPARSE_VECTOR_NAME", "sparse")
CONTENT_PAYLOAD_KEY = os.getenv("CONTENT_PAYLOAD_KEY", "page_content")
METADATA_PAYLOAD_KEY = os.getenv("METADATA_PAYLOAD_KEY", "metadata")
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "5"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETRIEVED_CONTENT_MAX_CHARS = int(os.getenv("LOG_RETRIEVED_CONTENT_MAX_CHARS", "1000"))

LLM_URL = OPENAI_BASE_URL
LLM_MODEL = AGENT_MODEL
