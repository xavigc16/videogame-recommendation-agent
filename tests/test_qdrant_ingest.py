from src.data_pipeline.qdrant_ingest import (
    game_to_document,
    ingest_postgres_to_qdrant,
)
from src.data_pipeline.steam_store import fetch_steam_app
from tests.test_steam_store import FakeResponse, _app_payload


def test_game_to_document_builds_recommendation_document():
    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )

    document = game_to_document(game)

    assert document.id == "1091500"
    assert document.page_content == game.recommendation_text
    assert document.metadata == {
        "steam_app_id": 1091500,
        "game": "Cyberpunk 2077",
        "source": "steam_store",
        "source_url": (
            "https://store.steampowered.com/api/appdetails?"
            "appids=1091500&l=english&cc=us"
        ),
        "section": "recommendation_text",
        "type": "game",
        "developers": ["CD PROJEKT RED"],
        "publishers": ["CD PROJEKT RED"],
        "genres": ["RPG"],
        "categories": ["Single-player"],
        "platforms": ["windows"],
        "price": "$59.99",
        "release_date": "10 Dec, 2020",
        "metacritic_score": 86,
        "recommendation_count": 951000,
    }


def test_ingest_postgres_to_qdrant_uses_stable_document_ids(monkeypatch):
    from src.data_pipeline import qdrant_ingest

    class FakeVectorStore:
        def __init__(self):
            self.documents = None
            self.ids = None

        def add_documents(self, documents, ids):
            self.documents = documents
            self.ids = ids
            return ids

    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    vector_store = FakeVectorStore()
    monkeypatch.setattr(
        qdrant_ingest, "load_steam_games", lambda postgres_dsn=None: [game]
    )

    ids = ingest_postgres_to_qdrant(vector_store=vector_store)

    assert ids == [1091500]
    assert vector_store.ids == [1091500]
    assert vector_store.documents == [game_to_document(game)]


def test_ingest_postgres_to_qdrant_retries_after_qdrant_failure(monkeypatch):
    from src.data_pipeline import qdrant_ingest

    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    attempts = []
    resets = []

    class FakeVectorStore:
        def __init__(self, should_fail):
            self.should_fail = should_fail

        def add_documents(self, documents, ids):
            attempts.append(ids)
            if self.should_fail:
                raise RuntimeError("closed connection")
            return ids

    stores = [FakeVectorStore(True), FakeVectorStore(False)]
    monkeypatch.setattr(
        qdrant_ingest, "load_steam_games", lambda postgres_dsn=None: [game]
    )
    monkeypatch.setattr(qdrant_ingest, "qdrant_vector_store", lambda: stores.pop(0))
    monkeypatch.setattr(
        qdrant_ingest, "reset_qdrant_vector_store", lambda: resets.append(True)
    )

    ids = ingest_postgres_to_qdrant()

    assert ids == [1091500]
    assert attempts == [[1091500], [1091500]]
    assert resets == [True]
