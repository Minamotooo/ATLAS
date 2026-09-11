"""
One-off script: load the full parsed corpus via rag.ingest.load_document_items()
(no embeddings needed) and dump it to
Ontology/full_corpus_rebuild/parsed_items.jsonl, one JSON object per line.

Run from data-gen/:
    python _dump_parsed_items.py
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

_DATA_GEN = Path(__file__).resolve().parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

from rag.ingest import load_document_items  # noqa: E402

OUT_PATH = _DATA_GEN.parent / "Ontology" / "full_corpus_rebuild" / "parsed_items.jsonl"


def main() -> None:
    items = load_document_items()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    breakdown = Counter()
    for item in items:
        source_file = item.get("source_file") or ""
        key = source_file[:-4] if source_file.endswith(".txt") else source_file
        breakdown[key] += 1

    print(f"TOTAL_ITEMS={len(items)}")
    print(f"OUT_PATH={OUT_PATH}")
    print("BREAKDOWN:")
    for key in sorted(breakdown):
        print(f"  {key}={breakdown[key]}")


if __name__ == "__main__":
    main()
