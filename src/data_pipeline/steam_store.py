import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen as default_urlopen


STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
DEFAULT_DB_PATH = Path("data/steam_games.sqlite3")


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


@dataclass(frozen=True)
class SteamApp:
    app_id: int
    name: str
    type: str
    is_free: bool
    short_description: str
    about_the_game: str
    developers: list[str]
    publishers: list[str]
    genres: list[str]
    categories: list[str]
    platforms: list[str]
    release_date: str | None
    metacritic_score: int | None
    recommendation_count: int | None
    header_image: str | None
    source_url: str

    @property
    def recommendation_text(self) -> str:
        parts = [f"{self.name} is a {self.type}"]
        if self.developers:
            parts.append(f"from {', '.join(self.developers)}")

        text = " ".join(parts) + "."
        if self.genres:
            text += f" Genres: {', '.join(self.genres)}."
        if self.categories:
            text += f" Categories: {', '.join(self.categories)}."
        if self.short_description:
            text += f" {self.short_description}"
        if self.about_the_game:
            text += f" {self.about_the_game}"
        return text

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_steam_app(app_id: int, *, timeout: int = 10, urlopen=default_urlopen) -> SteamApp:
    query = urlencode({"appids": app_id})
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


def save_steam_app(app: SteamApp, database_path: str | Path = DEFAULT_DB_PATH) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            create table if not exists steam_apps (
                app_id integer primary key,
                name text not null,
                data_json text not null,
                recommendation_text text not null,
                fetched_at text not null default current_timestamp
            )
            """
        )
        connection.execute(
            """
            insert into steam_apps (app_id, name, data_json, recommendation_text)
            values (?, ?, ?, ?)
            on conflict(app_id) do update set
                name = excluded.name,
                data_json = excluded.data_json,
                recommendation_text = excluded.recommendation_text,
                fetched_at = current_timestamp
            """,
            (
                app.app_id,
                app.name,
                json.dumps(app.to_dict(), sort_keys=True),
                app.recommendation_text,
            ),
        )


def _normalize_app(app_id: int, data: dict, source_url: str) -> SteamApp:
    return SteamApp(
        app_id=app_id,
        name=data.get("name", ""),
        type=data.get("type", ""),
        is_free=bool(data.get("is_free", False)),
        short_description=_clean_html(data.get("short_description", "")),
        about_the_game=_clean_html(data.get("about_the_game", "")),
        developers=list(data.get("developers") or []),
        publishers=list(data.get("publishers") or []),
        genres=_descriptions(data.get("genres")),
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


def _descriptions(items: list[dict] | None) -> list[str]:
    return [item["description"] for item in items or [] if item.get("description")]


def _clean_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    return " ".join(parser.parts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", type=int, nargs="?", default=1091500)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args(argv)

    app = fetch_steam_app(args.app_id)
    if args.db:
        save_steam_app(app, args.db)
    print(json.dumps(app.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
