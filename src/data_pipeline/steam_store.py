import json
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen as default_urlopen


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
    args = argv if argv is not None else sys.argv[1:]
    app_id = int(args[0]) if args else 1091500
    print(json.dumps(fetch_steam_app(app_id).to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
