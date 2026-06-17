from src.data_pipeline.qdrant_ingest import (
    game_to_document,
    ingest_sqlite_to_qdrant,
)
from src.data_pipeline.steam_store import fetch_steam_app, save_steam_app
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
        "is_free": False,
        "release_date": "10 Dec, 2020",
        "metacritic_score": 86,
        "recommendation_count": 951000,
    }


def test_ingest_sqlite_to_qdrant_uses_stable_document_ids(tmp_path):
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
    db_path = tmp_path / "games.sqlite3"
    save_steam_app(game, db_path)
    vector_store = FakeVectorStore()

    ids = ingest_sqlite_to_qdrant(db_path, vector_store)

    assert ids == ["1091500"]
    assert vector_store.ids == ["1091500"]
    assert vector_store.documents == [game_to_document(game)]
