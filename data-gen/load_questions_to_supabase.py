"""
load_questions_to_supabase.py
-----------------------------
Load RAG-generated MCQs (output_questions.json) into the Supabase tables that
Backend/server.py queries. This is the link between the generation pipeline and
the adaptive engine.

Target schema: see Backend/schema.sql. The constraints that shape this loader:

  * questions.topic  FK -> ontology_topics(topic_code)
        The column stores a topic CODE ("MAT_MATRIX"), but the generator writes
        tuple["topicLabel"] ("Matrices and Determinants") into the `topic` field.
        We resolve label -> code before inserting, or the FK rejects the row.
  * questions.skill_id                     FK -> skills(skill_id)
  * option_missing_prerequisites.missing_skill_id  FK -> skills(skill_id)
        Both must exist before the insert. Use --create-missing-skills to upsert
        them from the question's own skill_description, otherwise rows are skipped.
  * question_options.option_label          CHECK in (A,B,C,D)
  * question_options(question_id, option_label)  UNIQUE
  * skills.skill_description               NOT NULL
  * questions has NO natural unique key — only the bigserial id. A second run of
        this script would happily duplicate every question, so we dedup against
        rows already in the DB on (skill_id, bloom_level, topic, normalized stem).

Bloom labels are normalized to the exact capitalization server.py filters on
(`BloomLevel.name.capitalize()` -> "Remember", "Apply", ...). A row written as
"apply" or "APPLY" would be invisible to every question query.

Usage
-----
    # inspect only — no writes, full validation report
    python load_questions_to_supabase.py --dry-run

    # real load
    python load_questions_to_supabase.py \
        --input output_questions.json \
        --topic-labels ../Backend/tree_data/topic_resolution.json \
        --create-missing-skills

Env: SUPABASE_URL and SUPABASE_SERVICE_KEY, read from the environment or from
     Backend/.env / data-gen/.env.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_DATA_GEN = Path(__file__).resolve().parent
_REPO_ROOT = _DATA_GEN.parent

VALID_LABELS = ["A", "B", "C", "D"]

# Must match Backend/bloom_taxonomy.BloomLevel names, capitalized the way
# server.py's _bloom_label() emits them.
CANONICAL_BLOOM = {
    "remember": "Remember",
    "understand": "Understand",
    "apply": "Apply",
    "analyze": "Analyze",
    "analyse": "Analyze",
    "evaluate": "Evaluate",
    "create": "Create",
}


# ---------------------------------------------------------------------------
# Environment / client
# ---------------------------------------------------------------------------
def load_env() -> Tuple[str, str]:
    for candidate in (_REPO_ROOT / "Backend" / ".env", _DATA_GEN / ".env"):
        if candidate.is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(candidate)
                print(f"loaded env from {candidate}")
                break
            except ImportError:
                # Minimal parser so this script works without python-dotenv installed.
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
                print(f"loaded env from {candidate} (fallback parser)")
                break

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set (env, "
            "Backend/.env, or data-gen/.env)."
        )
    return url, key


def make_client(url: str, key: str):
    try:
        from supabase import create_client
    except ImportError:
        raise SystemExit(
            "ERROR: the supabase package is not installed.\n"
            "  pip install supabase>=2.4.0"
        )
    return create_client(url, key)


def payload(response):
    """Mirror server.py's _extract_supabase_payload."""
    if response is None:
        return None, None
    if isinstance(response, dict):
        return response.get("data"), response.get("error")
    return getattr(response, "data", None), getattr(response, "error", None)


def rows_of(data) -> List[dict]:
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    return list(data)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
def normalize_bloom(raw) -> Optional[str]:
    if not raw:
        return None
    return CANONICAL_BLOOM.get(str(raw).strip().casefold())


def normalize_stem(text: str) -> str:
    """Whitespace-insensitive key used for duplicate detection."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def fuzzy_topic_key(value: str) -> str:
    """
    Loose key for topic matching. The `topic` field is written by an LLM, so it
    drifts from the canonical label in small ways ("Acids, Bases & pH" vs
    "Acids, Bases and pH", "15 · Modern Physics" vs "Modern Physics"). Strip it
    down to comparable alphanumerics.
    """
    text = str(value or "").casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"^\s*\d+\s*[.·•:-]\s*", "", text)  # leading "1 · ", "2. "
    text = re.sub(r"[^a-z0-9ঀ-৿]+", " ", text)  # keep latin + bengali
    return re.sub(r"\s+", " ", text).strip()


class TopicResolver:
    """Resolve a generator-written topic string to a real ontology_topics.topic_code."""

    def __init__(self) -> None:
        self.exact: Dict[str, str] = {}
        self._fuzzy: Dict[str, Set[str]] = defaultdict(set)

    def register(self, source: str, code: str, *, override: bool = False) -> None:
        key = str(source).strip().casefold()
        if override:
            self.exact[key] = code
        else:
            self.exact.setdefault(key, code)
        self._fuzzy[fuzzy_topic_key(source)].add(code)

    def resolve(self, raw: str) -> Optional[str]:
        key = str(raw).strip().casefold()
        if key in self.exact:
            return self.exact[key]
        candidates = self._fuzzy.get(fuzzy_topic_key(raw))
        # Only trust a fuzzy hit when it is unambiguous.
        if candidates and len(candidates) == 1:
            return next(iter(candidates))
        return None

    @property
    def ambiguous(self) -> List[str]:
        return sorted(k for k, v in self._fuzzy.items() if len(v) > 1)


def build_topic_resolver(
    topic_labels_path: Optional[Path],
    db_topics: Dict[str, str],
    topic_map_path: Optional[Path] = None,
) -> TopicResolver:
    """
    Map any topic string the generator may emit -> a topic_code that exists in
    ontology_topics. Accepts the code itself, the DB label, a label from the
    converter's topic_labels.json, or an explicit override from --topic-map.

    The source ontology carries several codes per topic (MAT_ vs MATH_, CHE_ vs
    CHEM_), which ontology_config.json collapses to one canonical code. The
    generator stamps questions with the RAW label, so resolution is required.
    """
    resolver = TopicResolver()

    # Explicit overrides win over anything derived from the DB or label files.
    if topic_map_path and topic_map_path.is_file():
        overrides = {
            k: v
            for k, v in json.loads(topic_map_path.read_text(encoding="utf-8")).items()
            if not k.startswith("_")  # allow "_comment" documentation keys
        }
        unknown = sorted({v for v in overrides.values() if db_topics and v not in db_topics})
        for source, code in overrides.items():
            resolver.register(source, code, override=True)
        print(f"loaded {len(overrides)} topic overrides from {topic_map_path.name}")
        if unknown:
            print(
                f"  WARN {len(unknown)} override targets are not in ontology_topics "
                f"and will fail the FK: {', '.join(unknown[:8])}"
            )

    for code, label in db_topics.items():
        resolver.register(code, code)
        if label:
            resolver.register(label, code)

    if topic_labels_path and topic_labels_path.is_file():
        # topic_resolution.json is {any raw code or label: canonical topic_code}.
        extra = json.loads(topic_labels_path.read_text(encoding="utf-8"))
        for source, code in extra.items():
            resolver.register(source, code)
        print(f"loaded {len(extra)} topic resolutions from {topic_labels_path.name}")

    if resolver.ambiguous:
        print(
            f"  note: {len(resolver.ambiguous)} topic names are ambiguous after "
            "normalization; those resolve by exact match only."
        )

    return resolver


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class Rejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def validate_question(q: dict, topic_resolver: "TopicResolver") -> dict:
    """
    Return a DB-shaped record, or raise Rejected. Every check here corresponds to
    a NOT NULL / CHECK / FK constraint in Backend/schema.sql.
    """
    if not isinstance(q, dict):
        raise Rejected("not a JSON object")

    skill_id = str(q.get("skill_id") or "").strip()
    if not skill_id:
        raise Rejected("missing skill_id")

    bloom = normalize_bloom(q.get("bloom_level"))
    if not bloom:
        raise Rejected(f"unrecognized bloom_level {q.get('bloom_level')!r}")

    stem = normalize_stem(q.get("question_stem"))
    if not stem:
        raise Rejected("empty question_stem")

    raw_topic = str(q.get("topic") or "").strip()
    if not raw_topic:
        raise Rejected("missing topic")
    topic_code = topic_resolver.resolve(raw_topic)
    if not topic_code:
        raise Rejected(f"topic {raw_topic!r} does not resolve to any ontology_topics.topic_code")

    options = q.get("options")
    if not isinstance(options, list) or len(options) != 4:
        raise Rejected(f"needs exactly 4 options, got {len(options) if isinstance(options, list) else 'none'}")

    seen_labels: List[str] = []
    normalized_options: List[dict] = []
    correct = 0
    for opt in options:
        if not isinstance(opt, dict):
            raise Rejected("option is not an object")
        label = str(opt.get("label") or "").strip().upper()
        if label not in VALID_LABELS:
            raise Rejected(f"option label {label!r} violates CHECK (A,B,C,D)")
        if label in seen_labels:
            raise Rejected(f"duplicate option label {label!r} violates UNIQUE(question_id, option_label)")
        seen_labels.append(label)

        text = str(opt.get("option_text") or opt.get("text") or "").strip()
        if not text:
            raise Rejected(f"option {label} has empty text (option_text is NOT NULL)")

        is_correct = bool(opt.get("is_correct"))
        correct += int(is_correct)

        explanation = str(opt.get("explanation") or "").strip() or None

        missing: List[str] = []
        for m in opt.get("missing_prerequisites") or []:
            mid = m.get("id") if isinstance(m, dict) else m
            mid = str(mid or "").strip()
            if mid and mid != skill_id and mid not in missing:
                missing.append(mid)
        if is_correct:
            missing = []

        normalized_options.append(
            {
                "option_label": label,
                "option_text": text,
                "is_correct": is_correct,
                "explanation": explanation,
                "missing_prerequisites": missing,
            }
        )

    if sorted(seen_labels) != VALID_LABELS:
        raise Rejected(f"labels must be exactly A,B,C,D — got {sorted(seen_labels)}")
    if correct != 1:
        raise Rejected(f"needs exactly one correct option, found {correct}")

    return {
        "skill_id": skill_id,
        "bloom_level": bloom,
        "topic": topic_code,
        "question_stem": stem,
        "skill_description": str(q.get("skill_description") or "").strip(),
        "options": normalized_options,
        "_dupe_key": (skill_id, bloom, topic_code, stem),
    }


# ---------------------------------------------------------------------------
# DB reads
# ---------------------------------------------------------------------------
def fetch_topics(db) -> Dict[str, str]:
    result = db.table("ontology_topics").select("topic_code, topic_label").limit(10000).execute()
    data, error = payload(result)
    if error:
        raise SystemExit(f"ERROR: could not read ontology_topics: {error}")
    return {r["topic_code"]: r.get("topic_label") for r in rows_of(data)}


def fetch_skill_ids(db) -> Set[str]:
    result = db.table("skills").select("skill_id").limit(100000).execute()
    data, error = payload(result)
    if error:
        raise SystemExit(f"ERROR: could not read skills: {error}")
    return {r["skill_id"] for r in rows_of(data) if r.get("skill_id")}


def fetch_existing_keys(db, skill_ids: List[str]) -> Set[Tuple[str, str, str, str]]:
    """
    Existing (skill_id, bloom_level, topic, stem) tuples, for dedup.

    PostgREST silently caps a response at its project's max-rows setting
    (1000 on this Supabase project) regardless of what `.limit()` asks for -
    it is NOT an error, just a truncated result. A single unpaged select
    used to work fine when the table was small; once it grew past ~1000
    matching rows, later pages went missing from `existing`, dedup stopped
    recognizing already-loaded questions as duplicates, and a rerun
    quietly re-inserted them. Page explicitly with `.range()` until a page
    comes back under the page size, so this doesn't reappear as the table
    keeps growing.
    """
    existing: Set[Tuple[str, str, str, str]] = set()
    chunk = 200
    page_size = 1000
    for i in range(0, len(skill_ids), chunk):
        batch = skill_ids[i : i + chunk]
        offset = 0
        while True:
            result = (
                db.table("questions")
                .select("skill_id, bloom_level, topic, question_stem")
                .in_("skill_id", batch)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            data, error = payload(result)
            if error:
                raise SystemExit(f"ERROR: could not read questions for dedup: {error}")
            page = rows_of(data)
            for r in page:
                existing.add(
                    (
                        r["skill_id"],
                        r["bloom_level"],
                        r["topic"],
                        normalize_stem(r["question_stem"]),
                    )
                )
            if len(page) < page_size:
                break
            offset += page_size
    return existing


# ---------------------------------------------------------------------------
# DB writes
# ---------------------------------------------------------------------------
def upsert_skills(db, skills: Dict[str, str]) -> int:
    """skills.skill_description is NOT NULL, so always send a string."""
    if not skills:
        return 0
    rows = [
        {"skill_id": sid, "skill_description": desc or sid}
        for sid, desc in sorted(skills.items())
    ]
    result = db.table("skills").upsert(rows, on_conflict="skill_id").execute()
    _, error = payload(result)
    if error:
        raise SystemExit(f"ERROR: could not upsert skills: {error}")
    return len(rows)


def insert_questions_batch(
    db, records: List[dict], known_skills: Set[str], stats: Counter, batch_size: int = 250
) -> None:
    """
    Bulk-insert many questions (with their options and missing-prerequisite
    links) using one INSERT per table per batch, instead of one question ->
    4 options -> N prereqs round trip per question. A single multi-row
    INSERT with no ON CONFLICT/trigger reordering returns its rows in the
    same order as the VALUES list, so generated ids are zipped back
    positionally rather than looked up - that's what makes batching safe
    here. If a batch fails outright (network blip, one bad row), the whole
    batch is skipped and logged; already-inserted batches are unaffected,
    and a retry is safe because the dedup pass treats them as already loaded.
    """
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        try:
            question_rows = [
                {
                    "skill_id": r["skill_id"],
                    "bloom_level": r["bloom_level"],
                    "topic": r["topic"],
                    "question_stem": r["question_stem"],
                }
                for r in batch
            ]
            result = db.table("questions").insert(question_rows).execute()
            data, error = payload(result)
            if error:
                raise RuntimeError(f"questions bulk insert failed: {error}")
            inserted = rows_of(data)
            if len(inserted) != len(batch):
                raise RuntimeError(f"expected {len(batch)} question ids back, got {len(inserted)}")
            question_ids = [row["id"] for row in inserted]

            option_rows = []
            option_owners = []  # same order as option_rows, for zipping ids back
            for rec, qid in zip(batch, question_ids):
                for o in rec["options"]:
                    option_rows.append(
                        {
                            "question_id": qid,
                            "option_label": o["option_label"],
                            "option_text": o["option_text"],
                            "is_correct": o["is_correct"],
                            "explanation": o["explanation"],
                        }
                    )
                    option_owners.append(o)

            try:
                result = db.table("question_options").insert(option_rows).execute()
                data, error = payload(result)
                if error:
                    raise RuntimeError(f"question_options bulk insert failed: {error}")
                inserted_opts = rows_of(data)
                if len(inserted_opts) != len(option_rows):
                    raise RuntimeError(f"expected {len(option_rows)} option ids back, got {len(inserted_opts)}")
            except Exception:
                # Options failed after the questions committed - those rows
                # would otherwise sit with zero options, yet still look
                # "already loaded" to the dedup pass on any future retry
                # (which only checks the questions table), permanently
                # hiding the gap. Delete them so a retry actually redoes them.
                db.table("questions").delete().in_("id", question_ids).execute()
                raise

            prereq_rows = []
            for owner, opt_row in zip(option_owners, inserted_opts):
                for mid in owner["missing_prerequisites"]:
                    if mid not in known_skills:
                        stats["missing_prereq_refs_dropped"] += 1
                        continue
                    prereq_rows.append({"option_id": opt_row["id"], "missing_skill_id": mid})

            if prereq_rows:
                result = db.table("option_missing_prerequisites").insert(prereq_rows).execute()
                _, error = payload(result)
                if error:
                    raise RuntimeError(f"option_missing_prerequisites bulk insert failed: {error}")
                stats["prereq_links"] += len(prereq_rows)

            stats["questions"] += len(batch)
        except Exception as exc:
            stats["failed"] += len(batch)
            print(f"  ERROR batch [{start}:{start + len(batch)}]: {exc}")
        print(f"  {min(start + batch_size, len(records))}/{len(records)} ...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Load RAG questions into Supabase.")
    parser.add_argument("--input", type=Path, default=_DATA_GEN / "output_questions.json")
    parser.add_argument(
        "--topic-labels",
        type=Path,
        default=_REPO_ROOT / "Backend" / "tree_data" / "topic_resolution.json",
        help="topic_resolution.json from build_from_ontology.py (raw code/label -> canonical code).",
    )
    parser.add_argument(
        "--topic-map",
        type=Path,
        default=None,
        help="JSON {source_topic_or_code: topic_code} overrides, for one-off corrections.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and report; write nothing.")
    parser.add_argument(
        "--create-missing-skills",
        action="store_true",
        help="Upsert skills referenced by questions but absent from the skills table.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N questions.")
    parser.add_argument("--verbose", "-v", action="store_true", help="List every rejected question.")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.input.is_file():
        raise SystemExit(f"ERROR: input not found: {args.input}")

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    questions = raw if isinstance(raw, list) else [raw]
    if args.limit:
        questions = questions[: args.limit]
    print(f"input: {args.input}  ({len(questions)} questions)")

    db = make_client(*load_env())

    db_topics = fetch_topics(db)
    known_skills = fetch_skill_ids(db)
    print(f"db: {len(db_topics)} ontology_topics, {len(known_skills)} skills")
    if not db_topics:
        print(
            "\nWARNING: ontology_topics is empty. questions.topic is a FK to it, so every\n"
            "insert will fail. Run Backend/tree_data/sync_ontology_to_supabase.sql first."
        )

    topic_resolver = build_topic_resolver(args.topic_labels, db_topics, args.topic_map)

    # --- validate ----------------------------------------------------------
    valid: List[dict] = []
    rejects: List[Tuple[int, str]] = []
    for i, q in enumerate(questions):
        try:
            valid.append(validate_question(q, topic_resolver))
        except Rejected as exc:
            rejects.append((i, exc.reason))

    print(f"\nvalidation: {len(valid)} ok, {len(rejects)} rejected")
    if rejects:
        by_reason = Counter(re.sub(r"'[^']*'", "'...'", r) for _, r in rejects)
        for reason, count in by_reason.most_common(10):
            print(f"  {count:5d}  {reason}")
        if args.verbose:
            print()
            for idx, reason in rejects:
                print(f"    q[{idx}]: {reason}")

    if not valid:
        print("\nNothing to load.")
        return 1

    # --- FK preflight ------------------------------------------------------
    needed_skills: Dict[str, str] = {}
    for record in valid:
        needed_skills.setdefault(record["skill_id"], record["skill_description"])
        for o in record["options"]:
            for mid in o["missing_prerequisites"]:
                needed_skills.setdefault(mid, "")

    missing_skills = {s: d for s, d in needed_skills.items() if s not in known_skills}
    missing_question_skills = sorted(
        {r["skill_id"] for r in valid if r["skill_id"] not in known_skills}
    )

    if missing_skills:
        print(f"\n{len(missing_skills)} referenced skills are not in the skills table")
        print(f"  of which {len(missing_question_skills)} are question skill_ids (hard FK blocker)")
        for sid in list(missing_skills)[:10]:
            print(f"    - {sid}")
        if len(missing_skills) > 10:
            print(f"    ... and {len(missing_skills) - 10} more")
        if not args.create_missing_skills:
            print(
                "  -> pass --create-missing-skills to upsert them, or sync the ontology first.\n"
                "     Questions on unknown skills will be SKIPPED; unknown missing_prerequisite\n"
                "     references will be dropped."
            )

    # --- dedup -------------------------------------------------------------
    loadable_skills = sorted({r["skill_id"] for r in valid})
    existing = fetch_existing_keys(db, loadable_skills)
    print(f"\ndedup: {len(existing)} existing questions for these skills")

    fresh: List[dict] = []
    dupes_in_db = 0
    dupes_in_file = 0
    seen_in_file: Set[Tuple[str, str, str, str]] = set()
    for record in valid:
        key = record["_dupe_key"]
        if key in existing:
            dupes_in_db += 1
            continue
        if key in seen_in_file:
            dupes_in_file += 1
            continue
        seen_in_file.add(key)
        fresh.append(record)

    print(f"  {dupes_in_db} already in DB, {dupes_in_file} duplicated within the file")
    print(f"  {len(fresh)} new questions to insert")

    # --- write -------------------------------------------------------------
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        by_topic = Counter(r["topic"] for r in fresh)
        by_bloom = Counter(r["bloom_level"] for r in fresh)
        print(f"\nwould insert across {len(by_topic)} topics, blooms: {dict(by_bloom)}")
        return 0

    stats: Counter = Counter()

    if args.create_missing_skills and missing_skills:
        created = upsert_skills(db, missing_skills)
        known_skills |= set(missing_skills)
        print(f"\nupserted {created} skills")

    to_insert = [r for r in fresh if r["skill_id"] in known_skills]
    skipped_fk = len(fresh) - len(to_insert)
    if skipped_fk:
        print(f"skipping {skipped_fk} questions whose skill_id is not in the skills table")

    print(f"\ninserting {len(to_insert)} questions (bulk) ...")
    insert_questions_batch(db, to_insert, known_skills, stats)

    print("\n--- summary ---")
    print(f"  questions inserted        : {stats['questions']}")
    print(f"  options inserted          : {stats['questions'] * 4}")
    print(f"  prereq links inserted     : {stats['prereq_links']}")
    print(f"  prereq refs dropped (FK)  : {stats['missing_prereq_refs_dropped']}")
    print(f"  failed                    : {stats['failed']}")
    print(f"  rejected in validation    : {len(rejects)}")
    print(f"  skipped as duplicates     : {dupes_in_db + dupes_in_file}")
    return 0 if not stats["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
