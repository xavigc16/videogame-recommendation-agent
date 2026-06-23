from src.db import migrate as migrate_module


def test_migrate_applies_unseen_sql_files_in_order(tmp_path, monkeypatch):
    (tmp_path / "002_second.sql").write_text("select 2", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("select 1", encoding="utf-8")
    connection = FakeConnection(applied={"001_first"})
    monkeypatch.setattr(migrate_module, "MIGRATIONS_DIR", tmp_path)
    monkeypatch.setattr(migrate_module.psycopg, "connect", lambda dsn: connection)

    applied = migrate_module.migrate("postgresql://example/test")

    assert applied == ["002_second"]
    assert ("select 2", None) in connection.statements
    assert ("insert into schema_migrations (version) values (%s)", ("002_second",)) in (
        connection.statements
    )
    assert ("select 1", None) not in connection.statements


class FakeConnection:
    def __init__(self, applied=()):
        self.applied = set(applied)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        sql = sql.strip()
        self.statements.append((sql, params))
        if sql == "select version from schema_migrations":
            return FakeCursor([(version,) for version in self.applied])
        if sql == "insert into schema_migrations (version) values (%s)":
            self.applied.add(params[0])
        return FakeCursor([])


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows
