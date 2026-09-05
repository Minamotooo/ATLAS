"""
Generate BUET / university-admission MCQs with a local Naive RAG pipeline.

Covers Mathematics, Physics, and Chemistry (Bangla stems + LaTeX math).

Flow:
  tuples.json + prereqs.json
    → retrieve top-k items from documents/*.txt (via rag/kb)
    → prompt local Ollama model with reference material
    → append to output_questions.json (same schema as Gemini pipeline)

Prerequisites:
  1. pip install -r requirements.txt
  2. python -m rag.ingest
  3. Install Ollama (https://ollama.com) and pull a model, e.g.:
       ollama pull qwen2.5:7b-instruct-q4_K_M
     Fallback if VRAM is tight:
       ollama pull qwen2.5:3b-instruct
       then set OLLAMA_MODEL in rag/config.py or via env OLLAMA_MODEL

Run from data-gen/:
    python generate_question_rag.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import requests

_DATA_GEN = Path(__file__).resolve().parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

from rag.config import (
    BLOOM_LEVELS,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    EXPAND_ALL_BLOOM_LEVELS,
    MAX_JSON_RETRIES,
    N_QUESTIONS,
    OLLAMA_BASE_URL,
    OLLAMA_FALLBACK_MODEL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SEC,
    OUTPUT_PATH,
    PREREQS_PATH,
    RAW_OUTPUT_DIR,
    START_TUPLE_INDEX,
    TOP_K,
    TUPLES_PATH,
)
from rag.retriever import Retriever

# ── 1. Load ontology data ─────────────────────────────────────────────────────
with TUPLES_PATH.open("r", encoding="utf-8") as f:
    tuples = json.load(f)

with PREREQS_PATH.open("r", encoding="utf-8") as f:
    prereqs_raw = json.load(f)


def expand_bloom_levels(tuple_list: list) -> list:
    """
    Emit one tuple per (skill x Bloom level) instead of the single level the
    ontology assigns. The adaptive engine selects questions one Bloom level above
    a learner's current band, so a bank covering one level per skill leaves the
    ladder with nothing to climb. Disable with env RAG_EXPAND_BLOOMS=0.
    """
    expanded = []
    for tup in tuple_list:
        for bloom in BLOOM_LEVELS:
            item = dict(tup)
            item["bloom"] = bloom
            expanded.append(item)
    return expanded


if EXPAND_ALL_BLOOM_LEVELS and os.environ.get("RAG_EXPAND_BLOOMS", "1") != "0":
    _before = len(tuples)
    tuples = expand_bloom_levels(tuples)
    print(f"Bloom expansion: {_before} tuples -> {len(tuples)} (all {len(BLOOM_LEVELS)} levels)")


def build_prereq_list(prereqs):
    items = prereqs if isinstance(prereqs, list) else [prereqs]
    return "\n".join(f"- [{p['id']}] {p['full']}" for p in items)


def get_prereq_list_for_skill(skill_id):
    return build_prereq_list(prereqs_raw.get(skill_id, []))


BLOOM_GUIDANCE = {
    "Remember": "কোনো সংজ্ঞা, সূত্র, বা তথ্য সরাসরি স্মরণ করতে বলো।",
    "Understand": "ধারণাটি ব্যাখ্যা করতে বলো।",
    "Apply": "সুনির্দিষ্ট মান/তথ্য দিয়ে সরাসরি সমস্যা সমাধান করতে বলো।",
    "Analyze": "একটি সমাধান উপস্থাপন করো যেখানে ভুল আছে — শিক্ষার্থীকে ভুলটি চিহ্নিত করতে বলো।",
    "Evaluate": "দুটি সমাধান বা পদ্ধতি তুলনা করতে বলো এবং কোনটি সঠিক বিচার করতে বলো।",
    "Create": "একটি সমীকরণ স্থাপন করতে, শর্ত তৈরি করতে, বা পরিস্থিতি নির্মাণ করতে বলো।",
}

SYSTEM_PROMPT = """You are an expert MCQ writer for Bangladesh university admission exams
(BUET, KUET, RUET, CUET, SUST, and similar engineering university admission tests).

Subjects you write for: Mathematics (গণিত), Physics (পদার্থবিজ্ঞান), and Chemistry (রসায়ন).
Candidates are HSC / admission aspirants. Match authentic admission-exam style, difficulty,
and Bangla presentation (with LaTeX for formulas when needed).

You will be given REFERENCE MATERIAL from a scanned exam/book knowledge base that may
include Math, Physics, and Chemistry items — some are MCQ and some are Written.
Use references for Bangla exam style, notation, solution structure, and distractor patterns.
Do NOT copy reference questions verbatim. Generate NEW questions for the requested skill.
Prefer reference material from the SAME subject as the tuple; if a retrieved item is from
another subject, borrow only style/notation habits — the generated question MUST test the
requested skill in the requested subject.

════════════════════════════════════════
MCQ-ONLY (MANDATORY)
════════════════════════════════════════
EVERY generated question MUST be a multiple-choice question (MCQ) with exactly 4 options.
NEVER generate Written / open-ended / descriptive / essay questions.

FORBIDDEN stem patterns (reject these styles):
- লিখ / লিখুন / লেখ / write / explain / describe / prove / draw / আঁক
- উত্তর দাও / ব্যাখ্যা কর / বর্ণনা কর / প্রমাণ কর / দেখাও / কি ঘটে সমীকরণের সাহায্যে
- multi-part "write answers to (i)(ii)(iii)" lab write-ups

REQUIRED stem style:
- Ask the student to CHOOSE the correct answer among A/B/C/D
- Stem ends with a closed question (কোনটি সঠিক? / মান কত? / কোনটি ঘটবে? etc.)
- Options may be short or longer phrases/expressions — but they must be selectable choices, not a request to write an answer

If a reference is type=Written, extract FACTS only — rewrite as a proper MCQ.

════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════
Output a JSON array of question objects. Each object must follow this exact schema:

{
  "bloom_level": string,
  "skill_id": string,
  "skill_description": string,
  "subject": string,
  "topic": string,
  "question_stem": string,
  "options": [
    {
      "label": "A",
      "text": string,
      "is_correct": boolean,
      "explanation": string,
      "missing_prerequisites": [
        {
          "id": string,
          "full": string
        }
      ]
    },
... (B, C, D)
  ],
  "source_refs": [
    {
      "item_id": string,
      "source_file": string,
      "page_number": number_or_null,
      "score": number
    }
  ]
}

════════════════════════════════════════
LANGUAGE RULES
════════════════════════════════════════
- question_stem: বাংলায় লিখুন (write in Bangla); formulas may use LaTeX ($...$)
- option text: numbers/formulas may stay symbolic; word-based options in Bangla
- explanation: সকল ব্যাখ্যা বাংলায় লিখুন (all explanations in Bangla)
- missing_prerequisites: English only (skill IDs and descriptions)
- subject: one of "Mathematics", "Physics", "Chemistry"

════════════════════════════════════════
OPTION RULES
════════════════════════════════════════
1. Exactly ONE option must have is_correct: true.
2. EVERY option — including the correct one — must have a non-empty explanation.
3. Wrong option missing_prerequisites: list only ancestor skills from the provided
   prerequisite chain. Correct option missing_prerequisites: always [].
   If the chain is empty, missing_prerequisites MUST be [] for every option.
4. Exactly four options labeled A, B, C, D.
5. Vary the correct answer position across A/B/C/D.

════════════════════════════════════════
DISTRACTOR DESIGN RULES
════════════════════════════════════════
Each wrong option must be a value or expression a real admission candidate would
actually produce from one specific, nameable error (wrong formula, sign error,
unit mistake, partial step, concept confusion).

════════════════════════════════════════
ADMISSION EXAM STYLE RULES
════════════════════════════════════════
- Stem must be concise: one or two sentences maximum
- NEVER tell the student which method to use in the stem
- Prefer realistic admission-exam numbers and clean results where possible

CRITICAL: Do NOT output anything outside the JSON array. No markdown, no explanation."""

USER_PROMPT_TEMPLATE = """নিচের টুপলের জন্য {N}টি আলাদা MCQ প্রশ্ন তৈরি করো।
প্রতিটি প্রশ্ন অবশ্যই ৪টি অপশন (A/B/C/D)সহ MCQ হতে হবে — Written/খোলা প্রশ্ন নয়।
প্রতিটি প্রশ্ন আলাদা JSON object হবে — সবগুলো মিলে একটি JSON array হিসেবে output দাও।

TUPLE:
- Subject      : {SUBJECT}
- Bloom's Level : {BLOOM_LEVEL}
- Skill ID      : {SKILL_ID}
- Skill         : {SKILL_FULL}
- Topic         : {TOPIC_LABEL}

BLOOM LEVEL GUIDANCE:
{BLOOM_GUIDANCE}

THIS SKILL'S PREREQUISITE CHAIN (use these for missing_prerequisites only):
{PREREQ_LIST}

If the chain above is empty, set missing_prerequisites to [] for all options.

REFERENCE MATERIAL FROM KNOWLEDGE BASE (style/notation/solution patterns only —
do not copy; generate NEW MCQ questions for the skill/subject above.
If a ref is Written, convert the idea into an MCQ with four selectable options.):
{REFERENCE_BLOCKS}

For every generated question, set "subject" to "{SUBJECT}" and set source_refs to the
reference item_ids listed above (or the ones you actually used).

MCQ CHECKLIST (must all be true):
- stem is closed-ended (student picks one option)
- exactly 4 options A–D
- exactly one correct option
- no "লিখুন/ব্যাখ্যা কর/উত্তর দাও" written-style stems

DISTRACTOR HINT:
প্রতিটি ভুল option-এর জন্য উপরের prerequisite chain থেকে
একটি নির্দিষ্ট skill-এর অভাবকে কেন্দ্র করে distractor তৈরি করো।"""


def resolve_ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL)


def ollama_chat(messages: list[dict], model: str | None = None, temperature: float = OLLAMA_TEMPERATURE) -> str:
    model = model or resolve_ollama_model()
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            # Without an explicit num_ctx Ollama uses 2048 and silently drops the
            # tail of the prompt - which is exactly where the reference material is.
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT_SEC)
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Cannot reach Ollama at "
            f"{OLLAMA_BASE_URL}. Install from https://ollama.com then run:\n"
            f"  ollama pull {model}\n"
            f"Fallback smaller model: ollama pull {OLLAMA_FALLBACK_MODEL}\n"
            f"Then optionally: set OLLAMA_MODEL={OLLAMA_FALLBACK_MODEL}"
        ) from exc

    if resp.status_code == 404:
        raise RuntimeError(
            f"Ollama model '{model}' not found. Pull it with:\n"
            f"  ollama pull {model}\n"
            f"Or use the smaller fallback:\n"
            f"  ollama pull {OLLAMA_FALLBACK_MODEL}\n"
            f"  set OLLAMA_MODEL={OLLAMA_FALLBACK_MODEL}"
        )
    resp.raise_for_status()
    data = resp.json()
    content = (data.get("message") or {}).get("content") or ""
    return content.strip()


def strip_markdown_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def extract_questions_payload(parsed):
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("questions", "data", "items", "result"):
            if isinstance(parsed.get(key), list):
                return parsed[key]
        # Sometimes the model wraps a single question as an object
        if "question_stem" in parsed and "options" in parsed:
            return [parsed]
        # Or {"0": {...}, "1": {...}}
        values = list(parsed.values())
        if values and all(isinstance(v, dict) for v in values):
            return values
    raise ValueError("Model output is not a JSON array of questions")


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y"}
    return False


def _normalize_option(raw, fallback_label: str) -> dict:
    if not isinstance(raw, dict):
        return {
            "label": fallback_label,
            "text": str(raw),
            "is_correct": False,
            "explanation": "ব্যাখ্যা নেই।",
            "missing_prerequisites": [],
        }
    label = str(raw.get("label") or fallback_label).strip().upper()
    if label and label[0] in "ABCD":
        label = label[0]
    else:
        label = fallback_label
    missing = raw.get("missing_prerequisites") or []
    if not isinstance(missing, list):
        missing = []
    return {
        "label": label,
        "text": str(raw.get("text") or raw.get("option_text") or "").strip(),
        "is_correct": _coerce_bool(raw.get("is_correct")),
        "explanation": str(raw.get("explanation") or "").strip() or "ব্যাখ্যা নেই।",
        "missing_prerequisites": missing,
    }


def normalize_questions(questions: list) -> list:
    """Repair common local-LLM schema drift before validation."""
    if isinstance(questions, dict):
        questions = extract_questions_payload(questions)
    if not isinstance(questions, list):
        return []

    normalized: list = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        q = dict(q)
        options = q.get("options")

        # documents-style {"a": "...", "b": "..."} or {"A": {...}}
        if isinstance(options, dict):
            converted = []
            for key in ("A", "B", "C", "D", "a", "b", "c", "d", "e", "E"):
                if key not in options:
                    continue
                val = options[key]
                label = key.upper()[0]
                if isinstance(val, dict):
                    converted.append(_normalize_option({**val, "label": label}, label))
                elif val is not None:
                    converted.append(
                        {
                            "label": label,
                            "text": str(val).strip(),
                            "is_correct": False,
                            "explanation": "ব্যাখ্যা নেই।",
                            "missing_prerequisites": [],
                        }
                    )
            options = converted

        if not isinstance(options, list):
            options = []

        # Prefer including the marked-correct option when model returns 5+ choices (A-E).
        normalized_opts = [_normalize_option(opt, "A") for opt in options if isinstance(opt, (dict, str, int, float))]
        if len(normalized_opts) > 4:
            correct_ones = [o for o in normalized_opts if o.get("is_correct")]
            distractors = [o for o in normalized_opts if not o.get("is_correct")]
            if correct_ones:
                chosen = [correct_ones[0]] + distractors[:3]
            else:
                chosen = normalized_opts[:4]
            while len(chosen) < 4 and distractors:
                # already handled
                break
            while len(chosen) < 4:
                label = "ABCD"[len(chosen)]
                chosen.append(
                    {
                        "label": label,
                        "text": f"বিকল্প {label}",
                        "is_correct": False,
                        "explanation": "ব্যাখ্যা নেই।",
                        "missing_prerequisites": [],
                    }
                )
            fixed = chosen[:4]
        else:
            fixed = normalized_opts[:4]

        for idx, opt in enumerate(fixed):
            opt["label"] = "ABCD"[idx]

        # Ensure exactly one correct answer
        correct_idxs = [i for i, o in enumerate(fixed) if o.get("is_correct")]
        if len(correct_idxs) != 1:
            ans = str(q.get("answer") or "").strip().upper()
            for o in fixed:
                o["is_correct"] = False
            if ans in "ABCD":
                fixed["ABCD".index(ans)]["is_correct"] = True
            else:
                # Keep first previously-correct if any, else A
                if correct_idxs:
                    fixed[correct_idxs[0]]["is_correct"] = True
                elif fixed:
                    fixed[0]["is_correct"] = True

        while len(fixed) < 4:
            label = "ABCD"[len(fixed)]
            fixed.append(
                {
                    "label": label,
                    "text": f"বিকল্প {label}",
                    "is_correct": False,
                    "explanation": "ব্যাখ্যা নেই।",
                    "missing_prerequisites": [],
                }
            )

        for o in fixed:
            if o.get("is_correct"):
                o["missing_prerequisites"] = []
            else:
                cleaned = []
                for m in o.get("missing_prerequisites") or []:
                    if isinstance(m, dict) and m.get("id"):
                        cleaned.append({"id": m["id"], "full": m.get("full") or m["id"]})
                o["missing_prerequisites"] = cleaned

        q["options"] = fixed[:4]
        if "question_stem" not in q and "question_text" in q:
            q["question_stem"] = q["question_text"]
        normalized.append(q)
    return normalized


# Written / open-ended stem markers (Bangla + English). Generated output must be MCQ only.
_WRITTEN_STEM_RE = re.compile(
    r"(?:"
    r"লিখুন|লিখ|লেখ|"
    r"ব্যাখ্যা\s*কর|"
    r"বর্ণনা\s*কর|"
    r"প্রমাণ\s*কর|"
    r"উত্তর\s*দাও|"
    r"দেখাও|"
    r"আঁক|"
    r"সমীকরণের\s*সাহায্যে|"
    r"\bwrite\b|\bexplain\b|\bdescribe\b|\bprove\b|\bdraw\b|"
    r"\bdiscuss\b|\belaborate\b"
    r")",
    re.IGNORECASE,
)


def looks_like_written_stem(stem: str) -> bool:
    text = (stem or "").strip()
    if not text:
        return True
    if _WRITTEN_STEM_RE.search(text):
        return True
    # Multi-part written lab prompts: (i)/(ii)/(iii) with write-style length
    if len(re.findall(r"\(\s*[ivxIVX]+\s*\)", text)) >= 3 and len(text) > 160:
        return True
    return False


def validate_questions(questions: list, skill_id: str, bloom: str, prereq_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(questions, list) or not questions:
        return ["empty or non-list questions"]

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            errors.append(f"q[{i}] not an object")
            continue
        for field in ("question_stem", "options"):
            if field not in q or not q.get(field):
                errors.append(f"q[{i}] missing {field}")
        options = q.get("options")
        if not isinstance(options, list) or len(options) != 4:
            errors.append(f"q[{i}] needs exactly 4 options")
            continue
        labels = [str(o.get("label", "")).upper() for o in options]
        if labels != ["A", "B", "C", "D"]:
            errors.append(f"q[{i}] labels must be A,B,C,D got {labels}")

        stem = str(q.get("question_stem") or "")
        if looks_like_written_stem(stem):
            errors.append(
                f"q[{i}] must be MCQ (not Written): rewrite stem as a closed question "
                f"with A/B/C/D choices; avoid লিখুন/ব্যাখ্যা কর/উত্তর দাও"
            )

        # Repair is_correct / missing_prereq drift from small local models
        for o in options:
            o["is_correct"] = _coerce_bool(o.get("is_correct"))
        correct_idxs = [j for j, o in enumerate(options) if o["is_correct"]]
        if len(correct_idxs) != 1:
            for j, o in enumerate(options):
                o["is_correct"] = j == 0
        for o in options:
            if o["is_correct"]:
                o["missing_prerequisites"] = []
            else:
                cleaned = []
                for m in o.get("missing_prerequisites") or []:
                    if not isinstance(m, dict):
                        continue
                    mid = m.get("id")
                    if not mid or mid == skill_id:
                        continue
                    if prereq_ids and mid not in prereq_ids:
                        continue
                    cleaned.append({"id": mid, "full": m.get("full") or mid})
                o["missing_prerequisites"] = cleaned

        for o in options:
            if not str(o.get("text") or "").strip() or str(o.get("text")).startswith("(placeholder"):
                errors.append(f"q[{i}] option {o.get('label')} missing real text")
            if not str(o.get("explanation") or "").strip():
                errors.append(f"q[{i}] option {o.get('label')} missing explanation")
        q["skill_id"] = skill_id
        q["bloom_level"] = bloom
        q["question_type"] = "MCQ"
    return errors


def attach_source_refs(questions: list, hits: list[dict]) -> None:
    refs = [
        {
            "item_id": h.get("item_id"),
            "source_file": h.get("source_file"),
            "page_number": h.get("page_number"),
            "score": round(float(h.get("score", 0.0)), 4),
        }
        for h in hits
    ]
    for q in questions:
        if not isinstance(q, dict):
            continue
        if not q.get("source_refs"):
            q["source_refs"] = refs


def parse_questions(raw_text: str, tuple_number: int, model: str) -> list:
    text = strip_markdown_fences(raw_text)
    try:
        parsed = json.loads(text)
        return extract_questions_payload(parsed)
    except (json.JSONDecodeError, ValueError):
        RAW_OUTPUT_DIR.mkdir(exist_ok=True)
        raw_path = RAW_OUTPUT_DIR / f"tuple_{tuple_number}_raw.txt"
        raw_path.write_text(raw_text, encoding="utf-8")

        fix_prompt = (
            "Fix the following into valid JSON. Output ONLY a JSON array of question objects. "
            "Do not add or remove questions, only fix JSON formatting.\n\n"
            f"RAW:\n{raw_text}"
        )
        fixed = ollama_chat(
            messages=[{"role": "user", "content": fix_prompt}],
            model=model,
            temperature=0.0,
        )
        fixed = strip_markdown_fences(fixed)
        return extract_questions_payload(json.loads(fixed))


def save_questions(questions: list) -> None:
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def format_reference_blocks(hits: list[dict]) -> str:
    if not hits:
        return "(no reference material retrieved)"
    return "\n\n---\n\n".join(h["prompt_block"] for h in hits)


def tuple_subject(tup: dict) -> str:
    """Prefer explicit subject; fall back to topicLabel heuristics."""
    raw = tup.get("subject") or tup.get("Subject") or ""
    if raw:
        return str(raw).strip()
    label = str(tup.get("topicLabel") or "").casefold()
    if any(k in label for k in ("physics", "পদার্থ")):
        return "Physics"
    if any(k in label for k in ("chem", "রসায়ন", "রসায়ন")):
        return "Chemistry"
    if any(k in label for k in ("math", "গণিত", "algebra", "calculus", "trigonom", "matri", "geometry")):
        return "Mathematics"
    return "Mathematics"


def generate_for_tuple(
    retriever: Retriever,
    tup: dict,
    tuple_number: int,
    model: str,
) -> list:
    subject = tuple_subject(tup)
    hits = retriever.retrieve_for_tuple(
        topic_label=tup["topicLabel"],
        skill_full=tup["skillFull"],
        bloom=tup["bloom"],
        subject=subject,
        top_k=TOP_K,
    )
    prereq_list = get_prereq_list_for_skill(tup["skillId"])
    prereq_ids = {p["id"] for p in prereqs_raw.get(tup["skillId"], []) if isinstance(p, dict) and "id" in p}

    user_prompt = USER_PROMPT_TEMPLATE.format(
        N=N_QUESTIONS,
        SUBJECT=subject,
        BLOOM_LEVEL=tup["bloom"],
        SKILL_ID=tup["skillId"],
        SKILL_FULL=tup["skillFull"],
        TOPIC_LABEL=tup["topicLabel"],
        BLOOM_GUIDANCE=BLOOM_GUIDANCE.get(tup["bloom"], ""),
        PREREQ_LIST=prereq_list or "(empty)",
        REFERENCE_BLOCKS=format_reference_blocks(hits),
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_errors: list[str] = []
    for attempt in range(MAX_JSON_RETRIES + 1):
        raw_text = ollama_chat(messages, model=model, temperature=OLLAMA_TEMPERATURE)
        try:
            questions = parse_questions(raw_text, tuple_number, model=model)
            questions = normalize_questions(questions)
        except Exception as exc:
            last_errors = [f"parse error: {exc}"]
            messages.append({"role": "assistant", "content": raw_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous output was invalid JSON. "
                        "Output ONLY a valid JSON array of question objects matching the schema."
                    ),
                }
            )
            continue

        errors = validate_questions(questions, tup["skillId"], tup["bloom"], prereq_ids)
        if not errors:
            attach_source_refs(questions, hits)
            for q in questions:
                if isinstance(q, dict):
                    q.setdefault("skill_description", tup["skillFull"])
                    q.setdefault("topic", tup["topicLabel"])
                    q["subject"] = subject
            return questions

        last_errors = errors
        messages.append({"role": "assistant", "content": raw_text})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Fix these schema errors and regenerate the FULL JSON array only.\n"
                    "Every question MUST be a 4-option MCQ — "
                    "never Written/open-ended stems (no লিখুন/ব্যাখ্যা কর/উত্তর দাও).\n- "
                    + "\n- ".join(errors[:12])
                ),
            }
        )

    raise RuntimeError(
        f"Failed validation after retries for tuple {tuple_number}: " + "; ".join(last_errors[:8])
    )


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    model = resolve_ollama_model()
    print(f"Ollama model: {model}")
    print("Loading retriever from KB ...")
    retriever = Retriever()
    print(f"KB size: {len(retriever.items)} items")

    if OUTPUT_PATH.exists():
        try:
            with OUTPUT_PATH.open("r", encoding="utf-8") as f:
                existing = json.load(f)
            all_questions = existing if isinstance(existing, list) else []
        except json.JSONDecodeError:
            all_questions = []
    else:
        all_questions = []

    tuples_list = tuples if isinstance(tuples, list) else [tuples]
    start_index = max(START_TUPLE_INDEX - 1, 0)

    for i, tup in enumerate(tuples_list):
        if i < start_index:
            continue
        subj = tuple_subject(tup)
        print(
            f"generating tuple {i + 1}/{len(tuples_list)}: "
            f"{subj} / {tup['skillId']} @ {tup['bloom']}..."
        )
        try:
            questions = generate_for_tuple(retriever, tup, i + 1, model=model)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            RAW_OUTPUT_DIR.mkdir(exist_ok=True)
            err_path = RAW_OUTPUT_DIR / f"tuple_{i + 1}_error.txt"
            err_path.write_text(str(exc), encoding="utf-8")
            continue

        all_questions.extend(questions)
        save_questions(all_questions)
        print(f"  OK: Got {len(questions)} questions (total {len(all_questions)})")

    save_questions(all_questions)
    print(f"\nDone! {len(all_questions)} total questions saved to {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
