import src.qdrant_store as qdrant_store


def test_qdrant_vector_store_is_cached(monkeypatch):
    qdrant_store.reset_qdrant_vector_store()
    calls = []

    def fake_build():
        calls.append(object())
        return calls[-1]

    monkeypatch.setattr(qdrant_store, "_build_qdrant_vector_store", fake_build)

    first = qdrant_store.qdrant_vector_store()
    second = qdrant_store.qdrant_vector_store()

    assert first is second
    assert len(calls) == 1


def test_reset_qdrant_vector_store_rebuilds_next_call(monkeypatch):
    qdrant_store.reset_qdrant_vector_store()
    calls = []

    def fake_build():
        calls.append(object())
        return calls[-1]

    monkeypatch.setattr(qdrant_store, "_build_qdrant_vector_store", fake_build)

    first = qdrant_store.qdrant_vector_store()
    qdrant_store.reset_qdrant_vector_store()
    second = qdrant_store.qdrant_vector_store()

    assert first is not second
    assert len(calls) == 2
    qdrant_store.reset_qdrant_vector_store()
