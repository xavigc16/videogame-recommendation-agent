from pydantic import BaseModel, ConfigDict, Field


class Review(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None = None
    app_id: int
    publisher: str = Field(min_length=1)
    title: str = Field(min_length=1)
    subtitle: str | None = None
    rating: float | None = None
    rating_scale: float | None = None
    source_url: str = Field(min_length=1)
    content: list[str] = Field(min_length=1)
