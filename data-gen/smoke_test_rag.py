"""
Quick end-to-end RAG smoke test (does NOT overwrite output_questions.json).

From data-gen/:
    .\\.venv\\Scripts\\Activate.ps1
    $env:OLLAMA_MODEL = "qwen2.5:3b-instruct"
    python smoke_test_rag.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from rag.retriever import Retriever
import generate_question_rag as gen

OUT = Path(__file__).resolve().parent / "output_questions_rag_test.json"


def test_retrieval() -> Retriever:
    print("=== 1) RETRIEVAL ===")
    r = Retriever()
    print(f"KB items: {len(r.items)} | backend: {r.backend}")
    hits = r.retrieve_for_tuple(
        topic_label="Laboratory Safety and Apparatus",
        skill_full="Identify common laboratory glassware and hazard symbols",
        bloom="Remember",
        subject="Chemistry",
        top_k=3,
    )
    assert hits, "No retrieval hits"
    for h in hits:
        print(
            f"  score={h['score']:.3f} subject={h.get('subject')} "
            f"type={h.get('question_type')}"
        )
        print(f"    {(h.get('question_text') or '')[:120]}")
    print("Retrieval OK\n")
    return r


def test_ollama() -> str:
    print("=== 2) OLLAMA ===")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct")
    reply = gen.ollama_chat(
        messages=[{"role": "user", "content": 'Reply with JSON only: {"ok": true}'}],
        model=model,
        temperature=0.0,
    )
    print(f"model={model}")
    print(f"raw={reply[:200]}")
    print("Ollama OK\n")
    return model


def test_generate(retriever: Retriever, model: str) -> None:
    print("=== 3) ONE-TUPLE GENERATION ===")
    # Ask for 1 question — easier for small local models to keep valid JSON.
    gen.N_QUESTIONS = 1
    gen.MAX_JSON_RETRIES = 3

    tup = {
        "bloom": "Remember",
        "skillId": "CHEM_TEST1",
        "skillFull": "Identify common laboratory glassware and their uses",
        "topicKey": "CHEM_LAB",
        "topicLabel": "Laboratory Safety and Apparatus",
        "subject": "Chemistry",
    }
    gen.prereqs_raw.setdefault("CHEM_TEST1", [])

    questions = gen.generate_for_tuple(retriever, tup, tuple_number=0, model=model)
    OUT.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(questions)} question(s) -> {OUT.name}")
    for q in questions:
        print("---")
        print("subject:", q.get("subject"))
        print("question_type:", q.get("question_type"))
        print("skill_id:", q.get("skill_id"))
        stem = q.get("question_stem") or ""
        print("stem:", stem[:200])
        opts = q.get("options") or []
        correct = [o for o in opts if o.get("is_correct")]
        print("options:", len(opts), "| correct:", correct[0].get("label") if correct else None)
        print("opt lens:", [len(str(o.get("text") or "")) for o in opts])
        print("source_refs:", len(q.get("source_refs") or []))
        assert q.get("question_type") == "MCQ", "question_type must be MCQ"
        assert not gen.looks_like_written_stem(stem), f"Written-style stem: {stem[:80]}"
        assert len(opts) == 4, "Need exactly 4 options"
    print("\nGeneration OK (MCQ enforced)")


def main() -> None:
    r = test_retrieval()
    model = test_ollama()
    try:
        test_generate(r, model)
        print("\nRAG smoke test PASSED")
        print(f"Inspect: {OUT}")
    except Exception as exc:
        print("\nGeneration FAILED (retrieval + Ollama still OK):")
        print(f"  {exc}")
        print(
            "Tip: small 3B models often break JSON. Retry the same command, "
            "or pull qwen2.5:7b-instruct-q4_K_M when you have disk/VRAM room."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
