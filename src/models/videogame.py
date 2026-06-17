from pydantic import BaseModel, ConfigDict


class VideoGame(BaseModel):
    model_config = ConfigDict(frozen=True)

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
        return self.model_dump()
