from langchain_openai import ChatOpenAI
from src.config import LLM_URL, LLM_MODEL


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL, 
        temperature=0,
        base_url=LLM_URL,
        api_key="s3cr3t"
    )