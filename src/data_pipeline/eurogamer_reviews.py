import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen as default_urlopen
from xml.etree import ElementTree

from bs4 import BeautifulSoup, Tag


EUROGAMER_HOSTS = {"eurogamer.net", "www.eurogamer.net"}
EUROGAMER_SITEMAP = "https://www.eurogamer.net/sitemap-{year}.xml"
MAX_RESPONSE_BYTES = 5_000_000
MAX_CANDIDATE_URLS = 10
HEADERS = {
    "User-Agent": "videogame-recommendation-agent/0.1",
    "Accept-Language": "en-US,en;q=0.9",
}


class ReviewDiscoveryError(RuntimeError):
    """Raised when one unambiguous professional review cannot be found."""


@dataclass(frozen=True)
class ScrapedReview:
    publisher: str
    title: str
    subtitle: str | None
    rating: float | None
    rating_scale: float | None
    source_url: str
    content: list[str]


def find_eurogamer_review(
    game_name: str,
    release_date: str | None,
    *,
    timeout: int = 15,
    urlopen=default_urlopen,
) -> ScrapedReview:
    year = _release_year(release_date)
    candidate_urls = []
    for candidate_year in (year, year + 1, year - 1):
        sitemap_url = EUROGAMER_SITEMAP.format(year=candidate_year)
        sitemap = _fetch(sitemap_url, timeout=timeout, urlopen=urlopen)
        candidate_urls.extend(_review_urls(sitemap, game_name))

    candidate_urls = list(dict.fromkeys(candidate_urls))
    if len(candidate_urls) > MAX_CANDIDATE_URLS:
        raise ReviewDiscoveryError(
            f"Too many Eurogamer review candidates found for {game_name!r}."
        )

    reviews = []
    for url in candidate_urls:
        html = _fetch(url, timeout=timeout, urlopen=urlopen)
        review = _parse_review(html, url)
        if review and _matches_game(review.title, game_name):
            reviews.append(review)

    if not reviews:
        raise ReviewDiscoveryError(
            f"No Eurogamer review found for {game_name!r} near release year {year}."
        )
    if len(reviews) > 1:
        raise ReviewDiscoveryError(
            f"Multiple Eurogamer reviews found for {game_name!r}; refusing to guess."
        )
    return reviews[0]


def _fetch(url: str, *, timeout: int, urlopen) -> bytes:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in EUROGAMER_HOSTS
        or parsed.port not in (None, 443)
    ):
        raise ReviewDiscoveryError(f"Refusing unexpected Eurogamer URL: {url}")

    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=timeout) as response:
        content = response.read(MAX_RESPONSE_BYTES + 1)
    if len(content) > MAX_RESPONSE_BYTES:
        raise ReviewDiscoveryError(f"Eurogamer response is too large: {url}")
    return content


def _release_year(release_date: str | None) -> int:
    match = re.search(r"\b(?:19|20)\d{2}\b", release_date or "")
    if not match:
        raise ReviewDiscoveryError("The stored game release date has no usable year.")
    return int(match.group())


def _review_urls(sitemap: bytes, game_name: str) -> list[str]:
    terms = _meaningful_terms(game_name)
    urls = []
    for element in ElementTree.fromstring(sitemap).iter():
        if not element.tag.endswith("loc") or not element.text:
            continue
        url = element.text.strip()
        parsed = urlparse(url)
        path = parsed.path.casefold()
        path_tokens = set(re.findall(r"[a-z0-9]+", path))
        if (
            parsed.hostname in EUROGAMER_HOSTS
            and "review" in path_tokens
            and all(term in path_tokens for term in terms)
        ):
            urls.append(url)
    return urls


def _parse_review(html: bytes, url: str) -> ScrapedReview | None:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if not isinstance(article, Tag):
        return None

    title_tag = article.find("h1")
    if not isinstance(title_tag, Tag):
        return None
    title = title_tag.get_text(" ", strip=True)

    subtitle_tag = article.find("h2")
    subtitle = (
        subtitle_tag.get_text(" ", strip=True)
        if isinstance(subtitle_tag, Tag)
        else None
    )
    rating_tag = article.select_one(".review_rating[data-value]")
    rating = _rating(rating_tag.get("data-value") if rating_tag else None)
    content = [
        text
        for paragraph in article.find_all("p")
        if (text := paragraph.get_text(" ", strip=True)) and len(text) > 50
    ]
    if not content:
        return None

    return ScrapedReview(
        publisher="eurogamer",
        title=title,
        subtitle=subtitle,
        rating=rating,
        rating_scale=5 if rating is not None else None,
        source_url=url,
        content=content,
    )


def _rating(value: object) -> float | None:
    try:
        return float(str(value)) if value is not None else None
    except ValueError:
        return None


def _matches_game(title: str, game_name: str) -> bool:
    title_terms = _normalize(title).split()
    game_terms = _meaningful_terms(game_name)
    return (
        title_terms[: len(game_terms)] == game_terms
        and "review" in title_terms[len(game_terms) :]
    )


def _meaningful_terms(value: str) -> list[str]:
    terms = _normalize(value).split()
    if not terms:
        raise ReviewDiscoveryError("Game name has no searchable characters.")
    return terms


def _normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    ascii_value = ascii_value.replace("'", "")
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.casefold()))
