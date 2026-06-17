import argparse
import json
import sqlite3
from pathlib import Path

from langchain_core.documents import Document
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
from src.data_pipeline.steam_store import DEFAULT_DB_PATH
from src.models.videogame import VideoGame


def load_games(database_path: str | Path = DEFAULT_DB_PATH) -> list[VideoGame]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "select data_json from steam_apps order by app_id"
        ).fetchall()

    return [VideoGame.model_validate_json(row[0]) for row in rows]


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
            "is_free": game.is_free,
            "release_date": game.release_date,
            "metacritic_score": game.metacritic_score,
            "recommendation_count": game.recommendation_count,
        },
    )


def build_ingestion_vector_store() -> QdrantVectorStore:
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


def ingest_sqlite_to_qdrant(
    database_path: str | Path = DEFAULT_DB_PATH,
    vector_store: QdrantVectorStore | None = None,
) -> list[str]:
    documents = [game_to_document(game) for game in load_games(database_path)]
    store = vector_store or build_ingestion_vector_store()
    ids = [document.id for document in documents]
    return store.add_documents(documents, ids=ids)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)

    ids = ingest_sqlite_to_qdrant(args.db)
    print(json.dumps({"ingested": len(ids), "ids": ids}, indent=2))


if __name__ == "__main__":
    main()
