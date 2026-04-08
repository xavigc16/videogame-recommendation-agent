from dataclasses import dataclass
from langchain.tools import tool

@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str

@tool
def search_game_opinions(game_name: str) -> str:
    """
    Search the review database for opinions, critiques, and ratings about a specific video game.
    Call this tool whenever the user asks for thoughts, reviews, or opinions on a game.
    """

    # TODO: Implement actual database retrieval logic here. For now, we return a mock response.
    return f"Retrieved context: Players generally praise the world design of {game_name}, but some find the combat repetitive. Critics gave it a solid 8.5/10."

tools = [search_game_opinions]