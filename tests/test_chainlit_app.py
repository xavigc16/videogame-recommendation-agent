from types import SimpleNamespace

import chainlit_app
from chainlit_app import _game_card_elements, _game_card_markdown


def test_game_card_markdown_shows_decision_signals_only():
    payload = {
        "app_id": 1091500,
        "name": "Cyberpunk 2077",
        "short_description": "Open-world RPG.",
        "about_the_game": "Long store copy.",
        "developers": ["CD PROJEKT RED"],
        "publishers": ["CD PROJEKT RED"],
        "genres": ["RPG"],
        "tags": ["Open World", "Cyberpunk", "Story Rich"],
        "platforms": ["windows", "linux"],
        "price": "$59.99",
        "release_date": "10 Dec, 2020",
        "metacritic_score": 86,
        "source_url": "https://store.steampowered.com/app/1091500",
    }

    card = _game_card_markdown(payload)

    assert "### Cyberpunk 2077" in card
    assert "Open-world RPG." in card
    assert "**Genres:** RPG" in card
    assert "**Tags:** Open World, Cyberpunk, Story Rich" in card
    assert "**Platforms:** Windows, Linux" in card
    assert "Price: $59.99" in card
    assert "Metacritic: 86" in card
    assert "Released: 10 Dec, 2020" in card
    assert "[Store page](https://store.steampowered.com/app/1091500)" in card
    assert "app_id" not in card
    assert "Long store copy." not in card
    assert "CD PROJEKT RED" not in card


def test_game_card_elements_use_header_image(monkeypatch):
    monkeypatch.setattr(
        chainlit_app.cl,
        "Image",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    elements = _game_card_elements(
        {
            "name": "Cyberpunk 2077",
            "header_image": "https://example.test/header.jpg",
        }
    )

    assert len(elements) == 1
    assert elements[0].url == "https://example.test/header.jpg"
    assert elements[0].name == "Cyberpunk 2077 cover"
