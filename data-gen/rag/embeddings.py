"""Embedding backends for naive RAG.

Preferred: sentence-transformers multilingual model (CPU).
Fallback: sklearn TF-IDF character n-grams (offline, no HF download).
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Literal

import numpy as np

from rag.config import (
    EMBEDDING_MODEL_NAME,
    KB_DIR,
    PASSAGE_PREFIX,
    QUERY_PREFIX,
)

BackendName = Literal["st", "tfidf"]

META_PATH = KB_DIR / "embed_meta.json"
TFIDF_PATH = KB_DIR / "tfidf.pkl"


def try_load_sentence_transformer(model_name: str = EMBEDDING_MODEL_NAME):
    try:
        from sentence_transformers import SentenceTransformer

        print(f"Loading sentence-transformers on CPU: {model_name}")
        return SentenceTransformer(model_name, device="cpu")
    except Exception as exc:
        print(f"sentence-transformers unavailable ({exc}); will use TF-IDF fallback.")
        return None


def embed_with_st(model, texts: list[str], *, is_query: bool) -> np.ndarray:
    prefix = QUERY_PREFIX if is_query else PASSAGE_PREFIX
    name = str(getattr(model, "model_name_or_path", EMBEDDING_MODEL_NAME)).lower()
    use_prefix = "e5" in name
    batch = [((prefix + t) if use_prefix else t) for t in texts]
    vectors = model.encode(
        batch,
        batch_size=16,
        show_progress_bar=len(batch) > 8,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def fit_tfidf(texts: list[str]):
    from sklearn.feature_extraction.text import TfidfVectorizer

    # Char n-grams work reasonably for Bangla without a tokenizer.
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_features=50000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    # Convert to dense normalized rows for cosine via dot product
    dense = matrix.toarray().astype(np.float32)
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    dense = dense / norms
    return vectorizer, dense


def embed_queries_tfidf(vectorizer, texts: list[str]) -> np.ndarray:
    matrix = vectorizer.transform(texts)
    dense = matrix.toarray().astype(np.float32)
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return dense / norms


def save_meta(backend: BackendName, model_name: str | None) -> None:
    import json

    KB_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(
        json.dumps({"backend": backend, "model_name": model_name}, indent=2),
        encoding="utf-8",
    )


def load_meta() -> dict:
    import json

    if not META_PATH.exists():
        return {"backend": "st", "model_name": EMBEDDING_MODEL_NAME}
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def save_tfidf(vectorizer) -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    with TFIDF_PATH.open("wb") as f:
        pickle.dump(vectorizer, f)


def load_tfidf():
    with TFIDF_PATH.open("rb") as f:
        return pickle.load(f)
