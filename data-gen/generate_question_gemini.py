"""
Generate BUET / university-admission MCQs via the Gemini API, using a pool of
keys from keys/.gemini_keys run concurrently to stay under each key's
per-minute quota while maximizing combined throughput.

Reuses the ontology loading, Bloom expansion, prompt templates, and
schema/LaTeX validation from question_gen_common.py. Gemini's responseSchema
(structured output) usually returns correctly-escaped JSON, but NOT always -
under long, LaTeX-dense responses (multi-step Analyze/Evaluate stems packing
many \tan/\frac/\therefore-style commands) the underlying model can still
emit a raw, undoubled backslash, which json.loads() then silently consumes
as a JSON control escape (\t/\f/\n/\r -> a real control byte, eating the
command's leading letter) - the exact bug fixed for the local Ollama
pipeline. Confirmed empirically: 13.4% of an early real-model batch showed
this corruption. gen.repair_llm_json_escapes() runs before every json.loads()
here for that reason.

Run from data-gen/:
    python generate_question_gemini.py --limit 6              # small pilot (test model)
    python generate_question_gemini.py --sample-topics 5       # broader pilot (test model)
    python generate_question_gemini.py --real                  # full run (production model)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Callable

import requests

_DATA_GEN = Path(__file__).resolve().parent
if str(_DATA_GEN) not in sys.path:
    sys.path.insert(0, str(_DATA_GEN))

import question_gen_common as gen  # reuse prompts, ontology loading, validation
from rag.retriever import Retriever

KEYS_PATH = _DATA_GEN.parent / "keys" / ".gemini_keys"
# 3.5-flash-lite is reserved for the real run; pilots/tests default to 3.1 so
# they don't eat into the quota budgeted for the actual question bank.
REAL_MODEL = "gemini-3.5-flash-lite"
TEST_MODEL = "gemini-3.1-flash-lite"
GENERATION_MODEL = TEST_MODEL
# Verification (skill-relevance judge + blind answer re-solve) always runs on
# the cheaper model, regardless of --real - it's a simpler task (pick among 4
# given options) than generation, and keeping it off REAL_MODEL means it draws
# from a separate quota pool instead of competing with generation calls.
ANSWER_VERIFICATION_MODEL = TEST_MODEL
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# requests' own `timeout=` is supposed to bound a call, but a real ~40-minute
# hang was observed (audit_questions.py, 2026-09-07) with no progress from any
# of 10 parallel keys - well past every theoretical retry/backoff ceiling in
# this file, meaning some single HTTP call likely blocked past its stated
# timeout (a known occasional platform/networking issue, not something this
# code can prevent at the requests-call level). Running the call through a
# thread pool and bounding it with .result(timeout=...) gives a hard ceiling
# that holds even if requests' own timeout silently fails to fire - the
# request thread is orphaned (Python can't kill a blocked thread) but the
# caller is guaranteed to get control back.
_HTTP_HARD_TIMEOUT_SEC = 75.0  # a bit above requests' own 60s timeout
# Every question that reaches the output file has already passed schema
# validation AND the combined verification call (on-topic + independent
# answer check) - that's true regardless of which model generated it, so
# pilot/test runs accumulate into the same file as the real run rather than
# a separate throwaway one. A verified-good question is real usable data.
#
# _v2 = the full-corpus-rebuild ontology (1,688 skills), NOT the legacy
# 430-skill run. Deliberately a separate file: 26 skillIds collide as
# STRINGS between the two ontologies (same id, different or reworded skill -
# see the reassignment feasibility probe from 2026-09-18), so reusing the
# legacy progress/output file could silently mark new-ontology tuples "done"
# off a stale legacy match, or interleave two unrelated corpora in one file.
# The legacy output_questions_gemini.json / gemini_progress.json are left
# on disk untouched as historical reference for the old 430-skill campaign.
OUTPUT_PATH = _DATA_GEN / "output_questions_gemini_v2.json"
PROGRESS_PATH = _DATA_GEN / "gemini_progress_v2.json"

# Conservative default; adjusted downward automatically if a 429 says otherwise.
DEFAULT_RPM = 15
MAX_RETRIES_PER_TUPLE = 2
# On a 429, retry exactly 3 times at these fixed delays (1st retry after
# 10s, 2nd after 30s, 3rd after 60s) - not adaptive, not server-driven.
# After all 3 still fail, the call is treated as timed out (one
# fully-failed logical call - see note_call_exhausted).
RETRY_DELAYS_SEC = [10.0, 30.0, 60.0]
# A key/model pair that racks up this many CONSECUTIVE fully-failed LOGICAL
# CALLS (each of which already retried up to MAX_429_RETRIES times - this
# is NOT a count of raw 429 responses, see note_call_exhausted's docstring
# for why that distinction is the whole fix) gets marked exhausted rather
# than retried forever. Reset to 0 by any success.
CONSECUTIVE_429_EXHAUSTION_THRESHOLD = 10
# Batched verification: up to this many tuples' worth of questions go into
# ONE verification call, cutting call count ~N-fold vs one call per tuple.
BATCH_VERIFY_SIZE = 8
# How long a verifier thread waits for the FIRST item before giving up this
# round (not how long it waits to fill a full batch - once it has one item
# it grabs whatever else is immediately available via get_nowait() and sends
# the batch, so a slow trickle near the end of a run doesn't stall verification).
VERIFY_BATCH_WAIT = 20.0

RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "question_stem": {"type": "STRING"},
            "options": {
                "type": "ARRAY",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "label": {"type": "STRING", "enum": ["A", "B", "C", "D"]},
                        "text": {"type": "STRING"},
                        "is_correct": {"type": "BOOLEAN"},
                        "explanation": {"type": "STRING"},
                        "missing_prerequisites": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id": {"type": "STRING"},
                                    "full": {"type": "STRING"},
                                },
                                "required": ["id", "full"],
                            },
                        },
                    },
                    "required": ["label", "text", "is_correct", "explanation", "missing_prerequisites"],
                },
            },
        },
        "required": ["question_stem", "options"],
    },
}


def load_keys() -> list[str]:
    """Always re-read from disk - the key pool changes during a session."""
    if not KEYS_PATH.is_file():
        raise SystemExit(f"ERROR: no key file at {KEYS_PATH}")
    keys = [
        line.strip()
        for line in KEYS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not keys:
        raise SystemExit(f"ERROR: {KEYS_PATH} is empty")
    return keys


class _ModelLimiter:
    """Rate-limit state for one (key, model) pair. Gemini quotas are per-model,
    not shared project-wide, so the same key running two models concurrently
    (generation on 3.5, verification on 3.1) has two independent budgets -
    each needs its own spacing/backoff/exhaustion tracking, not one shared one."""

    def __init__(self) -> None:
        self.min_interval = 60.0 / DEFAULT_RPM
        self.next_allowed = 0.0
        self.daily_count = 0
        self.exhausted = False
        # Counts fully-failed LOGICAL CALLS: a whole tuple attempt that
        # exhausted its own RETRY_DELAYS_SEC schedule without ever
        # succeeding - NOT individual 429 responses (that was tried and is
        # why this field exists; see note_call_exhausted's docstring).
        self.consecutive_failed_calls = 0
        # Per (key, model): serializes every outbound HTTP call for this
        # exact key+model pair. wait_for_turn() only paces calls against
        # the SAME model's _ModelLimiter, so nothing previously stopped two
        # verify_worker threads that round-robin onto the same key from
        # both being in flight for it at once (4 verify threads cycling
        # through 18 keys can easily lap a slow call). Holding this for the
        # whole wait+call+response cycle guarantees at most one in-flight
        # request per (key, model) at any time.
        #
        # Deliberately scoped to (key, model), NOT the whole key: Gemini's
        # quota is confirmed per-model (a real 429 body's quotaId reads
        # "GenerateRequestsPerDayPerProjectPerModel-FreeTier"), so
        # generation and verification calls for the same key were never
        # actually contending for the same budget. An earlier version of
        # this lock was scoped to the whole KeyState, shared across models -
        # that meant a verification call (gemini-3.1-flash-lite) holding the
        # lock, including its own wait_for_turn sleep, could delay the
        # generation worker (gemini-3.5-flash-lite) for that same key past
        # its intended send time. Confirmed directly: all 18 keys reported
        # "exhausted" by the pipeline mid-run, yet a standalone test of
        # every one of them - individually AND as a 15-way concurrent burst
        # across different keys - succeeded immediately. The delayed calls
        # were arriving bunched up once the shared lock freed, violating
        # the real per-model RPM window even though each model's own pacing
        # math looked correct in isolation.
        self.http_lock = threading.Lock()


class KeyState:
    """One API key, tracking a separate rate-limit budget per model it's used
    with (see _ModelLimiter)."""

    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label
        self.lock = threading.Lock()
        self._limiters: dict[str, _ModelLimiter] = {}

    def _limiter(self, model: str) -> _ModelLimiter:
        with self.lock:
            if model not in self._limiters:
                self._limiters[model] = _ModelLimiter()
            return self._limiters[model]

    def wait_for_turn(self, model: str) -> None:
        lim = self._limiter(model)
        # Compute-and-reserve under the lock, but sleep OUTSIDE it. This key's
        # generation and verification models share one KeyState (and one
        # lock) - holding the lock across a multi-second/minute sleep would
        # block the other model's calls on this same key for no reason, since
        # each model has its own independent _ModelLimiter budget.
        with self.lock:
            now = time.monotonic()
            wait = lim.next_allowed - now
            lim.next_allowed = max(lim.next_allowed, now) + lim.min_interval
        if wait > 0:
            time.sleep(wait)

    def note_success(self, model: str) -> None:
        lim = self._limiter(model)
        lim.consecutive_failed_calls = 0
        lim.daily_count += 1

    def note_rate_limited(self, model: str, retry_after: float | None, attempt: int) -> None:
        """
        Fixed retry schedule on a 429: RETRY_DELAYS_SEC (10s, 30s, 60s) for
        the 1st/2nd/3rd retry respectively, not adaptive and not driven by
        the server's own suggested retryDelay (logged for visibility only -
        Gemini sometimes hands back a RetryInfo.retryDelay measured in TENS
        OF MINUTES, a different quota bucket resetting, e.g. RPD; honoring
        that literally would mean one `time.sleep()` blocking this key/model
        for that entire duration with zero visibility, which looked exactly
        like a hung pipeline). After 3 retries all fail, the call is treated
        as timed out - see note_call_exhausted, called from gemini_generate's
        fallthrough once this key/model has been through the whole schedule
        without success.

        `attempt` is the CALLER's own local retry-loop index (0 = first
        try, before any retry), not a value stored on this object - an
        earlier version kept a persistent consecutive_429s counter here
        instead, incremented on every 429 and only reset on success. That
        meant a call that failed all 3 retries left the counter elevated
        for whatever call came next on this key+model, so a FRESH tuple's
        very first retry could be computed as if it were already deep into
        someone else's retry schedule (observed directly: log lines like
        "retry 5/3"). Taking the index from the caller's own loop variable
        means each call's retry schedule always starts at 10s truly fresh,
        regardless of what a previous, unrelated call did.

        Deliberately never marks the key exhausted by itself, however many
        times this fires - only note_call_exhausted (a count of whole
        fully-failed calls, not of individual 429s like this) does that.
        An earlier version marked exhausted directly from repeated 429s
        here, at two different thresholds, and both were false positives:
        a key marked "exhausted" this way answered a standalone test with
        HTTP 200 within minutes, twice, confirmed directly. Not this
        function's job to guess exhaustion - it only enforces the fixed
        wait between retries.
        """
        lim = self._limiter(model)
        delay = RETRY_DELAYS_SEC[min(attempt, len(RETRY_DELAYS_SEC) - 1)]
        with self.lock:
            lim.next_allowed = time.monotonic() + delay
        suggested = f", server suggested {retry_after:.1f}s" if retry_after else ""
        shown_attempt = min(attempt + 1, len(RETRY_DELAYS_SEC))
        print(f"[ratelimit] {self.label}/{model} retry {shown_attempt}/{len(RETRY_DELAYS_SEC)} "
              f"in {delay:.0f}s{suggested}")

    def note_call_exhausted(self, model: str) -> None:
        """
        Called once per LOGICAL CALL that exhausted its own MAX_429_RETRIES
        (MAX_429_RETRIES, currently 3, at the fixed RETRY_DELAYS_SEC
        schedule) without ever succeeding - not once per individual 429
        response.

        This replaces counting raw 429s (consecutive_429s) for exhaustion,
        because that reintroduced the exact false-positive this project
        already hit once before, just at a higher threshold. All 18 worker
        threads fire their first request within the same second or two at
        the start of a run - a real but brief startup burst. A single
        unlucky tuple's own retry loop can rack up 10+ consecutive 429s BY
        ITSELF within that one burst, tripping the old check before its own
        retry delay even got a chance to work. Confirmed directly, twice
        (2026-09-19): every key the pipeline marked "exhausted" answered a
        standalone test with HTTP 200 within minutes, both times.

        Counting fully-failed calls instead means 10 in a row: ten SEPARATE
        tuple attempts, each of which already went through the whole 3-try
        schedule, must ALL fail before giving up - a much stronger, more
        deliberate signal that a burst clearing on its own can't trip.
        """
        lim = self._limiter(model)
        with self.lock:
            lim.consecutive_failed_calls += 1
            if lim.consecutive_failed_calls >= CONSECUTIVE_429_EXHAUSTION_THRESHOLD:
                lim.exhausted = True
        if lim.exhausted and lim.consecutive_failed_calls == CONSECUTIVE_429_EXHAUSTION_THRESHOLD:
            print(f"[ratelimit] {self.label}/{model} marked EXHAUSTED after "
                  f"{CONSECUTIVE_429_EXHAUSTION_THRESHOLD} consecutive fully-failed calls "
                  f"- no longer retried this run")

    def mark_blocked(self, model: str) -> None:
        """Permanent per-key failure (401/403) - unlike rate-limiting, no
        backoff will fix this, so mark exhausted immediately."""
        self._limiter(model).exhausted = True

    def is_exhausted(self, model: str) -> bool:
        return self._limiter(model).exhausted

    def daily_count_for(self, model: str) -> int:
        return self._limiter(model).daily_count


MAX_429_RETRIES = len(RETRY_DELAYS_SEC)  # separate from MAX_RETRIES_PER_TUPLE - a rate limit is not a content problem


def gemini_generate(key_state: KeyState, model: str, system_prompt: str, user_prompt: str,
                     prior_turns: list[dict] | None = None,
                     response_schema: dict | None = RESPONSE_SCHEMA) -> tuple[object | None, str | None]:
    """
    One logical Gemini call against the given model, using this key's budget
    for THAT model specifically. Returns (parsed_json, error_message).

    429s (RPM/TPM limit hit) are retried HERE, with the backoff wait_for_turn
    already enforces, up to MAX_429_RETRIES - deliberately separate from the
    caller's MAX_RETRIES_PER_TUPLE budget, which exists for genuine content
    problems (bad schema, wrong answer). Without this split, a tuple that hit
    two transient rate limits and then produced valid content on the third
    try would be abandoned having "used up" its retries on infrastructure
    noise, not its own fault.
    """
    contents = list(prior_turns or [])
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    generation_config = {
        "temperature": 0.7,
        "responseMimeType": "application/json",
        "maxOutputTokens": 4096,
    }
    if response_schema is not None:
        generation_config["responseSchema"] = response_schema

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": generation_config,
    }
    url = f"{API_BASE}/{model}:generateContent?key={key_state.key}"

    last_retry_status: int | None = None
    for _429_attempt in range(MAX_429_RETRIES + 1):
        if key_state.is_exhausted(model):
            return None, "key exhausted"

        # Held across wait_for_turn's sleep AND the call itself: see
        # _ModelLimiter.http_lock's docstring for why this is scoped to
        # (key, model) and not the whole key. Holding it this early means a
        # second caller for the SAME key+model doesn't even start its own
        # wait_for_turn timer until the first caller's full cycle is done.
        with key_state._limiter(model).http_lock:
            key_state.wait_for_turn(model)
            # A fresh single-use executor per call, not a shared pool: if requests'
            # own timeout=60 fails to fire (observed platform issue) and the call
            # blocks forever past _HTTP_HARD_TIMEOUT_SEC, .result(timeout=...) only
            # abandons OUR wait - the underlying thread stays blocked forever. A
            # shared fixed-size pool would permanently lose that worker slot, and
            # after enough leaks (observed after ~40min/~650 calls under heavy
            # rate-limit retry volume) every slot is gone and ALL future calls
            # queue forever with zero free workers - a full stall. A disposable
            # one-off executor lets the leaked thread die alone without shrinking
            # capacity for calls that come after it.
            one_shot = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="gemini-http")
            try:
                resp = one_shot.submit(requests.post, url, json=payload, timeout=60) \
                    .result(timeout=_HTTP_HARD_TIMEOUT_SEC)
            except concurrent.futures.TimeoutError:
                return None, f"network error: hard timeout after {_HTTP_HARD_TIMEOUT_SEC}s (requests' own timeout did not fire)"
            except requests.RequestException as exc:
                return None, f"network error: {exc}"
            finally:
                one_shot.shutdown(wait=False)

        # 429 (rate limit) and transient 5xx (Gemini's own infrastructure
        # under load, e.g. 503 "This model is currently experiencing high
        # demand") get the SAME fixed retry treatment. Before this, only 429
        # did - a 503 fell straight through to the generic `!= 200` branch
        # below with zero retries, immediately failing the whole call.
        # Confirmed directly: a real Gemini-side 503 outage (2026-09-24)
        # permanently finalized 16 tuples with zero output and no chance to
        # retry, since generate_schema_valid_tuple's own error path treats
        # any non-429/non-"key exhausted" error as immediately final (see
        # gen_worker) - unlike a 429 timeout, which correctly requeues.
        # 401/403 (below) remain separate: those are permanent per-key
        # failures, not transient server-side ones, so still exhaust the
        # key immediately rather than retrying.
        if resp.status_code == 429 or resp.status_code in (500, 502, 503, 504):
            last_retry_status = resp.status_code
            retry_after = None
            if resp.status_code == 429:
                try:
                    body = resp.json()
                    for detail in body.get("error", {}).get("details", []):
                        if detail.get("@type", "").endswith("RetryInfo"):
                            delay = detail.get("retryDelay", "")
                            if delay.endswith("s"):
                                retry_after = float(delay[:-1])
                except Exception:
                    pass
            key_state.note_rate_limited(model, retry_after, _429_attempt)
            if key_state.is_exhausted(model):
                # Repeated failures even after backoff - stop hammering this
                # key for this model (daily cap for 429s; sustained outage
                # for 5xx - either way, no point in retrying anymore).
                return None, "key exhausted"
            continue  # wait_for_turn enforces the backoff on the next loop iteration

        if resp.status_code in (401, 403):
            # Permanent, per-key/project auth failure (e.g. "project denied
            # access") - unlike a 429, retrying the SAME key will never
            # succeed. Mark it exhausted immediately so the caller hands this
            # tuple to a different key right away instead of burning retry
            # attempts on a dead key.
            key_state.mark_blocked(model)
            return None, "key exhausted"

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:300]}"

        key_state.note_success(model)
        try:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # gen.repair_llm_json_escapes fixes undoubled backslashes (\tan,
            # \frac, ...) that json.loads() would otherwise silently eat as
            # control-character escapes - see its docstring for why this is
            # needed even for Gemini's structured output, not just local models.
            return json.loads(gen.repair_llm_json_escapes(text)), None
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            return None, f"parse error: {exc} | raw: {json.dumps(resp.json())[:300]}"

    # Every retry in the loop above was a 429/5xx and none ever succeeded -
    # one whole fully-failed logical call. See note_call_exhausted's
    # docstring for why exhaustion is counted here, not per individual
    # 429/5xx response. Report the actual last status seen (429 vs e.g. 503
    # are different real causes - a message that always says "429" even
    # when every retry was actually a 503 would be actively misleading).
    key_state.note_call_exhausted(model)
    return None, f"rate limited/unavailable (last status {last_retry_status}) - exhausted internal retries"


VERIFY_SYSTEM_PROMPT = (
    "You are a strict subject-matter expert grader AND relevance judge for "
    "Bangladesh university admission exams (Math/Physics/Chemistry). For each "
    "question, do two independent things: (1) judge whether it genuinely tests "
    "the stated TARGET SKILL specifically - not just the same subject/topic, "
    "the exact skill - and (2) solve the question yourself from scratch using "
    "only the stem and options given, then state which option is correct. Do "
    "not assume any option is marked correct - work it out independently."
)

VERIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "results": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "on_topic": {"type": "BOOLEAN"},
                    "correct_answer": {"type": "STRING", "enum": ["A", "B", "C", "D"]},
                },
                "required": ["on_topic", "correct_answer"],
            },
        },
    },
    "required": ["results"],
}


def verify_batch_combined(
    items: list[tuple[dict, list]], key_state: KeyState,
) -> list[tuple[bool, list[tuple[bool, bool | None]]]]:
    """
    Two independent judgments per question - (a) does it test its own target
    skill, (b) an independent blind re-solve compared against the marked
    answer - across MANY tuples in one call instead of one call per tuple.
    Cuts verification call COUNT roughly N-fold for a batch of N tuples,
    directly easing whatever RPM limit is the real bottleneck (TPM isn't
    close to being hit by these modest per-call token counts).

    Each question is labeled by (tuple_index, question_index) in the prompt
    so results route back to the right tuple regardless of batch size.
    Judgments stay per-question and independent either way - batching two
    already-independent judges together doesn't reintroduce the
    self-assessment bias that folding a check into generation itself would.

    items: list of (tup, questions) pairs. Returns, per item in the same
    order: (call_succeeded, [(on_topic, answer_matches), ...]) - always
    True/real verdicts now, since a failed call raises instead (see below).

    Raises RuntimeError if the call itself didn't produce a usable response
    at all - callers must retry, not treat that as a verdict.
    """
    blocks = []
    for ti, (tup, questions) in enumerate(items):
        for qi, q in enumerate(questions):
            lines = [f"টিউপল {ti + 1}.{qi + 1} (দক্ষতা: {tup['skillFull']}): {q.get('question_stem', '')}"]
            for o in q.get("options", []):
                lines.append(f"  {o.get('label')}) {o.get('text')}")
            blocks.append("\n".join(lines))

    total_questions = sum(len(qs) for _, qs in items)
    prompt = (
        "নিচের প্রতিটি প্রশ্নের জন্য:\n"
        "(ক) এটি কি তার নিজস্ব দক্ষতা (প্রতিটির পাশে বন্ধনীতে দেওয়া) সরাসরি পরীক্ষা করে?\n"
        "(খ) নিজে সমাধান করে সঠিক অপশন (A/B/C/D) নির্বাচন করো — কোনো অপশনকে সঠিক ধরে না নিয়ে।\n\n"
        + "\n\n".join(blocks)
        + '\n\nশুধুমাত্র JSON দাও: {"results": [{"on_topic": true/false, "correct_answer": "A"}, ...]} '
        "— উপরের ক্রম অনুযায়ী (টিউপল ১-এর সব প্রশ্ন প্রথমে, তারপর টিউপল ২, ইত্যাদি)।"
    )
    parsed, err = gemini_generate(
        key_state, ANSWER_VERIFICATION_MODEL, VERIFY_SYSTEM_PROMPT, prompt,
        response_schema=VERIFY_SCHEMA,
    )
    if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list) \
            or len(parsed["results"]) != total_questions:
        # The call itself didn't produce a usable response (network/rate-limit
        # failure, or a malformed body) - NOT a verdict that every question
        # passed. Raising (instead of the previous
        # `return [(False, [(True, None)] * len(qs)) for _, qs in items]`)
        # lets callers distinguish "not verified" from "call failed, retry":
        # verify_worker already has a try/except around this call that
        # requeues on exception, but the old return value bypassed it
        # entirely - on_topic=True/answer_ok=None never triggers verify_worker's
        # rejection branch, so a failed call was silently treated as "every
        # question passed" and could reach the final corpus, just tagged
        # _verified=False in metadata nothing downstream checks. Same bug
        # class as audit_questions.py's VerifyCallFailed, fixed there first;
        # this was the one other place it existed. combined_validity (the
        # other caller) already wraps this call in try/except and treats an
        # exception as "not valid" either way, so this doesn't change its
        # behavior.
        raise RuntimeError(f"verify call failed: {err or 'malformed response'}")

    flat = parsed["results"]
    out: list[tuple[bool, list[tuple[bool, bool | None]]]] = []
    idx = 0
    for _tup, questions in items:
        per_q: list[tuple[bool, bool | None]] = []
        for q in questions:
            r = flat[idx]
            idx += 1
            if not isinstance(r, dict):
                per_q.append((True, None))
                continue
            on_topic = bool(r.get("on_topic", True))
            marked = next((o.get("label") for o in q.get("options", []) if o.get("is_correct")), None)
            ans = r.get("correct_answer")
            answer_ok = (str(ans).strip().upper() == marked) if ans else None
            per_q.append((on_topic, answer_ok))
        out.append((True, per_q))
    return out


def generate_schema_valid_tuple(
    retriever: Retriever, tup: dict, key_state: KeyState, generation_model: str,
) -> tuple[list, dict | None, str, str | None]:
    """
    Generation + schema-validation retry loop ONLY - verification is no
    longer called here, since it now happens separately, batched across many
    tuples at once (see verify_batch_combined). Returns
    (questions, hits_dict_or_None, subject, error). On success, `questions`
    are schema-valid but NOT yet verified - the caller is responsible for
    routing them through batched verification before treating them as final.
    """
    subject = gen.tuple_subject(tup)
    hits = retriever.retrieve_for_tuple(
        topic_label=tup["topicLabel"], skill_full=tup["skillFull"],
        bloom=tup["bloom"], subject=subject, top_k=gen.TOP_K,
    )
    prereq_list = gen.get_prereq_list_for_skill(tup["skillId"])
    prereq_ids = {p["id"] for p in gen.prereqs_raw.get(tup["skillId"], []) if isinstance(p, dict) and "id" in p}

    user_prompt = gen.USER_PROMPT_TEMPLATE.format(
        N=gen.N_QUESTIONS, SUBJECT=subject, BLOOM_LEVEL=tup["bloom"],
        SKILL_ID=tup["skillId"], SKILL_FULL=tup["skillFull"], TOPIC_LABEL=tup["topicLabel"],
        BLOOM_GUIDANCE=gen.BLOOM_GUIDANCE.get(tup["bloom"], ""),
        PREREQ_LIST=prereq_list or "(empty)",
        REFERENCE_BLOCKS=gen.format_reference_blocks(hits),
    )

    prior_turns: list[dict] = []
    last_err = "exhausted retries without a definitive error"
    for _attempt in range(MAX_RETRIES_PER_TUPLE + 1):
        if key_state.is_exhausted(generation_model):
            return [], None, subject, "key exhausted"
        parsed, err = gemini_generate(key_state, generation_model, gen.SYSTEM_PROMPT, user_prompt, prior_turns)
        if parsed is None or not isinstance(parsed, list):
            last_err = err or f"generation model returned non-list: {parsed!r:.200}"
            if err == "key exhausted":
                return [], None, subject, "key exhausted"
            continue  # 429s are already retried inside gemini_generate; this is a parse issue

        questions = gen.normalize_questions(parsed)
        errors = gen.validate_questions(questions, tup["skillId"], tup["bloom"], prereq_ids)
        if not errors:
            for q in questions:
                q.setdefault("skill_description", tup["skillFull"])
                q.setdefault("topic", tup["topicLabel"])
                q["subject"] = subject
            return questions, hits, subject, None

        last_err = "; ".join(errors[:6])
        prior_turns = [
            {"role": "user", "parts": [{"text": user_prompt}]},
            {"role": "model", "parts": [{"text": json.dumps(parsed, ensure_ascii=False)}]},
        ]
        user_prompt = (
            "Fix these issues and regenerate the FULL JSON array only.\n- "
            + "\n- ".join(errors[:12])
        )

    return [], None, subject, last_err


def combined_validity(tup: dict, questions: list, key_state: KeyState) -> list[bool]:
    """
    Per-question boolean from ONE verify_batch_combined call: True iff the
    question is on-topic AND the verifier's independent re-solve doesn't
    disagree with the marked answer (answer_ok is True or None - None means
    "couldn't determine", which was never treated as a failure here). False
    for every question if the call itself failed outright, since there's no
    per-question signal to fall back on.
    """
    try:
        ok_call, checks = verify_batch_combined([(tup, questions)], key_state)[0]
    except Exception:
        ok_call, checks = False, []
    if not ok_call:
        return [False] * len(questions)
    return [on_topic and (answer_ok is not False) for on_topic, answer_ok in checks]


def generate_verified_pool(
    retriever: Retriever, tup: dict, key_state: KeyState, generation_model: str,
    is_valid: Callable[[dict, list, KeyState], list[bool]],
    target_count: int = gen.N_QUESTIONS,
    max_attempts: int = MAX_RETRIES_PER_TUPLE,
) -> tuple[list[dict], str | None]:
    """
    Generates schema-valid candidates for `tup` in batches (each
    generate_schema_valid_tuple call naturally returns up to N_QUESTIONS
    candidates), verifies each batch via `is_valid(tup, questions, key_state)
    -> list[bool]`, and ACCUMULATES every individually-valid candidate across
    attempts - a batch that yields only 1 or 2 valid candidates out of 3
    still contributes those, rather than the whole batch being discarded for
    one bad sibling (the old behavior: any single failure meant a full fresh
    regeneration, throwing away candidates that were actually fine).

    Keeps generating fresh batches until the accumulated valid pool reaches
    at least target_count, or max_attempts is exhausted. May return MORE
    than target_count - a batch can push the pool past the line in one
    step - callers that only strictly need target_count treat the rest as
    a bonus surplus, not something to truncate.

    Returns (accumulated_valid_questions, last_error_or_None). The error is
    None whenever accumulated is non-empty (partial progress isn't a
    failure), even if target_count was never fully reached.
    """
    accumulated: list[dict] = []
    last_err: str | None = None
    for _attempt in range(max_attempts):
        if len(accumulated) >= target_count:
            break
        try:
            questions, hits, subject, err = generate_schema_valid_tuple(
                retriever, tup, key_state, generation_model
            )
        except Exception as exc:  # noqa: BLE001
            last_err = f"unhandled exception: {exc!r}"
            continue
        if not questions:
            last_err = err
            continue
        try:
            valid = is_valid(tup, questions, key_state)
        except Exception as exc:  # noqa: BLE001
            last_err = f"verify exception: {exc!r}"
            continue
        if hits is not None:
            valid_questions = [q for q, ok in zip(questions, valid) if ok]
            if valid_questions:
                gen.attach_source_refs(valid_questions, hits)
        for q, ok in zip(questions, valid):
            if ok:
                q.setdefault("skill_description", tup["skillFull"])
                q.setdefault("topic", tup["topicLabel"])
                q["subject"] = subject
                accumulated.append(q)
    return accumulated, (None if accumulated else last_err)


def stratified_sample(topics_per_subject: int) -> list[dict]:
    """
    Pick up to N distinct topics per subject (one skill per topic), then
    expand each to all 6 Bloom levels. tuples.json is grouped in contiguous
    subject blocks, so a plain --limit only ever samples one subject.
    """
    base = json.loads(gen.TUPLES_PATH.read_text(encoding="utf-8"))
    by_subject: dict[str, dict[str, dict]] = {}
    for tup in base:
        subj = tup.get("subject") or gen.tuple_subject(tup)
        by_subject.setdefault(subj, {}).setdefault(tup["topicKey"], tup)  # first skill per topic

    selected: list[dict] = []
    for subj, by_topic in by_subject.items():
        for tup in list(by_topic.values())[:topics_per_subject]:
            selected.append(tup)

    expanded: list[dict] = []
    for tup in selected:
        for bloom in gen.BLOOM_LEVELS:
            item = dict(tup)
            item["bloom"] = bloom
            expanded.append(item)
    return expanded


def main() -> None:
    try:
        # Default stdout buffering is fully block-buffered when redirected to a
        # file/pipe (the normal case for a long background run), so prints sit
        # unflushed for arbitrarily long - making a live-tailed log or a killed
        # process's captured output useless for diagnosing a stall. Force line
        # buffering so every print is visible immediately.
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N tuples (pilot mode).")
    parser.add_argument(
        "--sample-topics", type=int, default=0,
        help="Stratified pilot: N distinct topics per subject (Math/Physics/Chemistry), all 6 Bloom levels each.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=0,
        help="Process only the next N not-yet-done tuples from the FULL 2580-tuple list (for the real run in "
             "discrete, validate-between-batches chunks), rather than the whole remaining set at once.",
    )
    parser.add_argument(
        "--real", action="store_true",
        help=f"Use {REAL_MODEL} (spends real quota). Default is {TEST_MODEL} for pilots/tests.",
    )
    args = parser.parse_args()

    global GENERATION_MODEL
    GENERATION_MODEL = REAL_MODEL if args.real else TEST_MODEL

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(
        f"Generation model: {GENERATION_MODEL}"
        f"{'  (REAL RUN - spends production quota)' if args.real else '  (test model)'}"
    )
    print(f"Verification model: {ANSWER_VERIFICATION_MODEL} (always, regardless of --real)")
    keys = load_keys()
    print(f"Loaded {len(keys)} API keys from {KEYS_PATH}")
    key_states = [KeyState(k, f"key{i+1}") for i, k in enumerate(keys)]

    print("Loading retriever + KB ...")
    retriever = Retriever()
    print(f"KB size: {len(retriever.items)} items")

    # Resume support: load what's already completed before selecting tuples,
    # so --batch-size can slice the NOT-yet-done portion of the full list.
    done_keys: set[tuple] = set()
    all_questions: list = []
    if OUTPUT_PATH.exists():
        try:
            all_questions = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            all_questions = []
    if PROGRESS_PATH.exists():
        try:
            done_list = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
            done_keys = {tuple(x) for x in done_list}
        except json.JSONDecodeError:
            pass

    if args.sample_topics:
        tuples_list = stratified_sample(args.sample_topics)
        by_subj = {}
        for t in tuples_list:
            by_subj[t.get("subject")] = by_subj.get(t.get("subject"), 0) + 1
        print(f"Stratified sample: {args.sample_topics} topics/subject -> {dict(by_subj)}")
    elif args.batch_size:
        full_list = gen.tuples if isinstance(gen.tuples, list) else [gen.tuples]
        not_done = [t for t in full_list if (t["skillId"], t["bloom"]) not in done_keys]
        print(f"Full tuple set: {len(full_list)} | not yet done: {len(not_done)}")
        tuples_list = not_done[: args.batch_size]
    else:
        tuples_list = gen.tuples if isinstance(gen.tuples, list) else [gen.tuples]
        if args.limit:
            tuples_list = tuples_list[: args.limit]
    print(f"Tuples to generate: {len(tuples_list)}")

    work_q: "queue.Queue[tuple[int, dict]]" = queue.Queue()
    for i, tup in enumerate(tuples_list):
        k = (tup["skillId"], tup["bloom"])
        if list(k) not in [list(d) for d in done_keys]:
            work_q.put((i, tup))
    total_to_do = work_q.qsize()
    print(f"Already done (resume): {len(tuples_list) - total_to_do} | remaining: {total_to_do}")

    out_lock = threading.Lock()
    stats = {"ok": 0, "failed": 0}
    stats_lock = threading.Lock()

    # Two-phase pipeline: generation workers produce schema-valid (but not yet
    # verified) tuples into pending_verify_q; separate verifier threads drain
    # it in batches so ONE verification call covers many tuples at once,
    # instead of one call per tuple. `in_flight` tracks every tuple that has
    # not yet reached a terminal state (finalized success or permanent
    # failure) - set ONCE to the total queued count, and ONLY ever
    # decremented (in finalize_success/finalize_failure), never
    # re-incremented. A verification failure requeues onto work_q for another
    # generation attempt WITHOUT touching in_flight at all - it must not be
    # bumped again on that re-pull, or a tuple that gets requeued even once
    # inflates the counter permanently, in_flight never reaches 0, and every
    # worker spins in `while not all_done()` forever (a real bug this was:
    # the pull-from-work_q site used to increment on EVERY pull, requeues
    # included, despite a comment claiming otherwise - confirmed by two
    # separate hangs where ok+failed exactly matched the batch size, i.e.
    # every tuple truly finished, yet the process never exited).
    # All worker loops exit once in_flight reaches 0 and work_q is empty.
    pending_verify_q: "queue.Queue[tuple[int, dict, list, dict | None, str]]" = queue.Queue()
    in_flight = {"n": total_to_do}
    flight_lock = threading.Lock()
    verify_retry_count: dict[tuple, int] = {}
    # A batch that yields only 1 or 2 valid questions out of gen.N_QUESTIONS
    # is no longer discarded wholesale for one bad sibling - the valid ones
    # accumulate here across verify rounds for the same tuple, and the tuple
    # only finalizes once its pool reaches gen.N_QUESTIONS (or retries run
    # out, in which case whatever accumulated is used rather than nothing).
    accumulated_per_tuple: dict[tuple, list] = {}
    accum_lock = threading.Lock()
    MAX_VERIFY_RETRIES = 2

    # Set when the watchdog below detects every key is exhausted for
    # GENERATION_MODEL with tuples still stuck in work_q - a state no
    # worker can ever clear on its own. Without this, gen_workers exit
    # (each checks is_exhausted() and returns), but verify_workers keep
    # looping in `while not all_done()` forever: pending_verify_q goes
    # empty and stays empty (nothing left generates), yet work_q is
    # non-empty and nothing is left alive to drain it, so all_done() can
    # never become True. Observed directly (2026-09-19): the process sat
    # alive but fully idle for ~1h45m after every key hit the new
    # consecutive-429 exhaustion threshold, with zero indication anything
    # was wrong short of noticing the progress file had stopped moving.
    stuck = threading.Event()

    def all_done() -> bool:
        if stuck.is_set():
            return True
        with flight_lock:
            return in_flight["n"] == 0 and work_q.empty() and pending_verify_q.empty()

    def watchdog() -> None:
        while not stuck.is_set():
            time.sleep(15)
            with flight_lock:
                nothing_pending_verify = pending_verify_q.empty()
                work_left = work_q.qsize()
            if in_flight["n"] == 0:
                return  # legitimately finished, not stuck
            if work_left > 0 and nothing_pending_verify and \
                    all(ks.is_exhausted(GENERATION_MODEL) for ks in key_states):
                print(f"\n[FATAL] All {len(key_states)} keys are exhausted for "
                      f"{GENERATION_MODEL} and {work_left} tuple(s) remain unprocessed. "
                      f"No key can make further progress this run - stopping instead of "
                      f"spinning forever. Re-run once at least one key's quota has reset.")
                stuck.set()
                return

    def finalize_success(tup: dict, questions: list, verified_ok: bool) -> None:
        with out_lock:
            all_questions.extend(questions)
            done_keys.add((tup["skillId"], tup["bloom"]))
            OUTPUT_PATH.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2), encoding="utf-8")
            PROGRESS_PATH.write_text(json.dumps([list(d) for d in done_keys], ensure_ascii=False), encoding="utf-8")
        with stats_lock:
            stats["ok"] += 1
            print(f"[verify] OK {tup['skillId']}@{tup['bloom']} (verified={verified_ok}) "
                  f"(total ok={stats['ok']} failed={stats['failed']})")
        with flight_lock:
            in_flight["n"] -= 1

    def finalize_failure(tup: dict, reason: str, source: str) -> None:
        with out_lock:
            done_keys.add((tup["skillId"], tup["bloom"]))
            PROGRESS_PATH.write_text(json.dumps([list(d) for d in done_keys], ensure_ascii=False), encoding="utf-8")
        with stats_lock:
            stats["failed"] += 1
            print(f"[{source}] FAILED {tup['skillId']}@{tup['bloom']}: {reason}")
        with flight_lock:
            in_flight["n"] -= 1

    def gen_worker(key_state: KeyState) -> None:
        while not all_done():
            if key_state.is_exhausted(GENERATION_MODEL):
                return
            try:
                idx, tup = work_q.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                questions, hits, subject, err = generate_schema_valid_tuple(
                    retriever, tup, key_state, GENERATION_MODEL
                )
            except Exception as exc:  # noqa: BLE001 - must never leave in_flight permanently stuck
                finalize_failure(tup, f"unhandled exception: {exc!r}", "gen")
                continue
            if questions:
                pending_verify_q.put((idx, tup, questions, hits, subject))
            else:
                if err == "key exhausted":
                    work_q.put((idx, tup))  # still in_flight - another gen thread/key will pick it up
                    return  # this key really is done - stop this worker
                if err and "exhausted internal retries" in err:
                    # This tuple timed out on this key (see RETRY_DELAYS_SEC /
                    # note_call_exhausted), but the key itself isn't
                    # necessarily exhausted - is_exhausted() may still be
                    # False. Requeue the TUPLE for another shot (maybe a
                    # different key, maybe this one again later), but keep
                    # this worker going rather than exiting: previously this
                    # fell through to finalize_failure, permanently marking
                    # the tuple "done" (indistinguishable from success) after
                    # one bad run of luck - a real data-loss bug, worse once
                    # MAX_429_RETRIES dropped from 12 to 3 (a tuple hits this
                    # far more easily now).
                    work_q.put((idx, tup))  # still in_flight - not done, no key exhaustion either
                    continue
                finalize_failure(tup, err or "unknown generation error", "gen")

    verify_key_idx = {"i": 0}
    verify_idx_lock = threading.Lock()

    def next_verify_key() -> KeyState:
        with verify_idx_lock:
            ks = key_states[verify_key_idx["i"] % len(key_states)]
            verify_key_idx["i"] += 1
        return ks

    def verify_worker() -> None:
        while not all_done():
            batch: list[tuple[int, dict, list, dict | None, str]] = []
            try:
                batch.append(pending_verify_q.get(timeout=VERIFY_BATCH_WAIT))
            except queue.Empty:
                continue
            while len(batch) < BATCH_VERIFY_SIZE:
                try:
                    batch.append(pending_verify_q.get_nowait())
                except queue.Empty:
                    break

            key_state = next_verify_key()
            items = [(tup, questions) for (_idx, tup, questions, _hits, _subject) in batch]
            try:
                results = verify_batch_combined(items, key_state)
            except Exception as exc:  # noqa: BLE001 - must never leave in_flight permanently stuck
                for idx, tup, questions, hits, subject in batch:
                    key = (tup["skillId"], tup["bloom"])
                    verify_retry_count[key] = verify_retry_count.get(key, 0) + 1
                    if verify_retry_count[key] <= MAX_VERIFY_RETRIES:
                        work_q.put((idx, tup))  # still in_flight - cycling back, don't decrement
                        print(f"[verify] RETRY {tup['skillId']}@{tup['bloom']} "
                              f"after unhandled exception: {exc!r}")
                    else:
                        finalize_failure(tup, f"unhandled exception: {exc!r}", "verify")
                continue

            for (idx, tup, questions, hits, subject), (verified_ok, checks) in zip(batch, results):
                key = (tup["skillId"], tup["bloom"])
                problems = []
                valid_questions = []
                for i, (q, (on_topic, answer_ok)) in enumerate(zip(questions, checks)):
                    if not on_topic:
                        problems.append(f"q[{i}] off-topic for {tup['skillFull']!r}")
                    elif answer_ok is False:
                        problems.append(f"q[{i}] independent re-solve disagrees with marked answer")
                    else:
                        valid_questions.append(q)

                if hits is not None and valid_questions:
                    gen.attach_source_refs(valid_questions, hits)
                for q in valid_questions:
                    q["_verified"] = verified_ok

                with accum_lock:
                    pool = accumulated_per_tuple.setdefault(key, [])
                    pool.extend(valid_questions)
                    pool_len = len(pool)
                    final_pool = accumulated_per_tuple.pop(key) if pool_len >= gen.N_QUESTIONS else None

                if final_pool is not None:
                    finalize_success(tup, final_pool, verified_ok)
                    continue

                # Not enough valid questions yet for this tuple - top up with
                # another generation round instead of discarding what's
                # already accumulated.
                verify_retry_count[key] = verify_retry_count.get(key, 0) + 1
                if verify_retry_count[key] <= MAX_VERIFY_RETRIES:
                    work_q.put((idx, tup))  # still in_flight - cycling back, don't decrement
                    print(f"[verify] RETRY {tup['skillId']}@{tup['bloom']} "
                          f"(attempt {verify_retry_count[key]}, have {pool_len}/{gen.N_QUESTIONS} valid so far): "
                          f"{'; '.join(problems[:3])}")
                else:
                    with accum_lock:
                        leftover = accumulated_per_tuple.pop(key, [])
                    if leftover:
                        print(f"[verify] PARTIAL {tup['skillId']}@{tup['bloom']}: accepting "
                              f"{len(leftover)}/{gen.N_QUESTIONS} valid after exhausting retries")
                        finalize_success(tup, leftover, verified_ok=False)
                    else:
                        finalize_failure(tup, "; ".join(problems[:6]), "verify")

    N_VERIFY_WORKERS = min(4, len(key_states))
    gen_threads = [threading.Thread(target=gen_worker, args=(ks,), daemon=True) for ks in key_states]
    verify_threads = [threading.Thread(target=verify_worker, daemon=True) for _ in range(N_VERIFY_WORKERS)]
    watchdog_thread = threading.Thread(target=watchdog, daemon=True)

    start = time.time()
    for t in gen_threads + verify_threads + [watchdog_thread]:
        t.start()
    for t in gen_threads + verify_threads:
        t.join()
    elapsed = time.time() - start

    if stuck.is_set():
        print(f"\nStopped after {elapsed:.1f}s (all keys exhausted, work remaining) - "
              f"ok={stats['ok']} failed={stats['failed']} total_questions={len(all_questions)}")
    else:
        print(f"\nDone in {elapsed:.1f}s. ok={stats['ok']} failed={stats['failed']} "
              f"total_questions={len(all_questions)}")
    for ks in key_states:
        gen_calls = ks.daily_count_for(GENERATION_MODEL)
        gen_exh = ks.is_exhausted(GENERATION_MODEL)
        verify_calls = ks.daily_count_for(ANSWER_VERIFICATION_MODEL)
        verify_exh = ks.is_exhausted(ANSWER_VERIFICATION_MODEL)
        print(f"  {ks.label}: generation={gen_calls} calls (exhausted={gen_exh}) | "
              f"verification={verify_calls} calls (exhausted={verify_exh})")


if __name__ == "__main__":
    main()
