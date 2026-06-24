import json
import logging

from langchain.tools import tool

from src.data_pipeline.steam_store import load_steam_games_by_name
from src.qdrant_store import reset_qdrant_vector_store
from src.retriever import (
    format_recommendation_documents,
    log_retrieved_documents,
    retrieve_recommendation_documents,
)

logger = logging.getLogger(__name__)


@tool
def search_game_recommendations(query: str) -> str:
    """
    Search the Qdrant recommendation database for video game matches.

    Use this for questions about what to play next, games similar to a title,
    genre/platform preferences, strengths and weaknesses, or whether a game fits
    the user's taste. Do not use this for non-video-game questions.
    """
    logger.debug("Qdrant retrieval query: %s", query)
    try:
        documents = retrieve_recommendation_documents(query)
    except Exception:
        logger.warning(
            "Qdrant recommendation retrieval failed; reconnecting and retrying",
            exc_info=True,
        )
        reset_qdrant_vector_store()
        try:
            documents = retrieve_recommendation_documents(query)
        except Exception:
            logger.exception("Qdrant recommendation retrieval failed")
            raise

    logger.info("Retrieved %s recommendation evidence fragments from Qdrant", len(documents))
    log_retrieved_documents(documents)
    return format_recommendation_documents(documents)


@tool
def get_game_details(game_name: str) -> str:
    """
    Get stored PostgreSQL details for one exact game name.

    Use this when the user asks for factual information, details, metadata, or
    a frontend-ready game detail payload for a specific game. Do not use this
    for recommendations, similarity, taste fit, or comparison requests.
    """
    games = load_steam_games_by_name(game_name)
    if not games:
        result = {
            "status": "not_found",
            "message": f"{game_name} not found.",
            "frontend_payload": None,
            "choices": [],
        }
    elif len(games) > 1:
        result = {
            "status": "ambiguous",
            "message": (
                f"Multiple games named {game_name} were found. "
                "Ask the user which one they mean."
            ),
            "frontend_payload": None,
            "choices": [
                {"app_id": game.app_id, "name": game.name}
                for game in sorted(games, key=lambda game: game.app_id)
            ],
        }
    else:
        game = games[0]
        result = {
            "status": "found",
            "message": f"Found {game.name}.",
            "frontend_payload": game.to_dict(),
            "choices": [],
        }
    return json.dumps(result, sort_keys=True)


tools = [search_game_recommendations, get_game_details]
