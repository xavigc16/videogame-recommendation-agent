import argparse
import json
import logging

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore

from src.data_pipeline.steam_store import load_steam_games
from src.models.videogame import VideoGame
from src.qdrant_store import qdrant_vector_store, reset_qdrant_vector_store

logger = logging.getLogger(__name__)


def game_to_document(game: VideoGame) -> Document:
    return Document(
        id=str(game.app_id),
        page_content=game.recommendation_text,
        metadata={
            "steam_app_id": game.app_id,
            "game": game.name,
            "source": "steam_store",
            "source_url": game.source_url,
            "section": "recommendation_text",
            "type": game.type,
            "developers": game.developers,
            "publishers": game.publishers,
            "genres": game.genres,
            "categories": game.categories,
            "platforms": game.platforms,
            "price": game.price,
            "release_date": game.release_date,
            "metacritic_score": game.metacritic_score,
            "recommendation_count": game.recommendation_count,
        },
    )


def ingest_postgres_to_qdrant(
    postgres_dsn: str | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> list[str]:
    documents = [game_to_document(game) for game in load_steam_games(postgres_dsn)]
    store = vector_store or qdrant_vector_store()
    ids = [document.metadata["steam_app_id"] for document in documents]
    try:
        return store.add_documents(documents, ids=ids)
    except Exception:
        logger.warning(
            "Qdrant ingestion failed; reconnecting and retrying",
            exc_info=True,
        )
        reset_qdrant_vector_store()
        if vector_store is not None:
            raise
        try:
            return qdrant_vector_store().add_documents(documents, ids=ids)
        except Exception:
            logger.exception("Qdrant ingestion failed")
            raise


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres-dsn")
    args = parser.parse_args(argv)

    ids = ingest_postgres_to_qdrant(args.postgres_dsn)
    print(json.dumps({"ingested": len(ids), "ids": ids}, indent=2))


if __name__ == "__main__":
    main()
