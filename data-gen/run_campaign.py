"""
Runs one full attempt of the question-generation campaign end to end:
checks API key health, runs generation (real model) until either every
tuple is done or every key is exhausted for the day (generate_question_gemini.py
already detects that and stops on its own via its watchdog thread - this
script doesn't re-implement that), then pushes whatever was generated to
Supabase. Shows a live progress bar (tuples done) with a running count of
generated questions the whole time.

Pure Python, no shell script - works the same on any machine with the venv
set up (Windows/Mac/Linux), no Git Bash or PowerShell needed.

Safe to re-run as many times as you like (e.g. once a day after keys
reset): generation resumes from gemini_progress_v2.json automatically, and
the Supabase push dedups against what's already there. Nothing here is
destructive.

Usage (run from the data-gen/ directory, with the venv active or its
python.exe used directly). All arguments pass straight through to
generate_question_gemini.py:
    python run_campaign.py --real               # full real run (spends production quota)
    python run_campaign.py --limit 6             # small pilot, cheap test model (no --real)
    python run_campaign.py --real --limit 6      # small pilot, real model

Requires: venv set up per README.md section 7, keys/.gemini_keys, and
Backend/.env (SUPABASE_URL / SUPABASE_SERVICE_KEY).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

HERE = Path(__file__).resolve().parent
PY = sys.executable  # whatever interpreter is running this script
PROGRESS_PATH = HERE / "gemini_progress_v2.json"
OUTPUT_PATH = HERE / "output_questions_gemini_v2.json"
KEYS_PATH = HERE.parent / "keys" / ".gemini_keys"


def load_keys() -> list[str]:
    if not KEYS_PATH.is_file():
        raise SystemExit(f"ERROR: no key file at {KEYS_PATH}")
    return [line.strip() for line in KEYS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_key_health(model: str) -> None:
    print(f"=== 1/3: checking API key health ({model}) ===")
    keys = load_keys()
    ok = 0
    for i, key in enumerate(keys, 1):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=20)
            status = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            status = f"REQUEST ERROR {exc!r}"
        print(f"  key{i}: {status}")
        if status == "OK":
            ok += 1
        time.sleep(0.3)
    print(f"\n{ok}/{len(keys)} keys healthy right now.")
    if ok == 0:
        print(
            "WARNING: no key is currently usable - the run below will likely "
            "stop almost immediately (generate_question_gemini.py's watchdog "
            "detects an all-keys-exhausted state and stops cleanly rather than "
            "hanging). Consider waiting for quota reset before running this."
        )


def tuples_done() -> int:
    try:
        return len(json.loads(PROGRESS_PATH.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return 0


def questions_generated() -> int:
    try:
        return len(json.loads(OUTPUT_PATH.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return 0


def read_total_from_log(log_path: Path) -> int:
    """The tuple total depends on --limit/--sample-topics if passed, so read
    it back from the run's own "Tuples to generate: N" line instead of
    hardcoding it."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return 0
    for line in text.splitlines():
        if "Tuples to generate:" in line:
            try:
                return int(line.split("Tuples to generate:")[1].strip())
            except ValueError:
                return 0
    return 0


def run_generation(extra_args: list[str]) -> Path:
    mode = "REAL - spends production quota" if "--real" in extra_args else "test model"
    print(f"\n=== 2/3: running generation ({mode}) ===")
    print("    (resumes automatically from gemini_progress_v2.json; stops cleanly")
    print("     on its own once either every tuple is done or every key is")
    print("     exhausted for today - re-run this script again later either way)")

    log_path = HERE / f"gemini_run_{datetime.now():%Y%m%d_%H%M%S}.log"
    print(f"    full log: {log_path.name}\n")

    start_done = tuples_done()
    start_questions = questions_generated()

    with open(log_path, "w", encoding="utf-8") as log_f:
        proc = subprocess.Popen(
            [PY, "generate_question_gemini.py", *extra_args],
            stdout=log_f, stderr=subprocess.STDOUT, cwd=HERE,
        )

        total = 0
        for _ in range(180):  # up to 3 minutes for KB/model loading to finish
            if proc.poll() is not None:
                break
            total = read_total_from_log(log_path)
            if total:
                break
            time.sleep(1)

        if not total:
            print(f"  (couldn't read the tuple total yet - no progress bar; check {log_path.name} directly)")
            proc.wait()
        else:
            with tqdm(total=total, initial=start_done, unit="tuple", desc="tuples") as bar:
                last_done = start_done
                while proc.poll() is None:
                    cur_done = tuples_done()
                    if cur_done > last_done:
                        bar.update(cur_done - last_done)
                        last_done = cur_done
                    bar.set_postfix(questions=questions_generated())
                    time.sleep(5)
                # final catch-up after the process exits
                cur_done = tuples_done()
                if cur_done > last_done:
                    bar.update(cur_done - last_done)
                bar.set_postfix(questions=questions_generated())

    if proc.returncode != 0:
        print(f"\n  generation exited with code {proc.returncode} - check {log_path.name} for details")

    net_questions = questions_generated() - start_questions
    print(f"\n  {tuples_done() - start_done} new tuple(s) completed this run, "
          f"{net_questions} new question(s) generated.")

    tail = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-8:]
    print("  --- last log lines ---")
    for line in tail:
        print(f"  {line}")

    return log_path


def push_to_supabase() -> None:
    print("\n=== 3/3: pushing generated questions to Supabase ===")
    subprocess.run(
        [PY, "load_questions_to_supabase.py", "--input", str(OUTPUT_PATH)],
        cwd=HERE, check=False,
    )


def print_summary() -> None:
    print("\n=== summary ===")
    done = tuples_done()
    qs = questions_generated()
    print(f"tuples completed: {done} / 10128")
    print(f"total questions in local corpus file: {qs}")
    if done < 10128:
        print(
            f"\n{10128 - done} tuples remain. Re-run this script "
            f"(python run_campaign.py) to continue - it will resume automatically, "
            f"whether that's now, after a short wait, or tomorrow once quota resets."
        )
    else:
        print("\nAll tuples done.")


REAL_MODEL = "gemini-3.5-flash-lite"
TEST_MODEL = "gemini-3.1-flash-lite"


def main() -> None:
    extra_args = sys.argv[1:]
    # Always check against REAL_MODEL specifically, even for a --limit test-
    # model pilot: Gemini's quota is per-model
    # (GenerateRequestsPerDayPerProjectPerModel-FreeTier, confirmed directly
    # against a real 429 body), so gemini-3.1-flash-lite being healthy says
    # nothing about gemini-3.5-flash-lite's quota - the model that actually
    # matters, since it's what --real spends. Checking the wrong model here
    # is exactly how an earlier run got its "keys are back up" signal wrong.
    check_key_health(REAL_MODEL)
    run_generation(extra_args)
    push_to_supabase()
    print_summary()


if __name__ == "__main__":
    main()
