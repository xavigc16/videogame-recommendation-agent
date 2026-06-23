import pytest

from src.data_pipeline.eurogamer_reviews import ScrapedReview
from src.data_pipeline import review_ingest as ingest_module
from src.models.review import Review
from src.models.videogame import VideoGame


def test_review_chunks_are_augmented_positioned_and_deterministic():
    review = Review(
        id=7,
        app_id=1145360,
        publisher="eurogamer",
        title="Hades review - a divine roguelike",
        subtitle="Escaping hell in style",
        rating=5,
        rating_scale=5,
        source_url="https://www.eurogamer.net/hades-review",
        content=[" ".join(f"word{index}" for index in range(80))],
    )

    documents = ingest_module.review_to_documents(
        review,
        "Hades",
        chunk_size=180,
        chunk_overlap=40,
    )

    assert len(documents) > 1
    assert [document.metadata["chunk_index"] for document in documents] == list(
        range(len(documents))
    )
    assert all(
        document.metadata["chunk_count"] == len(documents)
        and document.metadata["review_id"] == 7
        and document.metadata["publisher"] == "eurogamer"
        and "language" not in document.metadata
        and "creator" not in document.metadata
        for document in documents
    )
    assert documents[0].page_content.startswith(
        "Game: Hades\nPublisher: Eurogamer\nReview: Hades review - a divine roguelike"
    )
    assert f"Chunk: 1 of {len(documents)}" in documents[0].page_content
    first_chunk = documents[0].page_content.split("\n\n", 1)[1].split()
    second_chunk = documents[1].page_content.split("\n\n", 1)[1].split()
    assert set(first_chunk) & set(second_chunk)
    assert [document.id for document in documents] == [
        document.id
        for document in ingest_module.review_to_documents(
            review,
            "Hades",
            chunk_size=180,
            chunk_overlap=40,
        )
    ]


def test_review_chunking_rejects_empty_text():
    review = Review(
        id=7,
        app_id=1145360,
        publisher="eurogamer",
        title="Hades review",
        source_url="https://www.eurogamer.net/hades-review",
        content=[""],
    )

    with pytest.raises(ingest_module.ReviewIngestError, match="no chunks"):
        ingest_module.review_to_documents(review, "Hades")


def test_ingest_review_resolves_game_stores_review_and_indexes_chunks(monkeypatch):
    game = _game()
    scraped = ScrapedReview(
        publisher="eurogamer",
        title="Hades review - a divine roguelike",
        subtitle="Escaping hell in style",
        rating=5,
        rating_scale=5,
        source_url="https://www.eurogamer.net/hades-review",
        content=["A substantial review paragraph about combat and progression." * 30],
    )
    store = FakeVectorStore()
    saved_reviews = []

    monkeypatch.setattr(
        ingest_module,
        "load_steam_games_by_name",
        lambda name, dsn: [game],
    )
    monkeypatch.setattr(
        ingest_module,
        "find_eurogamer_review",
        lambda name, release_date: scraped,
    )
    monkeypatch.setattr(
        ingest_module,
        "load_review_by_source_url",
        lambda url, dsn: None,
    )

    def save(review, dsn):
        saved_reviews.append(review)
        return review.model_copy(update={"id": 7})

    monkeypatch.setattr(ingest_module, "save_review", save)

    result = ingest_module.ingest_review(
        "Hades",
        publisher="eurogamer",
        postgres_dsn="postgresql://example/test",
        vector_store=store,
    )

    assert saved_reviews[0].app_id == game.app_id
    assert saved_reviews[0].publisher == "eurogamer"
    assert result.review_id == 7
    assert result.chunk_count == len(store.documents)
    assert all(document.metadata["steam_app_id"] == game.app_id for document in store.documents)


def _game() -> VideoGame:
    return VideoGame(
        app_id=1145360,
        name="Hades",
        type="game",
        price="$24.99",
        short_description="Battle out of hell.",
        about_the_game="Defy the god of the dead.",
        developers=["Supergiant Games"],
        publishers=["Supergiant Games"],
        genres=["Action", "Indie", "RPG"],
        tags=[],
        categories=["Single-player"],
        platforms=["windows"],
        release_date="Sep 17, 2020",
        metacritic_score=93,
        recommendation_count=300000,
        header_image=None,
        source_url="https://store.steampowered.com/api/appdetails?appids=1145360",
    )


class FakeVectorStore:
    def __init__(self):
        self.documents = []
        self.ids = []
        self.deleted_ids = []

    def add_documents(self, documents, ids):
        self.documents = documents
        self.ids = ids
        return ids

    def delete(self, ids):
        self.deleted_ids.extend(ids)
