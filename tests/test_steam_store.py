import json
import sqlite3
from io import BytesIO

from src.data_pipeline.steam_store import fetch_steam_app, save_steam_app


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return BytesIO(json.dumps(self.payload).encode())

    def __exit__(self, exc_type, exc, tb):
        return False


def test_fetch_steam_app_normalizes_store_response():
    def fake_urlopen(request, timeout):
        assert "appids=1091500" in request.full_url
        assert "l=english" in request.full_url
        assert "cc=us" in request.full_url
        assert timeout == 10
        return FakeResponse(
            {
                "1091500": {
                    "success": True,
                    "data": {
                        "type": "game",
                        "name": "Cyberpunk 2077",
                        "steam_appid": 1091500,
                        "is_free": False,
                        "short_description": "Open-world RPG.",
                        "about_the_game": "<p>Become a mercenary.</p>",
                        "developers": ["CD PROJEKT RED"],
                        "publishers": ["CD PROJEKT RED"],
                        "genres": [{"description": "RPG"}],
                        "categories": [{"description": "Single-player"}],
                        "platforms": {"windows": True, "mac": False, "linux": False},
                        "release_date": {"date": "10 Dec, 2020"},
                        "metacritic": {"score": 86},
                        "recommendations": {"total": 951000},
                        "header_image": "https://example.test/header.jpg",
                    },
                }
            }
        )

    game = fetch_steam_app(1091500, urlopen=fake_urlopen)

    assert game.app_id == 1091500
    assert game.name == "Cyberpunk 2077"
    assert game.genres == ["RPG"]
    assert game.categories == ["Single-player"]
    assert game.platforms == ["windows"]
    assert game.recommendation_text == (
        "Cyberpunk 2077 is a game from CD PROJEKT RED. Genres: RPG. "
        "Categories: Single-player. Open-world RPG. Become a mercenary."
    )


def test_save_steam_app_writes_sqlite_file(tmp_path):
    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    db_path = tmp_path / "games.sqlite3"

    save_steam_app(game, db_path)

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "select app_id, name, data_json, recommendation_text from steam_apps"
        ).fetchone()

    assert row[0] == 1091500
    assert row[1] == "Cyberpunk 2077"
    assert json.loads(row[2])["genres"] == ["RPG"]
    assert row[3] == game.recommendation_text


def _app_payload():
    return {
        "1091500": {
            "success": True,
            "data": {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "is_free": False,
                "short_description": "Open-world RPG.",
                "about_the_game": "<p>Become a mercenary.</p>",
                "developers": ["CD PROJEKT RED"],
                "publishers": ["CD PROJEKT RED"],
                "genres": [{"description": "RPG"}],
                "categories": [{"description": "Single-player"}],
                "platforms": {"windows": True, "mac": False, "linux": False},
                "release_date": {"date": "10 Dec, 2020"},
                "metacritic": {"score": 86},
                "recommendations": {"total": 951000},
                "header_image": "https://example.test/header.jpg",
            },
        }
    }
