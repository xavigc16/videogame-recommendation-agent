import json
from io import BytesIO

from src.data_pipeline.steam_store import (
    fetch_steam_app,
    load_steam_games,
    load_steam_games_by_app_ids,
    load_steam_games_by_name,
    save_steam_app,
)


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
                        "price_overview": {"final_formatted": "$59.99"},
                        "short_description": "Open-world RPG.",
                        "about_the_game": "<p>Become a mercenary.</p>",
                        "developers": ["CD PROJEKT RED"],
                        "publishers": ["CD PROJEKT RED"],
                        "genres": [{"description": "RPG"}],
                        "tags": [{"description": "Open World"}, {"description": "Cyberpunk"}],
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
    assert game.price == "$59.99"
    assert game.genres == ["RPG"]
    assert game.tags == ["Open World", "Cyberpunk"]
    assert game.categories == ["Single-player"]
    assert game.platforms == ["windows"]
    assert game.recommendation_text == (
        "Cyberpunk 2077 is a game from CD PROJEKT RED. Genres: RPG. "
        "Categories: Single-player. Open-world RPG. Become a mercenary."
    )


def test_save_steam_app_upserts_postgres_row_without_search_text():
    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    connection = FakeConnection()

    save_steam_app(
        game,
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )

    upsert_sql, params = connection.statements[0]
    stored_json = json.loads(params[-1])

    assert "recommendation_text" not in upsert_sql
    assert "is_free" not in upsert_sql
    assert params[:4] == (1091500, "Cyberpunk 2077", "game", "$59.99")
    assert stored_json["price"] == "$59.99"
    assert stored_json["tags"] == ["Open World", "Cyberpunk"]


def test_load_steam_games_reads_postgres_json_rows():
    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    connection = FakeConnection(rows=[(game.to_dict(),)])

    games = load_steam_games(
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )

    assert games == [game]


def test_load_steam_games_by_app_ids_preserves_requested_order():
    cyberpunk = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    hades = cyberpunk.model_copy(update={"app_id": 1145360, "name": "Hades"})
    connection = FakeConnection(rows=[(hades.to_dict(),), (cyberpunk.to_dict(),)])

    games = load_steam_games_by_app_ids(
        [1091500, 1145360],
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )

    assert games == [cyberpunk, hades]


def test_load_steam_games_by_name_matches_exact_name_case_insensitively():
    game = fetch_steam_app(
        1091500,
        urlopen=lambda request, timeout: FakeResponse(_app_payload()),
    )
    connection = FakeConnection(rows=[(game.to_dict(),)])

    games = load_steam_games_by_name(
        "cyberpunk 2077",
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )

    sql, params = connection.statements[0]
    assert "lower(name) = lower(%s)" in sql
    assert params == ("cyberpunk 2077",)
    assert games == [game]


def _app_payload():
    return {
        "1091500": {
            "success": True,
            "data": {
                "type": "game",
                "name": "Cyberpunk 2077",
                "steam_appid": 1091500,
                "is_free": False,
                "price_overview": {"final_formatted": "$59.99"},
                "short_description": "Open-world RPG.",
                "about_the_game": "<p>Become a mercenary.</p>",
                "developers": ["CD PROJEKT RED"],
                "publishers": ["CD PROJEKT RED"],
                "genres": [{"description": "RPG"}],
                "tags": [{"description": "Open World"}, {"description": "Cyberpunk"}],
                "categories": [{"description": "Single-player"}],
                "platforms": {"windows": True, "mac": False, "linux": False},
                "release_date": {"date": "10 Dec, 2020"},
                "metacritic": {"score": 86},
                "recommendations": {"total": 951000},
                "header_image": "https://example.test/header.jpg",
            },
        }
    }


class FakeConnection:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        return FakeCursor(self.rows)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows
