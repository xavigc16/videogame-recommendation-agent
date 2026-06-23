import argparse
import json
import uuid
from dataclasses import asdict, dataclass

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.data_pipeline.eurogamer_reviews import find_eurogamer_review
from src.data_pipeline.review_store import (
    load_review_by_source_url,
    save_review,
)
from src.data_pipeline.steam_store import load_steam_games_by_name
from src.models.review import Review
from src.qdrant_store import qdrant_vector_store


REVIEW_POINT_NAMESPACE = uuid.UUID("e4947b70-fb7e-4c66-8cfe-74e509c8f4ec")
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


class ReviewIngestError(RuntimeError):
    """Raised when a named game review cannot be safely ingested."""


@dataclass(frozen=True)
class ReviewIngestResult:
    game: str
    publisher: str
    source_url: str
    review_id: int
    chunk_count: int


def review_to_documents(
    review: Review,
    game_name: str,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    if review.id is None:
        raise ReviewIngestError("Review must be stored before it can be indexed.")

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    ).split_text("\n\n".join(review.content))
    if not chunks:
        raise ReviewIngestError("Review content produced no chunks.")
    documents = []
    chunk_count = len(chunks)
    for chunk_index, chunk in enumerate(chunks):
        point_id = str(
            uuid.uuid5(
                REVIEW_POINT_NAMESPACE,
                f"{review.source_url}#{chunk_index}",
            )
        )
        context = [
            f"Game: {game_name}",
            f"Publisher: {review.publisher.title()}",
            f"Review: {review.title}",
        ]
        if review.subtitle:
            context.append(f"Review context: {review.subtitle}")
        context.append(f"Chunk: {chunk_index + 1} of {chunk_count}")
        documents.append(
            Document(
                id=point_id,
                page_content="\n".join(context) + f"\n\n{chunk}",
                metadata={
                    "document_type": "professional_review",
                    "review_id": review.id,
                    "steam_app_id": review.app_id,
                    "game": game_name,
                    "publisher": review.publisher,
                    "source": review.publisher,
                    "source_url": review.source_url,
                    "review_title": review.title,
                    "chunk_index": chunk_index,
                    "chunk_count": chunk_count,
                },
            )
        )
    return documents


def ingest_review(
    game_name: str,
    *,
    publisher: str = "eurogamer",
    postgres_dsn: str | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> ReviewIngestResult:
    game_name = game_name.strip()
    publisher = publisher.strip().casefold()
    if not game_name or len(game_name) > 200:
        raise ReviewIngestError("Game name must contain between 1 and 200 characters.")
    if publisher != "eurogamer":
        raise ReviewIngestError(f"Unsupported review publisher: {publisher}")

    games = load_steam_games_by_name(game_name, postgres_dsn)
    if not games:
        raise ReviewIngestError(f"Game not found in PostgreSQL: {game_name}")
    if len(games) > 1:
        raise ReviewIngestError(
            f"Multiple PostgreSQL games are named {game_name!r}; use an exact unique name."
        )
    game = games[0]

    scraped = find_eurogamer_review(game.name, game.release_date)
    previous = load_review_by_source_url(scraped.source_url, postgres_dsn)
    review = save_review(
        Review(
            app_id=game.app_id,
            publisher=scraped.publisher,
            title=scraped.title,
            subtitle=scraped.subtitle,
            rating=scraped.rating,
            rating_scale=scraped.rating_scale,
            source_url=scraped.source_url,
            content=scraped.content,
        ),
        postgres_dsn,
    )

    documents = review_to_documents(review, game.name)
    store = vector_store or qdrant_vector_store()
    ids = [str(document.id) for document in documents]
    store.add_documents(documents, ids=ids)

    if previous:
        old_ids = {
            str(document.id)
            for document in review_to_documents(previous, game.name)
        }
        stale_ids = sorted(old_ids - set(ids))
        if stale_ids:
            store.delete(ids=stale_ids)

    return ReviewIngestResult(
        game=game.name,
        publisher=review.publisher,
        source_url=review.source_url,
        review_id=review.id,
        chunk_count=len(documents),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("game_name")
    parser.add_argument("--publisher", choices=("eurogamer",), default="eurogamer")
    parser.add_argument("--postgres-dsn")
    args = parser.parse_args(argv)

    result = ingest_review(
        args.game_name,
        publisher=args.publisher,
        postgres_dsn=args.postgres_dsn,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
