import json
from collections.abc import Callable

import psycopg

from src.config import POSTGRES_DSN
from src.models.review import Review


Connect = Callable[..., psycopg.Connection]
REVIEW_COLUMNS = """
    id, app_id, publisher, title, subtitle, rating, rating_scale, source_url, content
"""


def save_review(
    review: Review,
    postgres_dsn: str | None = None,
    *,
    connect: Connect = psycopg.connect,
) -> Review:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        row = connection.execute(
            """
            insert into reviews (
                app_id, publisher, title, subtitle, rating, rating_scale,
                source_url, content
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            on conflict (source_url) do update set
                app_id = excluded.app_id,
                publisher = excluded.publisher,
                title = excluded.title,
                subtitle = excluded.subtitle,
                rating = excluded.rating,
                rating_scale = excluded.rating_scale,
                content = excluded.content,
                fetched_at = now()
            returning id
            """,
            (
                review.app_id,
                review.publisher,
                review.title,
                review.subtitle,
                review.rating,
                review.rating_scale,
                review.source_url,
                json.dumps(review.content),
            ),
        ).fetchone()
    return review.model_copy(update={"id": row[0]})


def load_reviews_by_app_id(
    app_id: int,
    postgres_dsn: str | None = None,
    *,
    connect: Connect = psycopg.connect,
) -> list[Review]:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        rows = connection.execute(
            f"select {REVIEW_COLUMNS} from reviews where app_id = %s order by id",
            (app_id,),
        ).fetchall()
    return [_review_from_row(row) for row in rows]


def load_review_by_id(
    review_id: int,
    postgres_dsn: str | None = None,
    *,
    connect: Connect = psycopg.connect,
) -> Review | None:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        row = connection.execute(
            f"select {REVIEW_COLUMNS} from reviews where id = %s",
            (review_id,),
        ).fetchone()
    return _review_from_row(row) if row else None


def load_review_by_source_url(
    source_url: str,
    postgres_dsn: str | None = None,
    *,
    connect: Connect = psycopg.connect,
) -> Review | None:
    with connect(_postgres_dsn(postgres_dsn)) as connection:
        row = connection.execute(
            f"select {REVIEW_COLUMNS} from reviews where source_url = %s",
            (source_url,),
        ).fetchone()
    return _review_from_row(row) if row else None


def _review_from_row(row: tuple) -> Review:
    content = json.loads(row[8]) if isinstance(row[8], str) else row[8]
    return Review(
        id=row[0],
        app_id=row[1],
        publisher=row[2],
        title=row[3],
        subtitle=row[4],
        rating=row[5],
        rating_scale=row[6],
        source_url=row[7],
        content=content,
    )


def _postgres_dsn(postgres_dsn: str | None) -> str:
    dsn = postgres_dsn or POSTGRES_DSN
    if not dsn:
        raise RuntimeError("POSTGRES_DSN is not set")
    return dsn
