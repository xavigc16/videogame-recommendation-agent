import pytest

from src.data_pipeline.eurogamer_reviews import (
    ReviewDiscoveryError,
    _fetch,
    _matches_game,
    _review_urls,
    find_eurogamer_review,
)


def test_find_eurogamer_review_uses_release_year_and_parses_article():
    review_url = "https://www.eurogamer.net/hades-review-a-divine-roguelike"
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>{review_url}</loc></url>
      <url><loc>https://www.eurogamer.net/hades-preview</loc></url>
    </urlset>
    """
    article = """
    <html><body><article>
      <h1>Hades review - a divine roguelike</h1>
      <h2>Supergiant escapes the underworld in style.</h2>
      <div class="review_rating" data-value="5"></div>
      <p>This first substantial paragraph explains the combat, pacing, and repeated escape attempts.</p>
      <p>This second substantial paragraph describes the characters, atmosphere, and progression systems.</p>
    </article></body></html>
    """
    responses = {
        "https://www.eurogamer.net/sitemap-2020.xml": sitemap,
        review_url: article,
    }
    requested_urls = []

    def urlopen(request, timeout):
        requested_urls.append(request.full_url)
        return FakeResponse(responses.get(request.full_url, "<urlset />"))

    review = find_eurogamer_review(
        "Hades",
        "Sep 17, 2020",
        urlopen=urlopen,
    )

    assert review.publisher == "eurogamer"
    assert review.title == "Hades review - a divine roguelike"
    assert review.rating == 5
    assert review.rating_scale == 5
    assert review.source_url == review_url
    assert len(review.content) == 2
    assert requested_urls[0] == "https://www.eurogamer.net/sitemap-2020.xml"


def test_fetch_rejects_oversized_external_content():
    def urlopen(request, timeout):
        return FakeResponse("x" * 5_000_001)

    with pytest.raises(ReviewDiscoveryError, match="too large"):
        _fetch(
            "https://www.eurogamer.net/sitemap-2020.xml",
            timeout=15,
            urlopen=urlopen,
        )


def test_game_matching_uses_whole_tokens_and_keeps_numbers():
    sitemap = b"""<urlset>
      <url><loc>https://www.eurogamer.net/mario-tennis-aces-review-a-frustrating-return</loc></url>
    </urlset>"""

    assert _review_urls(sitemap, "Rust") == []
    assert not _matches_game(
        "Mario Tennis Aces review - a frustrating return",
        "Rust",
    )
    assert not _matches_game(
        "Counter-Strike: Global Offensive review",
        "Counter-Strike 2",
    )
    assert not _matches_game(
        "Where's our Baldur's Gate 3 review",
        "Baldur's Gate 3",
    )
    assert _matches_game("Counter-Strike 2 review", "Counter-Strike 2")


class FakeResponse:
    def __init__(self, body):
        self.body = body.encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]
