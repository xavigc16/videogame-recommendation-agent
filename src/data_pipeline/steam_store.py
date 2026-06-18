import argparse
import json
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen as default_urlopen

import psycopg

from src.config import POSTGRES_DSN
from src.models.videogame import VideoGame


STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


class SteamStoreError(RuntimeError):
    """Raised when Steam Store app details cannot be fetched or parsed."""


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def fetch_steam_app(
    app_id: int, *, timeout: int = 10, urlopen=default_urlopen
) -> VideoGame:
    query = urlencode({"appids": app_id, "l": "english", "cc": "us"})
    url = f"{STEAM_APPDETAILS_URL}?{query}"
    request = Request(
        url,
        headers={"User-Agent": "videogame-recommendation-agent/0.1"},
    )

    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    app_payload = payload.get(str(app_id))
    if not app_payload or not app_payload.get("success"):
        raise SteamStoreError(
            f"Steam Store did not return app details for app_id={app_id}"
        )

    data = app_payload.get("data") or {}
    return _normalize_app(app_id, data, url)


def save_steam_app(
    app: VideoGame,
    postgres_dsn: str | None = None,
    *,
    connect=psycopg.connect,
) -> None:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        connection.execute(
            """
            insert into steam_games (
                app_id, name, type, price, short_description, about_the_game,
                developers, publishers, genres, tags, categories, platforms,
                release_date, metacritic_score, recommendation_count, header_image,
                source_url, data_json
            )
            values (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s::jsonb
            )
            on conflict(app_id) do update set
                name = excluded.name,
                type = excluded.type,
                price = excluded.price,
                short_description = excluded.short_description,
                about_the_game = excluded.about_the_game,
                developers = excluded.developers,
                publishers = excluded.publishers,
                genres = excluded.genres,
                tags = excluded.tags,
                categories = excluded.categories,
                platforms = excluded.platforms,
                release_date = excluded.release_date,
                metacritic_score = excluded.metacritic_score,
                recommendation_count = excluded.recommendation_count,
                header_image = excluded.header_image,
                source_url = excluded.source_url,
                data_json = excluded.data_json,
                fetched_at = now()
            """,
            _game_params(app),
        )


def load_steam_games(
    postgres_dsn: str | None = None,
    *,
    connect=psycopg.connect,
) -> list[VideoGame]:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        rows = connection.execute(
            "select data_json from steam_games order by app_id"
        ).fetchall()
    return [_game_from_json(row[0]) for row in rows]


def load_steam_games_by_app_ids(
    app_ids: list[int],
    postgres_dsn: str | None = None,
    *,
    connect=psycopg.connect,
) -> list[VideoGame]:
    if not app_ids:
        return []

    with connect(_postgres_dsn(postgres_dsn)) as connection:
        rows = connection.execute(
            "select data_json from steam_games where app_id = any(%s)",
            (app_ids,),
        ).fetchall()

    games_by_id = {
        game.app_id: game for game in (_game_from_json(row[0]) for row in rows)
    }
    return [games_by_id[app_id] for app_id in app_ids if app_id in games_by_id]


def load_steam_games_by_name(
    name: str,
    postgres_dsn: str | None = None,
    *,
    connect=psycopg.connect,
) -> list[VideoGame]:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        rows = connection.execute(
            "select data_json from steam_games where lower(name) = lower(%s) order by app_id",
            (name,),
        ).fetchall()
    return [_game_from_json(row[0]) for row in rows]


def _normalize_app(app_id: int, data: dict, source_url: str) -> VideoGame:
    return VideoGame(
        app_id=app_id,
        name=data.get("name", ""),
        type=data.get("type", ""),
        price=_price(data),
        short_description=_clean_html(data.get("short_description", "")),
        about_the_game=_clean_html(data.get("about_the_game", "")),
        developers=list(data.get("developers") or []),
        publishers=list(data.get("publishers") or []),
        genres=_descriptions(data.get("genres")),
        tags=_descriptions(data.get("tags")),
        categories=_descriptions(data.get("categories")),
        platforms=[
            name for name, enabled in (data.get("platforms") or {}).items() if enabled
        ],
        release_date=(data.get("release_date") or {}).get("date"),
        metacritic_score=(data.get("metacritic") or {}).get("score"),
        recommendation_count=(data.get("recommendations") or {}).get("total"),
        header_image=data.get("header_image"),
        source_url=source_url,
    )


def _game_params(app: VideoGame) -> tuple:
    return (
        app.app_id,
        app.name,
        app.type,
        app.price,
        app.short_description,
        app.about_the_game,
        app.developers,
        app.publishers,
        app.genres,
        app.tags,
        app.categories,
        app.platforms,
        app.release_date,
        app.metacritic_score,
        app.recommendation_count,
        app.header_image,
        app.source_url,
        json.dumps(app.to_dict(), sort_keys=True),
    )


def _game_from_json(value: dict | str) -> VideoGame:
    if isinstance(value, str):
        return VideoGame.model_validate_json(value)
    return VideoGame.model_validate(value)


def _postgres_dsn(postgres_dsn: str | None) -> str:
    dsn = postgres_dsn or POSTGRES_DSN
    if not dsn:
        raise SteamStoreError("POSTGRES_DSN is not set")
    return dsn


def _price(data: dict) -> str | None:
    price = data.get("price_overview") or {}
    if price.get("final_formatted"):
        return price["final_formatted"]
    if data.get("is_free"):
        return "Free"
    return None


def _descriptions(items: list[dict] | None) -> list[str]:
    return [item["description"] for item in items or [] if item.get("description")]


def _clean_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    return " ".join(parser.parts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", type=int, nargs="?", default=1091500)
    parser.add_argument("--postgres-dsn")
    args = parser.parse_args(argv)

    app = fetch_steam_app(args.app_id)
    if args.postgres_dsn:
        save_steam_app(app, args.postgres_dsn)
    print(json.dumps(app.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
