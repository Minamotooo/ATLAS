"""
Cosine-similarity retriever over the ingested documents KB.

Works across Mathematics, Physics, and Chemistry (Bangla + English + LaTeX).
Subject is a soft signal only — never a hard filter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

_RAG_DIR = Path(__file__).resolve().parent
_DATA_GEN = _RAG_DIR.parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

from rag.config import (  # noqa: E402
    EMBEDDING_MODEL_NAME,
    EMBEDDINGS_PATH,
    ITEMS_PATH,
    MCQ_MATCH_BOOST,
    SUBJECT_ALIASES,
    SUBJECT_MATCH_BOOST,
    TOP_K,
)
from rag.embeddings import (  # noqa: E402
    embed_queries_tfidf,
    embed_with_st,
    load_meta,
    load_tfidf,
    try_load_sentence_transformer,
)


def normalize_subject(subject: Any) -> Optional[str]:
    """Map free-text subject labels to Mathematics / Physics / Chemistry."""
    if subject is None:
        return None
    raw = str(subject).strip()
    if not raw:
        return None
    key = raw.casefold()
    if key in SUBJECT_ALIASES:
        return SUBJECT_ALIASES[key]
    for alias, canonical in SUBJECT_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    # Title-case passthrough for already-canonical values
    titled = raw[:1].upper() + raw[1:]
    if titled in {"Mathematics", "Physics", "Chemistry"}:
        return titled
    return raw


def _format_hit_for_prompt(item: dict) -> str:
    """Compact reference block injected into the generator prompt."""
    qtype = str(item.get("question_type") or "").strip()
    lines = [
        f"[ref:{item.get('item_id')}]",
        f"type={qtype} | subject={item.get('subject')} | "
        f"source={item.get('source_tag')} | page={item.get('page_number')}",
    ]
    if qtype.casefold() == "written":
        lines.append(
            "NOTE: Written KB item — use facts/notation only. "
            "Your OUTPUT must still be a 4-option MCQ (never Written)."
        )
    lines.append(f"Q: {(item.get('question_text') or '').strip()}")
    options = item.get("options")
    if isinstance(options, dict):
        filled = {k: v for k, v in options.items() if v is not None and str(v).strip()}
        if filled:
            opt_lines = [f"  {k}) {v}" for k, v in sorted(filled.items())]
            lines.append("Options:\n" + "\n".join(opt_lines))
    answer = item.get("answer")
    if answer is not None and str(answer).strip():
        lines.append(f"Correct: {answer}")
    solution = item.get("solution")
    if solution is not None and str(solution).strip():
        sol = str(solution).strip()
        # Keep Written solutions shorter — facts only for MCQ generation.
        limit = 600 if qtype.casefold() == "written" else 1200
        if len(sol) > limit:
            sol = sol[:limit] + "..."
        lines.append(f"Solution:\n{sol}")
    return "\n".join(lines)


class Retriever:
    def __init__(
        self,
        items_path: Path = ITEMS_PATH,
        embeddings_path: Path = EMBEDDINGS_PATH,
        model_name: str = EMBEDDING_MODEL_NAME,
    ) -> None:
        if not items_path.exists() or not embeddings_path.exists():
            raise FileNotFoundError(
                f"KB not found. Run ingest first:\n"
                f"  python -m rag.ingest\n"
                f"Expected:\n  {items_path}\n  {embeddings_path}"
            )

        self.items: list[dict] = []
        with items_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.items.append(json.loads(line))

        self.embeddings = np.load(embeddings_path).astype(np.float32)
        if self.embeddings.ndim != 2 or self.embeddings.shape[0] != len(self.items):
            raise ValueError(
                f"KB mismatch: {len(self.items)} items vs embeddings {self.embeddings.shape}"
            )

        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        self.embeddings = self.embeddings / norms

        meta = load_meta()
        self.backend = meta.get("backend", "st")
        self.model = None
        self.vectorizer = None

        if self.backend == "tfidf":
            self.vectorizer = load_tfidf()
            print("Retriever backend: TF-IDF")
        else:
            name = meta.get("model_name") or model_name
            self.model = try_load_sentence_transformer(name)
            if self.model is None:
                raise RuntimeError(
                    "KB was built with sentence-transformers but the model cannot be loaded. "
                    "Re-run: set RAG_FORCE_TFIDF=1 && python -m rag.ingest"
                )
            print(f"Retriever backend: sentence-transformers ({name})")

        self._cache: dict[str, list[dict]] = {}

    def embed_query(self, query: str) -> np.ndarray:
        if self.backend == "tfidf":
            return embed_queries_tfidf(self.vectorizer, [query])[0]
        return embed_with_st(self.model, [query], is_query=True)[0]

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        subject: str | None = None,
    ) -> list[dict]:
        cache_key = f"{top_k}::{normalize_subject(subject)}::{query}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        q = self.embed_query(query)
        scores = self.embeddings @ q

        wanted = normalize_subject(subject)
        for i, item in enumerate(self.items):
            if wanted:
                item_subj = normalize_subject(item.get("subject"))
                if item_subj and item_subj == wanted:
                    scores[i] = float(scores[i]) + SUBJECT_MATCH_BOOST
            qtype = str(item.get("question_type") or "").casefold()
            if qtype == "mcq":
                scores[i] = float(scores[i]) + MCQ_MATCH_BOOST

        k = min(top_k, len(self.items))
        idx = np.argpartition(-scores, kth=k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]

        hits: list[dict] = []
        for i in idx:
            item = dict(self.items[int(i)])
            item["score"] = float(scores[int(i)])
            item["prompt_block"] = _format_hit_for_prompt(item)
            hits.append(item)

        self._cache[cache_key] = hits
        return hits

    @staticmethod
    def build_query(
        topic_label: str,
        skill_full: str,
        bloom: str | None = None,
        subject: str | None = None,
    ) -> str:
        parts = []
        if subject:
            parts.append(f"Subject: {subject}")
            # Bangla subject hints help TF-IDF / char n-grams when Bangla KB dominates.
            canon = normalize_subject(subject)
            if canon == "Mathematics":
                parts.append("গণিত")
            elif canon == "Physics":
                parts.append("পদার্থবিজ্ঞান")
            elif canon == "Chemistry":
                parts.append("রসায়ন")
        parts.append(f"Topic: {topic_label}")
        parts.append(f"Skill: {skill_full}")
        if bloom:
            parts.append(f"Bloom: {bloom}")
        parts.append("BUET university admission MCQ Bangla exam style")
        return " | ".join(parts)

    def retrieve_for_tuple(
        self,
        topic_label: str,
        skill_full: str,
        bloom: str | None = None,
        subject: str | None = None,
        top_k: int = TOP_K,
    ) -> list[dict]:
        return self.retrieve(
            self.build_query(topic_label, skill_full, bloom, subject),
            top_k=top_k,
            subject=subject,
        )


def main() -> None:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    r = Retriever()
    for subject, skill in [
        ("Chemistry", "Lab safety and hazard symbols"),
        ("Mathematics", "Multiply whole numbers"),
        ("Physics", "Electromagnetic spectrum applications"),
    ]:
        q = Retriever.build_query("Sample topic", skill, "Apply", subject)
        print("=" * 60)
        print("Query:", q)
        for hit in r.retrieve(q, top_k=2, subject=subject):
            print(
                f"  score={hit['score']:.4f} subject={hit.get('subject')} "
                f"id={hit['item_id']}"
            )
            print(" ", (hit.get("question_text") or "")[:120])


if __name__ == "__main__":
    main()
