"""
Standalone progress/ETA check for the Gemini generation run - independent of
any running batch, safe to run anytime (read-only, touches nothing the
generator itself owns except a small timestamp marker used only for ETA math).

Run from data-gen/:
    python check_progress.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_DATA_GEN = Path(__file__).resolve().parent
PROGRESS_PATH = _DATA_GEN / "gemini_progress.json"
OUTPUT_PATH = _DATA_GEN / "output_questions_gemini.json"
MARKER_PATH = _DATA_GEN / "gemini_run_started_at.json"
TOTAL_TUPLES = 2580


def load_done_count() -> int:
    if not PROGRESS_PATH.exists():
        return 0
    try:
        return len(json.loads(PROGRESS_PATH.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return 0


def load_question_count() -> int:
    if not OUTPUT_PATH.exists():
        return 0
    try:
        return len(json.loads(OUTPUT_PATH.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return 0


def get_or_create_marker(done_now: int) -> tuple[float, int]:
    """
    (timestamp, done_count) recorded the FIRST time this script ever runs -
    a stable zero-point so ETA math works across many separate batch
    invocations, restarts, and architecture changes (like the batch-
    verification rewrite), rather than resetting every time a new batch
    process starts. Delete gemini_run_started_at.json to reset the baseline
    (e.g. after a major pipeline change makes older throughput data stale).
    """
    if MARKER_PATH.exists():
        try:
            data = json.loads(MARKER_PATH.read_text(encoding="utf-8"))
            return data["timestamp"], data["done_count"]
        except (json.JSONDecodeError, KeyError):
            pass
    now = time.time()
    MARKER_PATH.write_text(json.dumps({"timestamp": now, "done_count": done_now}), encoding="utf-8")
    return now, done_now


def format_duration(seconds: float) -> str:
    if seconds < 0 or seconds != seconds:  # negative or NaN
        return "unknown"
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    done = load_done_count()
    questions = load_question_count()
    remaining = TOTAL_TUPLES - done

    marker_time, marker_done = get_or_create_marker(done)
    elapsed = time.time() - marker_time
    done_since_marker = done - marker_done

    print(f"Progress: {done} / {TOTAL_TUPLES} tuples done ({100*done/TOTAL_TUPLES:.1f}%)")
    print(f"Questions stored: {questions}")
    print(f"Remaining: {remaining} tuples")
    print()

    if elapsed < 60 or done_since_marker <= 0:
        print("Not enough elapsed time/progress yet since the baseline marker to estimate a rate.")
        print(f"(baseline set {format_duration(elapsed)} ago, {done_since_marker} tuples done since then)")
        return

    rate_per_min = done_since_marker / (elapsed / 60.0)
    eta_seconds = (remaining / rate_per_min) * 60.0 if rate_per_min > 0 else float("inf")

    print(f"Rate since baseline: {rate_per_min:.2f} tuples/min "
          f"({done_since_marker} tuples in {format_duration(elapsed)})")
    print(f"Estimated time remaining: {format_duration(eta_seconds)}")
    print()
    print("Note: this rate reflects whatever pipeline version has been running since the")
    print("baseline was set. If you just changed the code (e.g. batch verification), delete")
    print("gemini_run_started_at.json once to reset the baseline to NOW, so the ETA reflects")
    print("the new version's real throughput instead of blending it with older, slower data.")


if __name__ == "__main__":
    main()
