from dotenv import load_dotenv
import os

load_dotenv()

LLM_URL = os.getenv("LLM_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")