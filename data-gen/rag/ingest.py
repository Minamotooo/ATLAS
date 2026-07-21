"""
Build a naive RAG knowledge base from bktback/documents/*.txt (and legacy *.json).

Final KB format (see documents/1-20.txt):
  - One or more JSON arrays concatenated in a single .txt file
  - Each object: question_number, question_type (MCQ|Written), subject,
    source_tag, question_text, options ({} or filled), answer, solution, page_number

Each document object becomes one retrieval unit.

Run from data-gen/:

    python -m rag.ingest
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

_RAG_DIR = Path(__file__).resolve().parent
_DATA_GEN = _RAG_DIR.parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

from rag.config import (  # noqa: E402
    DOCUMENTS_DIR,
    EMBEDDING_MODEL_NAME,
    EMBEDDINGS_PATH,
    ITEMS_PATH,
    KB_DIR,
)
from rag.embeddings import (  # noqa: E402
    embed_with_st,
    fit_tfidf,
    save_meta,
    save_tfidf,
    try_load_sentence_transformer,
)


def _options_text(options) -> str:
    if options is None or not isinstance(options, dict):
        return ""
    lines = []
    for key in sorted(options.keys()):
        val = options[key]
        if val is None:
            continue
        text = str(val).strip()
        if text:
            lines.append(f"{key}) {text}")
    return "\n".join(lines)


def build_embed_text(item: dict) -> str:
    """Flatten one KB item into a single string for embedding."""
    parts: list[str] = []
    subject = (item.get("subject") or "").strip()
    source = (item.get("source_tag") or "").strip()
    qtype = (item.get("question_type") or "").strip()
    if subject:
        parts.append(f"Subject: {subject}")
    if source:
        parts.append(f"Source: {source}")
    if qtype:
        parts.append(f"Type: {qtype}")

    qtext = (item.get("question_text") or "").strip()
    if qtext:
        parts.append(f"Question:\n{qtext}")

    opt = _options_text(item.get("options"))
    if opt:
        parts.append(f"Options:\n{opt}")

    answer = item.get("answer")
    if answer is not None and str(answer).strip():
        parts.append(f"Answer: {answer}")

    solution = item.get("solution")
    if solution is not None and str(solution).strip():
        parts.append(f"Solution:\n{str(solution).strip()}")

    return "\n\n".join(parts).strip()


def repair_json_escapes(chunk: str) -> str:
    """
    OCR/LaTeX dumps often put single backslashes in JSON strings (\\%, \\text, …).
    Turn illegal escapes into literal backslashes so json.loads can succeed.
    """
    out: list[str] = []
    i = 0
    n = len(chunk)
    in_string = False
    while i < n:
        ch = chunk[i]
        if not in_string:
            out.append(ch)
            if ch == '"':
                in_string = True
            i += 1
            continue

        if ch == '"':
            out.append(ch)
            in_string = False
            i += 1
            continue

        if ch == "\\":
            if i + 1 >= n:
                out.append("\\\\")
                i += 1
                continue
            nxt = chunk[i + 1]
            if nxt in '"\\/bfnrt':
                out.append(ch)
                out.append(nxt)
                i += 2
                continue
            if nxt == "u" and i + 5 < n and all(
                c in "0123456789abcdefABCDEF" for c in chunk[i + 2 : i + 6]
            ):
                out.append(chunk[i : i + 6])
                i += 6
                continue
            # Illegal escape (e.g. \%, \text) → keep as literal backslash
            out.append("\\\\")
            out.append(nxt)
            i += 2
            continue

        out.append(ch)
        i += 1
    return "".join(out)


def parse_json_array_chunk(chunk: str, offset: int) -> list | None:
    """Parse one array chunk; retry after repairing LaTeX-style escapes."""
    for attempt, payload in enumerate((chunk, repair_json_escapes(chunk))):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            if attempt == 0:
                continue
            print(f"  warn: skipped invalid JSON array near offset {offset}: {exc}")
            return None
        if isinstance(parsed, list):
            if attempt == 1:
                print(f"  note: repaired escapes in array near offset {offset}")
            return parsed
        print(f"  warn: skipped non-list JSON value near offset {offset}")
        return None
    return None


def extract_json_arrays(text: str) -> list[list]:
    """
    Extract one or more top-level JSON arrays from a document file.

    Final format places several arrays in one .txt file, separated by blank lines.
    Tolerates minor trailing garbage between arrays (e.g. stray `}` / `]`).
    """
    arrays: list[list] = []
    i = 0
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        if text[i] != "[":
            # Skip junk until next array start
            next_bracket = text.find("[", i)
            if next_bracket < 0:
                break
            i = next_bracket
            continue

        depth = 0
        in_string = False
        escape = False
        start = i
        j = i
        while j < n:
            ch = text[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        chunk = text[start : j + 1]
                        parsed = parse_json_array_chunk(chunk, start)
                        if parsed is not None:
                            arrays.append(parsed)
                        i = j + 1
                        break
            j += 1
        else:
            print(f"  warn: unclosed JSON array starting at offset {start}")
            break
    return arrays


def list_document_files(documents_dir: Path) -> list[Path]:
    files = sorted(
        {
            *documents_dir.glob("*.txt"),
            *documents_dir.glob("*.json"),
        }
    )
    return files


def load_document_items(documents_dir: Path = DOCUMENTS_DIR) -> list[dict]:
    if not documents_dir.is_dir():
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    files = list_document_files(documents_dir)
    if not files:
        raise FileNotFoundError(
            f"No documents found in {documents_dir} "
            "(expected *.txt and/or *.json, e.g. 1-20.txt)"
        )

    items: list[dict] = []
    for path in files:
        print(f"  reading {path.name} ...")
        text = path.read_text(encoding="utf-8")
        arrays = extract_json_arrays(text)
        if not arrays:
            print(f"  warn: no JSON arrays found in {path.name}")
            continue

        local_idx = 0
        file_count = 0
        for arr in arrays:
            for raw in arr:
                if not isinstance(raw, dict):
                    continue
                # Normalize empty Written options {} / null
                options = raw.get("options")
                if options == {} or options is None:
                    options = None

                embed_text = build_embed_text({**raw, "options": options})
                if not embed_text:
                    continue

                item_id = (
                    f"{path.stem}__p{raw.get('page_number', 'x')}"
                    f"__q{raw.get('question_number', local_idx)}__{local_idx}"
                )
                items.append(
                    {
                        "item_id": item_id,
                        "source_file": path.name,
                        "page_number": raw.get("page_number"),
                        "question_number": raw.get("question_number"),
                        "question_type": raw.get("question_type"),
                        "subject": raw.get("subject"),
                        "source_tag": raw.get("source_tag"),
                        "question_text": raw.get("question_text"),
                        "options": options,
                        "answer": raw.get("answer"),
                        "solution": raw.get("solution"),
                        "embed_text": embed_text,
                    }
                )
                local_idx += 1
                file_count += 1
        print(f"    -> {file_count} items from {len(arrays)} array(s)")
    return items


def save_kb(items: list[dict], embeddings: np.ndarray) -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    with ITEMS_PATH.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"Wrote {len(items)} items -> {ITEMS_PATH}")
    print(f"Wrote embeddings {embeddings.shape} -> {EMBEDDINGS_PATH}")


def main() -> None:
    force_tfidf = os.environ.get("RAG_FORCE_TFIDF", "").strip().lower() in {"1", "true", "yes"}
    model_name = os.environ.get("RAG_EMBED_MODEL", EMBEDDING_MODEL_NAME)

    print(f"Scanning {DOCUMENTS_DIR} ...")
    items = load_document_items()
    print(f"Loaded {len(items)} knowledge units")
    if not items:
        raise RuntimeError("No knowledge units loaded; check documents format.")
    texts = [it["embed_text"] for it in items]

    model = None if force_tfidf else try_load_sentence_transformer(model_name)
    if model is not None:
        try:
            embeddings = embed_with_st(model, texts, is_query=False)
            save_meta("st", model_name)
            print(f"Backend: sentence-transformers ({model_name})")
        except Exception as exc:
            print(f"ST embedding failed ({exc}); falling back to TF-IDF.")
            model = None

    if model is None:
        vectorizer, embeddings = fit_tfidf(texts)
        save_tfidf(vectorizer)
        save_meta("tfidf", None)
        print("Backend: TF-IDF char n-grams (offline fallback)")

    if embeddings.shape[0] != len(items):
        raise RuntimeError("Embedding count mismatch")
    save_kb(items, embeddings)
    print("Ingest complete.")


if __name__ == "__main__":
    main()
