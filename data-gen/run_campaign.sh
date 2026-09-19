#!/usr/bin/env bash
# Runs one full attempt of the question-generation campaign end to end:
# checks key health, runs generation (real model) until either every tuple
# is done or every key is exhausted for the day, then pushes whatever was
# generated to Supabase and prints a summary.
#
# Safe to re-run as many times as needed (e.g. once a day after keys reset):
# generation resumes from gemini_progress_v2.json automatically, and the
# Supabase push dedups against what's already there. Nothing here is
# destructive.
#
# Usage:
#   ./run_campaign.sh              # full real run
#   ./run_campaign.sh --limit 6    # small test-model pilot (passes through
#                                   #  to generate_question_gemini.py; add
#                                   #  --real yourself if you want it to
#                                   #  spend production quota)

set -uo pipefail
cd "$(dirname "$0")"

PY=./.venv/Scripts/python.exe
LOG="gemini_run_$(date +%Y%m%d_%H%M%S).log"

echo "=== 1/3: checking API key health (gemini-3.5-flash-lite) ==="
"$PY" - <<'PYEOF'
import requests, time
keys = [l.strip() for l in open("../keys/.gemini_keys", encoding="utf-8").read().splitlines() if l.strip()]
ok = 0
for i, k in enumerate(keys, 1):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={k}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=20)
    except Exception as exc:
        print(f"  key{i}: REQUEST ERROR {exc!r}")
        continue
    status = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
    print(f"  key{i}: {status}")
    if r.status_code == 200:
        ok += 1
    time.sleep(0.3)
print(f"\n{ok}/{len(keys)} keys healthy right now.")
if ok == 0:
    print("WARNING: no key is currently usable - the run below will likely "
          "stop almost immediately via the all-keys-exhausted watchdog. "
          "Consider waiting for quota reset before running this.")
PYEOF

echo
echo "=== 2/3: running generation (--real), logging to $LOG ==="
echo "    (resumes automatically from gemini_progress_v2.json; stops cleanly"
echo "     on its own once either every tuple is done or every key is"
echo "     exhausted for today - re-run this script again later either way)"
"$PY" generate_question_gemini.py --real "$@" 2>&1 | tee "$LOG"

echo
echo "=== 3/3: pushing generated questions to Supabase ==="
"$PY" load_questions_to_supabase.py --input output_questions_gemini_v2.json

echo
echo "=== summary ==="
"$PY" - <<'PYEOF'
import json
prog = json.load(open("gemini_progress_v2.json", encoding="utf-8"))
qs = json.load(open("output_questions_gemini_v2.json", encoding="utf-8"))
print(f"tuples completed: {len(prog)} / 10128")
print(f"total questions in local corpus file: {len(qs)}")
if len(prog) < 10128:
    print(f"\n{10128 - len(prog)} tuples remain. Re-run this script "
          f"(./run_campaign.sh) to continue - it will resume automatically, "
          f"whether that's now, after a short wait, or tomorrow once quota resets.")
else:
    print("\nAll tuples done.")
PYEOF
