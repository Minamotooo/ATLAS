"""
Second-pass content audit for already-generated questions, using a STRICTER
verifier than the one the generation pipeline uses - and pushing fixes to
Supabase incrementally, in chunks, rather than all at once at the end.

Why this exists: generate_question_gemini.py's verify_batch_combined() asks
the judge model to pick a single letter among the 4 given options. If the
true correct value isn't exactly any of the 4 (a numerically close-but-wrong
distractor), the judge just picks the closest one - the error is invisible
to it. A manual 36-question stratified read-through (2026-09-07) found 3/36
(~8%) defects of exactly this shape, e.g. a question whose worked-out answer
is 1100 K but whose marked-"correct" option says 1092 K - concentrated in
Analyze/Evaluate/Create-tier questions.

This script's verifier instead forces the judge to derive the answer itself
and then grade EACH of the 4 options independently as exactly-true/false
(not "closest"), with an explicit instruction not to pick a near-miss and a
built-in escape hatch (all four false = none match). A question whose judged
correct option differs from the stored one - or where none/multiple options
verify true - is flagged and regenerated from scratch for the same
(skill, bloom) tuple, then re-checked with BOTH this strict verifier and the
original combined verifier before being accepted as a replacement.

Flagged questions are fixed and pushed to Supabase in chunks (default 100):
after each chunk, every (skill_id, bloom) group touched by a fix in that
chunk is reconciled against the live DB - any DB row whose stem no longer
appears anywhere in the current corpus file for that group is deleted, and
any corpus entry not yet in the DB is inserted. This reconcile-by-group
approach (rather than tracking old/new stems through the run) also means it
self-heals any earlier regenerated-but-not-yet-synced questions (e.g. from
a prior pilot run of this script) the first time it touches their group.

Run from data-gen/:
    python audit_questions.py --fraction 0.30 --real
    python audit_questions.py --fraction 0.05 --real --chunk-size 20  # pilot
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import sys
import threading
import time
from collections import Counter
from pathlib import Path

_DATA_GEN = Path(__file__).resolve().parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

import question_gen_common as gen
import generate_question_gemini as gg
import load_questions_to_supabase as loader
from rag.retriever import Retriever

OUTPUT_PATH = gg.OUTPUT_PATH
REPORT_PATH = _DATA_GEN / "audit_report.json"

STRICT_BATCH_SIZE = 6
MAX_REGEN_ATTEMPTS = 3
DEFAULT_CHUNK_SIZE = 100
# A verify call that fails outright (rate-limit exhaustion, hard timeout,
# malformed response) is retried this many times before giving up on
# auditing that question at all - it is NEVER treated as a finding, since
# under heavy rate-limiting most failures are just that, not a real defect.
MAX_STRICT_CALL_RETRIES = 5
# Outer watchdog around a WHOLE verify_batch_strict() call, independent of
# any timeout inside gemini_generate itself. Observed twice: the pipeline
# froze solid for 20-40+ minutes with zero new output of ANY kind (not even
# [ratelimit] lines, which print on virtually every retry) - i.e. something
# genuinely blocked with no periodic signal, not merely slow under heavy
# rate-limiting. The exact mechanism wasn't pinned down, so this bounds the
# damage structurally instead: no single batch, for any reason, can stall
# the whole run for more than this long before being abandoned and requeued.
BATCH_HARD_TIMEOUT_SEC = 300.0

STRICT_VERIFY_SYSTEM_PROMPT = (
    "You are a rigorous exam-setter double-checking already-written MCQs for "
    "Bangladesh university admission tests (Math/Physics/Chemistry). For each "
    "question: first derive the correct answer yourself from first principles, "
    "showing your work briefly. Then, using ONLY your own derivation - not by "
    "guessing which option 'looks right' or is numerically closest - decide for "
    "EACH of the four given options individually whether it is EXACTLY correct. "
    "A set of decoy options commonly includes one that is very close to the "
    "true answer but not exactly equal (e.g. off by a unit-conversion factor, "
    "a sign, or a rounding step) - such a near-miss must be marked false, not "
    "true. If your derivation matches none of the four options exactly, mark "
    "all four false. Do not assume exactly one option is correct; that is "
    "what you are checking, not a given."
)

STRICT_VERIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "results": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "derivation": {"type": "STRING"},
                    "A": {"type": "BOOLEAN"},
                    "B": {"type": "BOOLEAN"},
                    "C": {"type": "BOOLEAN"},
                    "D": {"type": "BOOLEAN"},
                },
                "required": ["derivation", "A", "B", "C", "D"],
            },
        },
    },
    "required": ["results"],
}


def marked_correct_label(q: dict) -> str | None:
    for o in q.get("options", []):
        if o.get("is_correct"):
            return o.get("label")
    return None


class VerifyCallFailed(Exception):
    """
    The call itself didn't complete (rate-limit exhaustion, hard timeout,
    malformed response) - NOT a judge verdict. Must never be treated the
    same as a genuine "judge found no/ambiguous match" (which returns None
    per-item below): under heavy rate-limiting, conflating the two would
    mark perfectly good questions as defective just because their verify
    call happened to fail, not because anything is wrong with them.
    """


def verify_batch_strict(questions: list[dict], key_state: gg.KeyState) -> list[str | None]:
    """
    Returns, per question in the same order: the single option label the
    judge verified as exactly correct, or None if it found zero or more than
    one (either is a red flag - a well-formed question has exactly one).
    Raises VerifyCallFailed if the call itself didn't produce a usable
    response at all - callers must retry, not treat that as a finding.
    """
    blocks = []
    for i, q in enumerate(questions):
        lines = [f"প্রশ্ন {i + 1} (দক্ষতা: {q.get('skill_description', q.get('skill_id'))}): "
                 f"{q.get('question_stem', '')}"]
        for o in q.get("options", []):
            lines.append(f"  {o.get('label')}) {o.get('text')}")
        blocks.append("\n".join(lines))

    prompt = (
        "নিচের প্রতিটি প্রশ্ন নিজে সমাধান করে যাচাই করো (কোনো অপশনকে সঠিক ধরে না নিয়ে):\n\n"
        + "\n\n".join(blocks)
        + '\n\nJSON দাও: {"results": [{"derivation": "...", "A": true/false, '
          '"B": true/false, "C": true/false, "D": true/false}, ...]} — প্রশ্নের ক্রম অনুযায়ী।'
    )
    parsed, err = gg.gemini_generate(
        key_state, gg.ANSWER_VERIFICATION_MODEL, STRICT_VERIFY_SYSTEM_PROMPT, prompt,
        response_schema=STRICT_VERIFY_SCHEMA,
    )
    if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list) \
            or len(parsed["results"]) != len(questions):
        raise VerifyCallFailed(err or "malformed response")

    out: list[str | None] = []
    for r in parsed["results"]:
        if not isinstance(r, dict):
            out.append(None)
            continue
        trues = [label for label in ("A", "B", "C", "D") if r.get(label) is True]
        out.append(trues[0] if len(trues) == 1 else None)
    return out


def stratified_sample(questions: list[dict], fraction: float, seed: int = 7) -> list[int]:
    rng = random.Random(seed)
    by_cell: dict[tuple, list[int]] = {}
    for i, q in enumerate(questions):
        cell = (q.get("subject"), q.get("bloom_level"))
        by_cell.setdefault(cell, []).append(i)

    picked: list[int] = []
    for cell, idxs in sorted(by_cell.items()):
        n = max(1, -(-int(len(idxs) * fraction) // 1))  # ceil
        picked.extend(rng.sample(idxs, min(n, len(idxs))))
    return sorted(picked)


def regenerate_one(
    retriever: Retriever, skill_id: str, bloom: str, key_state: gg.KeyState,
) -> tuple[dict | None, str]:
    """
    Regenerate ONE fresh question for (skill_id, bloom), requiring it to pass
    BOTH the original combined verifier AND this script's strict verifier
    before accepting it. Returns (question_or_None, reason_if_failed).
    """
    tup = next((t for t in gen.tuples if t["skillId"] == skill_id and t["bloom"] == bloom), None)
    if tup is None:
        return None, f"tuple not found for {skill_id}@{bloom}"

    for _attempt in range(MAX_REGEN_ATTEMPTS):
        try:
            questions, hits, subject, err = gg.generate_schema_valid_tuple(
                retriever, tup, key_state, gg.REAL_MODEL
            )
        except Exception as exc:  # noqa: BLE001
            questions, err = [], f"unhandled exception: {exc!r}"

        if not questions:
            continue

        try:
            ok_call, checks = gg.verify_batch_combined([(tup, questions)], key_state)[0]
        except Exception:
            ok_call, checks = False, []
        if not ok_call or any((not on_topic) or (answer_ok is False) for on_topic, answer_ok in checks):
            continue

        try:
            strict_labels = verify_batch_strict(questions, key_state)
        except Exception:
            continue

        for q, strict_label in zip(questions, strict_labels):
            if strict_label is not None and strict_label == marked_correct_label(q):
                q.setdefault("skill_description", tup["skillFull"])
                q.setdefault("topic", tup["topicLabel"])
                q["subject"] = subject
                if hits is not None:
                    gen.attach_source_refs([q], hits)
                q["_verified"] = True
                return q, ""

    return None, f"exhausted {MAX_REGEN_ATTEMPTS} regen attempts"


def reconcile_groups_to_db(
    db, topic_resolver, known_skills: set[str],
    all_questions: list[dict], groups: set[tuple[str, str]],
    by_group: dict[tuple[str, str], list[int]], stats: Counter,
) -> None:
    """
    For each (skill_id, bloom) touched this chunk: delete any DB row for that
    group whose stem no longer appears anywhere in the current corpus file
    for that group, and insert any corpus entry not yet in the DB. Self-heals
    stale rows regardless of whether they went stale in this run or an
    earlier one.
    """
    to_insert: list[dict] = []
    stale_ids: list[int] = []

    for skill_id, bloom in groups:
        result = (
            db.table("questions").select("id, question_stem")
            .eq("skill_id", skill_id).eq("bloom_level", bloom).execute()
        )
        data, error = loader.payload(result)
        if error:
            print(f"  WARN could not fetch DB rows for {skill_id}@{bloom}: {error}")
            continue
        db_by_stem = {loader.normalize_stem(r["question_stem"]): r["id"] for r in loader.rows_of(data)}

        file_stems = set()
        for idx in by_group.get((skill_id, bloom), []):
            q = all_questions[idx]
            try:
                record = loader.validate_question(q, topic_resolver)
            except loader.Rejected as exc:
                print(f"  WARN regenerated question for {skill_id}@{bloom} failed DB validation: {exc}")
                continue
            stem_key = record["_dupe_key"][3]
            file_stems.add(stem_key)
            if stem_key not in db_by_stem:
                to_insert.append(record)

        stale_ids.extend(rid for stem, rid in db_by_stem.items() if stem not in file_stems)

    if stale_ids:
        db.table("questions").delete().in_("id", stale_ids).execute()
        stats["db_deleted"] += len(stale_ids)
    if to_insert:
        loader.insert_questions_batch(db, to_insert, known_skills, stats)
        stats["db_inserted"] += len(to_insert)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--fraction", type=float, default=0.30)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()

    all_questions = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(all_questions)} questions from {OUTPUT_PATH.name}")

    by_group: dict[tuple[str, str], list[int]] = {}
    for i, q in enumerate(all_questions):
        by_group.setdefault((q["skill_id"], q["bloom_level"]), []).append(i)

    keys = gg.load_keys()
    key_states = [gg.KeyState(k, f"key{i+1}") for i, k in enumerate(keys)]
    print(f"Loaded {len(keys)} API keys")

    print("Connecting to Supabase ...")
    db = loader.make_client(*loader.load_env())
    db_topics = loader.fetch_topics(db)
    known_skills = loader.fetch_skill_ids(db)
    topic_resolver = loader.build_topic_resolver(
        loader._REPO_ROOT / "Backend" / "tree_data" / "topic_resolution.json", db_topics
    )
    db_stats: Counter = Counter()

    # Catch up any earlier run's regenerated-but-unsynced questions first,
    # so this run starts from a DB that matches the file.
    stale_groups = {(q["skill_id"], q["bloom_level"]) for q in all_questions if q.get("_audit_regenerated")}
    if stale_groups:
        print(f"Reconciling {len(stale_groups)} group(s) left unsynced by an earlier run ...")
        reconcile_groups_to_db(db, topic_resolver, known_skills, all_questions, stale_groups, by_group, db_stats)

    print("Loading retriever + KB ...")
    retriever = Retriever()

    sample_idx = stratified_sample(all_questions, args.fraction)
    print(f"Auditing {len(sample_idx)} questions ({100 * len(sample_idx) / len(all_questions):.1f}%), "
          f"stratified by subject x bloom_level")

    # --- phase 1: strict verify the sample, multi-key parallel -------------
    lock = threading.Lock()
    flagged: list[tuple[int, str]] = []
    stats = Counter()

    work = list(sample_idx)
    work_lock = threading.Lock()

    call_retry_count: dict[int, int] = {}

    def worker(key_state: gg.KeyState) -> None:
        while True:
            with work_lock:
                if not work:
                    return
                batch_idx = work[:STRICT_BATCH_SIZE]
                del work[:STRICT_BATCH_SIZE]
            batch_qs = [all_questions[i] for i in batch_idx]
            # A fresh disposable executor per batch (not a shared pool): if
            # verify_batch_strict never returns, .result(timeout=...) only
            # abandons OUR wait, leaking that one thread - a shared pool would
            # instead permanently lose the slot, eventually starving every
            # future batch. See generate_question_gemini.py's gemini_generate
            # for the same pattern and why it matters.
            one_shot = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                labels = one_shot.submit(verify_batch_strict, batch_qs, key_state) \
                    .result(timeout=BATCH_HARD_TIMEOUT_SEC)
            except concurrent.futures.TimeoutError:
                exc: Exception = VerifyCallFailed(f"batch hard-timed out after {BATCH_HARD_TIMEOUT_SEC}s")
            except Exception as caught:  # noqa: BLE001 - call-level failure, not a verdict
                exc = caught
            else:
                exc = None
            finally:
                one_shot.shutdown(wait=False)
            if exc is not None:
                with lock:
                    for idx in batch_idx:
                        call_retry_count[idx] = call_retry_count.get(idx, 0) + 1
                        if call_retry_count[idx] <= MAX_STRICT_CALL_RETRIES:
                            with work_lock:
                                work.append(idx)
                        else:
                            # Genuinely couldn't verify after retrying - leave
                            # UNAUDITED rather than guessing. Not a finding:
                            # never fed into flagged/regeneration.
                            stats["call_failed"] += 1
                            print(f"  [gave up verifying idx={idx} after "
                                  f"{MAX_STRICT_CALL_RETRIES} call failures: {exc!r}]")
                continue
            for idx, q, judged in zip(batch_idx, batch_qs, labels):
                actual = marked_correct_label(q)
                with lock:
                    if judged is not None and judged == actual:
                        stats["confirmed"] += 1
                    else:
                        reason = (
                            "judge found no/ambiguous match" if judged is None
                            else f"judge says {judged} but stored correct is {actual}"
                        )
                        flagged.append((idx, reason))
                        stats["flagged"] += 1
                done = stats["confirmed"] + stats["flagged"] + stats["call_failed"]
                print(f"  [{done}/{len(sample_idx)}] confirmed={stats['confirmed']} "
                      f"flagged={stats['flagged']}", end="\r")

    threads = [threading.Thread(target=worker, args=(ks,), daemon=True) for ks in key_states]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"\nPhase 1 done in {time.time()-t0:.1f}s: {stats['confirmed']} confirmed, "
          f"{stats['flagged']} flagged, {stats['call_failed']} call failures")

    # --- phase 2: regenerate + push flagged questions, in chunks -----------
    print(f"\nFixing {len(flagged)} flagged questions in chunks of {args.chunk_size} ...")
    fixed = 0
    unresolved = []
    chunk_size = args.chunk_size

    for chunk_start in range(0, len(flagged), chunk_size):
        chunk = flagged[chunk_start:chunk_start + chunk_size]
        print(f"\n-- chunk {chunk_start // chunk_size + 1} "
              f"({len(chunk)} items, {chunk_start}/{len(flagged)} so far) --")

        chunk_lock = threading.Lock()
        chunk_work = list(chunk)
        chunk_work_lock = threading.Lock()
        touched_groups: set[tuple[str, str]] = set()

        def fix_worker(key_state: gg.KeyState) -> None:
            nonlocal fixed
            while True:
                with chunk_work_lock:
                    if not chunk_work:
                        return
                    idx, reason = chunk_work.pop()
                old_q = all_questions[idx]
                new_q, fail_reason = regenerate_one(
                    retriever, old_q["skill_id"], old_q["bloom_level"], key_state
                )
                with chunk_lock:
                    if new_q is not None:
                        all_questions[idx] = new_q
                        fixed += 1
                        touched_groups.add((old_q["skill_id"], old_q["bloom_level"]))
                        print(f"  FIXED {old_q['skill_id']}@{old_q['bloom_level']} ({reason})")
                    else:
                        unresolved.append({"index": idx, "skill_id": old_q["skill_id"],
                                            "bloom_level": old_q["bloom_level"], "reason": reason,
                                            "regen_failure": fail_reason})
                        print(f"  UNRESOLVED {old_q['skill_id']}@{old_q['bloom_level']}: {fail_reason}")

        threads = [threading.Thread(target=fix_worker, args=(ks,), daemon=True) for ks in key_states]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if touched_groups:
            print(f"  Syncing {len(touched_groups)} affected skill/bloom group(s) to Supabase ...")
            reconcile_groups_to_db(db, topic_resolver, known_skills, all_questions, touched_groups, by_group, db_stats)

        OUTPUT_PATH.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Chunk done. Total so far: fixed={fixed}, unresolved={len(unresolved)}, "
              f"db_inserted={db_stats['db_inserted']}, db_deleted={db_stats['db_deleted']}")

    # --- final report ----------------------------------------------------
    report = {
        "audited": len(sample_idx),
        "audited_fraction": len(sample_idx) / len(all_questions),
        "confirmed": stats["confirmed"],
        "flagged": stats["flagged"],
        "call_failed": stats["call_failed"],
        "fixed": fixed,
        "unresolved": unresolved,
        "db_inserted": db_stats["db_inserted"],
        "db_deleted": db_stats["db_deleted"],
        "flagged_details": [
            {"skill_id": all_questions[i]["skill_id"] if i < len(all_questions) else None,
             "bloom_level": all_questions[i]["bloom_level"] if i < len(all_questions) else None,
             "reason": r}
            for i, r in flagged
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {REPORT_PATH.name}")

    print("\n--- summary ---")
    print(f"  audited          : {len(sample_idx)} / {len(all_questions)} "
          f"({100*len(sample_idx)/len(all_questions):.1f}%)")
    print(f"  confirmed correct: {stats['confirmed']}")
    print(f"  flagged          : {stats['flagged']}")
    print(f"  fixed (regen)    : {fixed}")
    print(f"  unresolved       : {len(unresolved)}")
    print(f"  db rows inserted : {db_stats['db_inserted']}")
    print(f"  db rows deleted  : {db_stats['db_deleted']}")


if __name__ == "__main__":
    main()
