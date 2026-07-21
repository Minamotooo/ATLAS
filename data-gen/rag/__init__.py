"""Naive RAG helpers for admission MCQ generation from documents/*.txt."""

__all__ = ["Retriever"]


def __getattr__(name: str):
    if name == "Retriever":
        from rag.retriever import Retriever

        return Retriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
