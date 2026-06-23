import json

from src.models.review import Review
from src.data_pipeline.review_store import (
    load_review_by_id,
    load_reviews_by_app_id,
    save_review,
)


def test_save_review_upserts_by_source_url_and_returns_id():
    connection = FakeConnection(rows=[(7,)])
    review = _review()

    saved = save_review(
        review,
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )

    sql, params = connection.statements[0]
    assert "on conflict (source_url) do update" in sql
    assert "language" not in sql
    assert params[1] == "eurogamer"
    assert json.loads(params[7]) == review.content
    assert saved.id == 7


def test_load_reviews_by_game_and_review_id():
    row = (
        7,
        367520,
        "eurogamer",
        "Hollow Knight review",
        "A deep kingdom",
        4,
        5,
        "https://www.eurogamer.net/hollow-knight-review",
        ["First paragraph", "Second paragraph"],
    )
    connection = FakeConnection(rows=[row])

    by_game = load_reviews_by_app_id(
        367520,
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )
    by_id = load_review_by_id(
        7,
        "postgresql://example/test",
        connect=lambda dsn: connection,
    )

    assert by_game == [by_id]
    assert by_id == _review().model_copy(update={"id": 7})
    assert "language" not in by_id.model_dump()


def _review() -> Review:
    return Review(
        app_id=367520,
        publisher="eurogamer",
        title="Hollow Knight review",
        subtitle="A deep kingdom",
        rating=4,
        rating_scale=5,
        source_url="https://www.eurogamer.net/hollow-knight-review",
        content=["First paragraph", "Second paragraph"],
    )


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.statements.append((" ".join(sql.split()), params))
        return FakeCursor(self.rows)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None
