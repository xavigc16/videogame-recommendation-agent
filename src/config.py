from dotenv import load_dotenv
import os

load_dotenv()

HUGGING_FACE_HUB_TOKEN = os.getenv("HUGGING_FACE_HUB_TOKEN")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
if QDRANT_API_KEY in {"", "None", "none", "null"}:
    QDRANT_API_KEY = None
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "game_reviews")

DENSE_MODEL_NAME = os.getenv("DENSE_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
SPARSE_MODEL_NAME = os.getenv("SPARSE_MODEL_NAME", "Qdrant/bm25")
DENSE_VECTOR_NAME = os.getenv("DENSE_VECTOR_NAME", "dense")
SPARSE_VECTOR_NAME = os.getenv("SPARSE_VECTOR_NAME", "sparse")

CONTENT_PAYLOAD_KEY = os.getenv("CONTENT_PAYLOAD_KEY", "page-content")
METADATA_PAYLOAD_KEY = os.getenv("METADATA_PAYLOAD_KEY", "metadata")
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "5"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETRIEVED_CONTENT_MAX_CHARS = int(os.getenv("LOG_RETRIEVED_CONTENT_MAX_CHARS", "1000"))

AGENT_MODEL = os.getenv("AGENT_MODEL", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_URL = os.getenv("LLM_URL", OPENAI_BASE_URL or "")
LLM_MODEL = os.getenv("LLM_MODEL", AGENT_MODEL)
