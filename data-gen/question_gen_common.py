"""
Shared, backend-agnostic pieces for generating BUET / university-admission
MCQs (Bangla stems + LaTeX math): prompt templates, ontology/Bloom-expansion
loading, and schema/LaTeX/content validation.

This module has no opinion about which model serves the actual generation
call - that lives in generate_question_gemini.py. Nothing here talks to any
model API directly.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_DATA_GEN = Path(__file__).resolve().parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

from rag.config import (
    BLOOM_LEVELS,
    EXPAND_ALL_BLOOM_LEVELS,
    N_QUESTIONS,
    PREREQS_PATH,
    TOP_K,
    TUPLES_PATH,
)

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
    "Analyze": (
        "স্টেমের মধ্যে অবশ্যই একটি সম্পূর্ণ, ধাপে-ধাপে সমাধান উপস্থাপন করতে হবে যেখানে "
        "ঠিক একটি নির্দিষ্ট, নামযোগ্য ভুল ধাপ আছে (যেমন: ভুল সাইন, ভুল সূত্র প্রয়োগ, একটি ধাপ "
        "বাদ পড়া)। প্রশ্ন হবে 'উপরের সমাধানে ভুলটি কোথায়?' বা 'কোন ধাপটি ভুল?' ধরনের — "
        "নিছক আরেকটি হিসাব-নির্ভর প্রশ্ন নয়। প্রতিটি option একটি সম্ভাব্য ভুল-ধাপকে নির্দেশ করবে।"
    ),
    "Evaluate": (
        "স্টেমে অবশ্যই দুটি ভিন্ন সমাধান-পদ্ধতি বা দুটি চূড়ান্ত উত্তর পাশাপাশি উপস্থাপন করতে হবে, "
        "এবং শিক্ষার্থীকে বিচার করতে বলতে হবে কোনটি সঠিক/বৈধ এবং কেন। প্রশ্নটি অবশ্যই এই একই "
        "স্কিলের মধ্যে থাকতে হবে — সম্পূর্ণ ভিন্ন বিষয়ের তুলনা নয়।"
    ),
    "Create": (
        "শিক্ষার্থীকে একটি নতুন সমীকরণ/ম্যাট্রিক্স/পরিস্থিতি নিজে তৈরি বা নির্বাচন করতে বলো যা একটি "
        "নির্দিষ্ট শর্ত পূরণ করে (যেমন: 'নিচের কোন ম্যাট্রিক্সটির নির্ণায়ক শূন্য হবে?')। এটি অবশ্যই "
        "একই স্কিল পরীক্ষা করবে — সম্পূর্ণ ভিন্ন কোনো গণনা বা সূত্র (যেমন adjugate, inverse) "
        "প্রবর্তন করা যাবে না যদি না তা স্পষ্টভাবে skill description-এর অংশ হয়।"
    ),
}

SYSTEM_PROMPT = r"""You are an expert MCQ writer for Bangladesh university admission exams
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
- Use ONLY standard, dictionary-correct Bangla technical vocabulary
  (e.g. "নির্ণায়ক" for determinant). NEVER invent a phonetic transliteration
  or a word that does not exist in standard Bangla mathematical/scientific usage.

════════════════════════════════════════
LATEX RULES (STRICT)
════════════════════════════════════════
- Every LaTeX control sequence MUST start with a backslash: \begin, \end,
  \left, \right, \times, \frac — never "egin{...}" or a bare "end{...}".
- Every \begin{X} MUST be closed by a matching \end{X} with the SAME X
  (e.g. \begin{pmatrix} ... \end{pmatrix}, never \end{matrix} or a bare
  closing parenthesis).
- Do NOT repeat spacing commands like \\[1ex] more than once in a row, and
  never pad an explanation with repeated LaTeX spacing tokens.
- Before outputting, mentally check every $...$ segment: does it start
  and end with matched delimiters? If unsure, prefer plain inline text
  over malformed LaTeX.

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


def repair_llm_json_escapes(text: str) -> str:
    """
    An LLM (local or hosted) writes correct LaTeX (\\begin, \\end, \\right,
    \\times, \\tan, \\frac, \\therefore, ...) directly into a JSON string value
    without doubling the backslash. json.loads() then SILENTLY consumes \\b,
    \\f, \\n, \\r, \\t as JSON's own control-character escapes (\\tan -> a
    literal TAB byte + "an", \\frac -> a FORMFEED byte + "rac") with no
    exception raised - it "succeeds" while quietly corrupting the LaTeX.

    This was first found and fixed for the local Ollama pipeline, on the
    assumption that a hosted API's structured-output mode would be immune to
    it (its own serialization layer, not free-text parsing). Confirmed false:
    under long, LaTeX-dense responses (multi-step Analyze/Evaluate stems
    packing many commands together), Gemini's underlying model still
    sometimes emits a raw undoubled backslash - measured at 13.4% of an early
    real-model batch. So this repair is needed for every backend, not just
    local ones.

    A real backspace/formfeed/carriage-return is never intentional in exam
    question text, so every backslash-letter pair except the genuinely safe
    ones (\\", \\\\, \\/, \\uXXXX) is treated as an unescaped LaTeX command
    and doubled. Applied unconditionally, before every parse attempt, because
    the corruption never raises an exception to fall back on.
    """
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
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
            nxt = text[i + 1]
            if nxt in ('"', "\\", "/"):
                out.append(ch)
                out.append(nxt)
                i += 2
                continue
            if nxt == "u" and i + 5 < n and all(
                c in "0123456789abcdefABCDEF" for c in text[i + 2 : i + 6]
            ):
                out.append(text[i : i + 6])
                i += 6
                continue
            # Everything else (b, f, n, r, t, and genuinely illegal escapes
            # like e/l/x/%) is treated as a literal backslash starting a
            # LaTeX command, not an intentional JSON control escape.
            out.append("\\\\")
            out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


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
    """Repair common schema drift before validation."""
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

        if q.get("question_stem"):
            q["question_stem"] = repair_latex(str(q["question_stem"]))
        for o in q["options"]:
            if o.get("text"):
                o["text"] = repair_latex(str(o["text"]))
            if o.get("explanation"):
                o["explanation"] = repair_latex(str(o["explanation"]))

        normalized.append(q)
    return normalized


# ── LaTeX repair + validation ─────────────────────────────────────────────────
# Small/quantized local models were observed dropping the leading backslash on
# LaTeX control sequences ("egin{pmatrix}" instead of "\begin{pmatrix}"), which
# renders as broken math notation. Kept as a defensive safety net even though
# the current Gemini backend's structured output hasn't shown this failure
# mode. Scoped to math segments only, so plain Bangla/English prose containing
# the words "left"/"right"/"end" is untouched.
#
# Segments are found by splitting on ANY run of 1-2 "$" characters, not by
# matching "$...$" as one pattern - a model can mix inline ($...$) and display
# ($$...$$) delimiters inconsistently (even opens with $$ and closes with a
# single $), and a naive "\$[^$]*\$" match treats adjacent "$$" as one empty
# pair, silently skipping the real content between them.
_MATH_DELIM_RE = re.compile(r"\${1,2}")
_LATEX_DROPPED_BACKSLASH_FIXES = [
    (re.compile(r"(?<!\\)\bbegin\{"), r"\\begin{"),
    (re.compile(r"(?<!\\)\bend\{"), r"\\end{"),
    (re.compile(r"(?<!\\)\bright(?=[)\]}.,])"), r"\\right"),
    (re.compile(r"(?<!\\)\bleft(?=[(\[{])"), r"\\left"),
]
_BEGIN_ENV_RE = re.compile(r"\\begin\{([a-zA-Z*]+)\}")
_END_ENV_RE = re.compile(r"\\end\{([a-zA-Z*]+)\}")


def _extract_math_segments(text: str) -> list[str]:
    """Content between consecutive $/$$ delimiter runs, alternation-based so
    mismatched single/double dollar usage doesn't hide the content between."""
    parts = _MATH_DELIM_RE.split(text)
    return [parts[i] for i in range(1, len(parts) - 1, 2)]


def repair_latex(text: str) -> str:
    """Fix the specific dropped-backslash corruption observed from local models."""
    if not text or "$" not in text:
        return text

    parts = _MATH_DELIM_RE.split(text)
    delims = _MATH_DELIM_RE.findall(text)
    for i in range(1, len(parts) - 1, 2):
        seg = parts[i].replace("\t", " ")
        for pattern, repl in _LATEX_DROPPED_BACKSLASH_FIXES:
            seg = pattern.sub(repl, seg)
        parts[i] = seg

    out = [parts[0]]
    for i, d in enumerate(delims):
        out.append(d)
        out.append(parts[i + 1])
    return "".join(out)


_CONTROL_CHAR_RE = re.compile(r"[\x08\x09\x0a\x0c\x0d]")


def find_escape_corruption(text: str) -> list[str]:
    """
    Safety net for the repair_llm_json_escapes failure mode: if a raw control
    character (backspace/tab/formfeed/CR - a real newline \\n is allowed,
    since genuine line breaks between multi-part sub-questions do occur)
    survives into a field, something upstream failed to repair an undoubled
    backslash before it got JSON-decoded into a control byte. This should
    never fire now that gemini_generate() repairs before every parse, but
    catching it here means a regression gets rejected and retried instead of
    silently stored - exactly what let 13.4% of an early batch through
    uncaught (find_latex_errors only checks brace/begin-end balance, which
    this kind of word-level corruption never breaks).
    """
    if not text:
        return []
    hits = [c for c in text if c in "\x08\x09\x0c\x0d"]
    if hits:
        return [f"control character (JSON-escape corruption) found near: {text[:60]!r}"]
    return []


def find_latex_errors(text: str) -> list[str]:
    """Detect LaTeX still broken after repair: unpaired $, unmatched braces,
    mismatched \\begin/\\end environment names."""
    if not text or "$" not in text:
        return []
    errors: list[str] = []
    if text.count("$") % 2 != 0:
        errors.append(f"unpaired $ delimiter near: {text[:60]!r}")
    for seg in _extract_math_segments(text):
        if seg.count("{") != seg.count("}"):
            errors.append(f"unbalanced braces in LaTeX: {seg[:60]!r}")
        begins = _BEGIN_ENV_RE.findall(seg)
        ends = _END_ENV_RE.findall(seg)
        if begins or ends:
            if len(begins) != len(ends) or begins != ends[::-1]:
                errors.append(f"mismatched \\begin/\\end in LaTeX: {seg[:60]!r}")
    return errors


# ── Skill-relevance judge prompt ────────────────────────────────────────────
# Retrieved reference material can pull the model onto an unrelated skill
# (e.g. a matrix-determinant tuple producing a straight-line-equation
# question) while still tagging the output with the requested skill_id. The
# schema validation below cannot catch this, so a second short judge call
# checks the generated stems against the requested skill before acceptance.
# The judge call itself is backend-specific (lives in generate_question_gemini.py) -
# only the prompt text is shared here.
RELEVANCE_JUDGE_PROMPT = """তুমি একজন বাংলাদেশ ভর্তি পরীক্ষার প্রশ্ন যাচাইকারী।
নিচের প্রতিটি প্রশ্ন কেবলমাত্র এই একটি নির্দিষ্ট দক্ষতা পরীক্ষা করে কিনা যাচাই করো:

দক্ষতা: {SKILL_FULL}

প্রশ্নসমূহ:
{NUMBERED_STEMS}

প্রতিটি প্রশ্নের জন্য true দাও যদি সেটি সরাসরি উপরের দক্ষতাটি পরীক্ষা করে, নাহলে false দাও
(এমনকি যদি প্রশ্নটি একই বিষয়ের/টপিকের হলেও ভিন্ন দক্ষতা পরীক্ষা করে, তাহলে false)।

শুধুমাত্র একটি JSON boolean array output দাও, উদাহরণ: [true, false, true]
অন্য কোনো লেখা, ব্যাখ্যা, বা markdown যোগ করবে না।"""


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

        for latex_err in find_latex_errors(stem) + find_escape_corruption(stem):
            errors.append(f"q[{i}] stem has broken LaTeX: {latex_err}")
        for o in options:
            for field in ("text", "explanation"):
                field_text = str(o.get(field) or "")
                for latex_err in find_latex_errors(field_text) + find_escape_corruption(field_text):
                    errors.append(f"q[{i}] option {o.get('label')} {field} has broken LaTeX: {latex_err}")

        # Repair is_correct / missing_prereq drift
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
    if any(k in label for k in ("chem", "রসায়ন", "রসায়ন")):
        return "Chemistry"
    if any(k in label for k in ("math", "গণিত", "algebra", "calculus", "trigonom", "matri", "geometry")):
        return "Mathematics"
    return "Mathematics"
