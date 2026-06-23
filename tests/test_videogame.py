from src.models.videogame import VideoGame


def test_videogame_builds_recommendation_text():
    game = VideoGame(
        app_id=1091500,
        name="Cyberpunk 2077",
        type="game",
        price="$59.99",
        short_description="Open-world RPG.",
        about_the_game="Become a mercenary.",
        developers=["CD PROJEKT RED"],
        publishers=["CD PROJEKT RED"],
        genres=["RPG"],
        tags=["Open World", "Cyberpunk"],
        categories=["Single-player"],
        platforms=["windows"],
        release_date="10 Dec, 2020",
        metacritic_score=86,
        recommendation_count=951000,
        header_image="https://example.test/header.jpg",
        source_url="https://example.test/source",
    )

    assert game.recommendation_text == (
        "Cyberpunk 2077 is a game from CD PROJEKT RED. Genres: RPG. "
        "Categories: Single-player. Open-world RPG. Become a mercenary."
    )
    assert game.model_dump()["genres"] == ["RPG"]
