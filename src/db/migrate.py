import argparse
from pathlib import Path

import psycopg

from src.config import POSTGRES_DSN


MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def migrate(
    postgres_dsn: str | None = None,
) -> list[str]:
    with psycopg.connect(_postgres_dsn(postgres_dsn)) as connection:
        connection.execute(
            """
            create table if not exists schema_migrations (
                version text primary key,
                applied_at timestamptz not null default now()
            )
            """
        )
        applied = {
            row[0]
            for row in connection.execute(
                "select version from schema_migrations"
            ).fetchall()
        }

        applied_now = []
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = migration.stem
            if version in applied:
                continue

            connection.execute(migration.read_text(encoding="utf-8"))
            connection.execute(
                "insert into schema_migrations (version) values (%s)",
                (version,),
            )
            applied_now.append(version)

    return applied_now


def _postgres_dsn(postgres_dsn: str | None) -> str:
    dsn = postgres_dsn or POSTGRES_DSN
    if not dsn:
        raise RuntimeError("POSTGRES_DSN is not set")
    return dsn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres-dsn")
    args = parser.parse_args(argv)

    applied = migrate(args.postgres_dsn)
    print("Applied migrations: " + ", ".join(applied) if applied else "No migrations to apply")


if __name__ == "__main__":
    main()
