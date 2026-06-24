from langchain_core.documents import Document

import src.retriever as retriever


def test_retrieve_recommendation_documents_reranks_hybrid_candidates(monkeypatch):
    candidates = [
        Document(page_content="first", metadata={"game": "First"}),
        Document(page_content="second", metadata={"game": "Second"}),
        Document(page_content="third", metadata={"game": "Third"}),
    ]

    class FakeStore:
        def similarity_search(self, query, k):
            assert query == "fast combat"
            assert k == 3
            return candidates

    class FakeReranker:
        def rerank(self, query, documents):
            assert query == "fast combat"
            assert documents == ["first", "second", "third"]
            return [0.1, 0.9, 0.5]

    monkeypatch.setattr(retriever, "qdrant_vector_store", FakeStore)
    monkeypatch.setattr(retriever, "recommendation_reranker", FakeReranker)
    monkeypatch.setattr(retriever, "RETRIEVER_CANDIDATE_K", 3)
    monkeypatch.setattr(retriever, "RETRIEVER_K", 2)

    documents = retriever.retrieve_recommendation_documents("fast combat")

    assert [document.page_content for document in documents] == ["second", "third"]


def test_retrieve_recommendation_documents_skips_reranker_when_empty(monkeypatch):
    class FakeStore:
        def similarity_search(self, query, k):
            return []

    monkeypatch.setattr(retriever, "qdrant_vector_store", FakeStore)
    monkeypatch.setattr(
        retriever,
        "recommendation_reranker",
        lambda: (_ for _ in ()).throw(AssertionError("reranker should not load")),
        raising=False,
    )

    assert retriever.retrieve_recommendation_documents("unknown") == []
