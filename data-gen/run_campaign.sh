#!/usr/bin/env bash
# Runs one full attempt of the question-generation campaign end to end:
# checks key health, runs generation (real model) until either every tuple
# is done or every key is exhausted for the day (generate_question_gemini.py
# already detects that and stops on its own - see its watchdog thread; this
# script doesn't need to re-implement that), then pushes whatever was
# generated to Supabase and prints a summary. Shows a live progress bar
# while generation runs.
#
# WINDOWS: run this from Git Bash (the same shell used to develop this
# pipeline), not cmd.exe or plain PowerShell - neither understands bash
# syntax. From a Git Bash terminal in data-gen/:  bash run_campaign.sh
#
# Safe to re-run as many times as needed (e.g. once a day after keys reset):
# generation resumes from gemini_progress_v2.json automatically, and the
# Supabase push dedups against what's already there. Nothing here is
# destructive.
#
# Usage:
#   bash run_campaign.sh              # full real run
#   bash run_campaign.sh --limit 6    # small test-model pilot (passes
#                                      #  through to generate_question_gemini.py;
#                                      #  add --real yourself if you want it
#                                      #  to spend production quota)

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

# Runs fully in the background so the verbose per-tuple log (hundreds of
# [verify]/[ratelimit] lines) goes to $LOG only, and this terminal can show
# a clean, single-line, live-updating progress bar instead.
"$PY" generate_question_gemini.py --real "$@" > "$LOG" 2>&1 &
GEN_PID=$!

# The total tuple count depends on --limit/--sample-topics if passed, so
# read it back from the run's own "Tuples to generate: N" line rather than
# hardcoding it.
TOTAL=""
for _ in $(seq 1 60); do
    TOTAL=$(sed -n 's/.*Tuples to generate: \([0-9]*\).*/\1/p' "$LOG" 2>/dev/null | head -1)
    [ -n "$TOTAL" ] && break
    sleep 1
done
if [ -z "$TOTAL" ]; then
    echo "  (couldn't read the tuple total yet - skipping the progress bar; check $LOG directly)"
    TOTAL=0
fi

if [ "$TOTAL" -gt 0 ]; then
    BAR_WIDTH=50
    while kill -0 "$GEN_PID" 2>/dev/null; do
        DONE=$("$PY" -c "
import json
try:
    print(len(json.load(open('gemini_progress_v2.json', encoding='utf-8'))))
except Exception:
    print(0)
" 2>/dev/null)
        [ -z "$DONE" ] && DONE=0
        PCT=$((DONE * 100 / TOTAL))
        [ "$PCT" -gt 100 ] && PCT=100
        FILLED=$((PCT * BAR_WIDTH / 100))
        EMPTY=$((BAR_WIDTH - FILLED))
        BAR=$(printf '%*s' "$FILLED" '' | tr ' ' '#')$(printf '%*s' "$EMPTY" '' | tr ' ' '-')
        printf "\r  [%s] %3d%%  (%d/%d tuples)   " "$BAR" "$PCT" "$DONE" "$TOTAL"
        sleep 5
    done
    echo
fi

wait "$GEN_PID"
GEN_EXIT=$?
if [ "$GEN_EXIT" -ne 0 ]; then
    echo "  generation exited with code $GEN_EXIT - check $LOG for details"
fi
tail -5 "$LOG"

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
