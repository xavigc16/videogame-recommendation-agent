from langchain_openai import ChatOpenAI
from src.config import AGENT_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL


def get_llm():
    return ChatOpenAI(
        model=AGENT_MODEL,
        temperature=0,
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY,
    )
