"""
admin_stats.py
---------------
Admin-only API for aggregate student-performance statistics and a full
data export, read from the live Supabase tables (`users`, `user_skill`)
and enriched with the served ontology's metadata
(Backend/tree_data/{skill_subjects,skill_descriptions,topic_skills,topic_labels}.json).

Deliberately isolated, same as admin_ontology.py: this module owns its own
Supabase client rather than importing server.py's, so there is no import
cycle and no coupling to server.py's internals. It only ever reads —
`user_skill` is the live mastery table the adaptive engine writes to, and
nothing here writes to it or to any tree_data file.

Data-scope note (see HANDOFF/README "known limitations"): `user_skill`
(final mastery per skill per student) is the ONLY durable, cross-restart
student-performance signal this project persists. There is no per-question
attempt log — diagnostic/topic-practice sessions live in in-memory dicts in
server.py and are lost on restart. So "aggregate statistics" and "export"
here mean the current mastery snapshot, not a historical event log. Field
names below say "mastery snapshot" rather than implying more than that.
"""
from __future__ import annotations

import csv
import io
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from supabase import create_client

from admin_ontology import require_admin

load_dotenv()

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

BASE_DIR = Path(__file__).resolve().parent
TREE_DIR = BASE_DIR / "tree_data"

# PostgREST silently caps a response at its project's max-rows setting
# (1000 on this project's Supabase instance) regardless of what `.limit()`
# asks for -- not an error, just a truncated result. `user_skill` crosses
# that on any non-trivial cohort (1,688 skills means one active student
# alone can exceed it), so every full-table read here pages explicitly with
# `.range()` -- the same fix already applied in
# data-gen/load_questions_to_supabase.py after it bit that pipeline once.
_PAGE_SIZE = 1000


def _payload(response):
    if response is None:
        return None, None
    if isinstance(response, dict):
        return response.get("data"), response.get("error")
    return getattr(response, "data", None), getattr(response, "error", None)


def _fetch_all_rows(table: str, select: str) -> List[dict]:
    rows: List[dict] = []
    offset = 0
    while True:
        result = db.table(table).select(select).range(offset, offset + _PAGE_SIZE - 1).execute()
        data, error = _payload(result)
        if error:
            raise HTTPException(status_code=502, detail=f"Could not read {table}: {error}")
        page = data or []
        rows.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return rows


# ---------------------------------------------------------------- ontology metadata
# Loaded once at process start, same lifecycle as server.py's own tree_data
# loads -- this reflects whatever ontology is currently adopted (served),
# and a rebuild/adoption already requires a backend restart to take effect.
def _load_skill_metadata():
    skill_subjects = json.loads((TREE_DIR / "skill_subjects.json").read_text(encoding="utf-8"))
    skill_descriptions = json.loads((TREE_DIR / "skill_descriptions.json").read_text(encoding="utf-8"))
    topic_skills = json.loads((TREE_DIR / "topic_skills.json").read_text(encoding="utf-8"))
    topic_labels = json.loads((TREE_DIR / "topic_labels.json").read_text(encoding="utf-8"))

    skill_topic: Dict[str, str] = {}
    for topic_key, skill_ids in topic_skills.items():
        for sid in skill_ids:
            skill_topic[sid] = topic_key

    return skill_subjects, skill_descriptions, skill_topic, topic_labels


SKILL_SUBJECTS, SKILL_DESCRIPTIONS, SKILL_TOPIC, TOPIC_LABELS = _load_skill_metadata()


def _skill_meta(skill_id: str) -> dict:
    topic_key = SKILL_TOPIC.get(skill_id, "")
    return {
        "skill_description": SKILL_DESCRIPTIONS.get(skill_id, ""),
        "subject": SKILL_SUBJECTS.get(skill_id, "Unknown"),
        "topic_key": topic_key,
        "topic_label": TOPIC_LABELS.get(topic_key, ""),
    }


# ---------------------------------------------------------------- core reads
def _fetch_users() -> Dict[str, str]:
    """user_id -> user_name."""
    rows = _fetch_all_rows("users", "user_id, user_name")
    return {r["user_id"]: r["user_name"] for r in rows}


def _fetch_mastery_rows() -> List[dict]:
    """Every (user_id, skill_id, mastery_level) row in the live database."""
    return _fetch_all_rows("user_skill", "user_id, skill_id, mastery_level")


# ---------------------------------------------------------------- aggregate stats
def compute_overview() -> dict:
    user_names = _fetch_users()
    rows = _fetch_mastery_rows()

    students_with_data: Set[str] = set()
    subject_sum: Dict[str, float] = defaultdict(float)
    subject_count: Dict[str, int] = defaultdict(int)
    subject_students: Dict[str, Set[str]] = defaultdict(set)
    skill_sum: Dict[str, float] = defaultdict(float)
    skill_count: Dict[str, int] = defaultdict(int)
    skill_students: Dict[str, Set[str]] = defaultdict(set)
    histogram = [0, 0, 0, 0, 0]  # 0-20, 20-40, 40-60, 60-80, 80-100
    overall_sum = 0.0

    for r in rows:
        uid = r["user_id"]
        sid = r["skill_id"]
        mastery = float(r.get("mastery_level") or 0.0)
        subject = SKILL_SUBJECTS.get(sid, "Unknown")

        students_with_data.add(uid)

        subject_sum[subject] += mastery
        subject_count[subject] += 1
        subject_students[subject].add(uid)

        skill_sum[sid] += mastery
        skill_count[sid] += 1
        skill_students[sid].add(uid)

        overall_sum += mastery
        histogram[min(int(mastery // 20), 4)] += 1

    by_subject = [
        {
            "subject": subject,
            "students_with_data": len(subject_students[subject]),
            "average_mastery": round(subject_sum[subject] / subject_count[subject], 2),
            "mastery_rows": subject_count[subject],
        }
        for subject in sorted(subject_sum)
    ]

    skill_stats = []
    for sid, total in skill_sum.items():
        cnt = skill_count[sid]
        skill_stats.append({
            "skill_id": sid,
            **_skill_meta(sid),
            "students_with_data": len(skill_students[sid]),
            "average_mastery": round(total / cnt, 2),
        })
    skill_stats.sort(key=lambda s: s["average_mastery"])

    total_rows = len(rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_students": len(user_names),
        "students_with_mastery_data": len(students_with_data),
        "total_skills_in_ontology": len(SKILL_DESCRIPTIONS),
        "total_mastery_rows": total_rows,
        "overall_average_mastery": round(overall_sum / total_rows, 2) if total_rows else 0.0,
        "mastery_distribution": {
            "0-20": histogram[0], "20-40": histogram[1], "40-60": histogram[2],
            "60-80": histogram[3], "80-100": histogram[4],
        },
        "by_subject": by_subject,
        "weakest_skills": skill_stats[:20],
        "strongest_skills": list(reversed(skill_stats[-20:])),
    }


# ---------------------------------------------------------------- export
_EXPORT_FIELDS = [
    "user_id", "user_name", "skill_id", "skill_description",
    "subject", "topic_key", "topic_label", "mastery_level",
]


def _performance_rows() -> List[dict]:
    user_names = _fetch_users()
    rows = _fetch_mastery_rows()
    out = []
    for r in rows:
        sid = r["skill_id"]
        uid = r["user_id"]
        out.append({
            "user_id": uid,
            "user_name": user_names.get(uid, ""),
            "skill_id": sid,
            **_skill_meta(sid),
            "mastery_level": round(float(r.get("mastery_level") or 0.0), 4),
        })
    return out


def _to_csv(rows: List[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    # Leading BOM so Excel (the realistic consumer of "export for analysis"
    # on this project, given the Bangla skill descriptions) opens the file
    # as UTF-8 instead of guessing a local codepage and mangling the text.
    return "﻿" + buf.getvalue()


router = APIRouter(prefix="/admin/stats", tags=["admin-stats"], dependencies=[Depends(require_admin)])


@router.get("/overview")
def get_overview():
    return compute_overview()


@router.get("/export")
def export_performance(format: str = "csv"):
    fmt = format.strip().lower()
    if fmt not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="format must be 'csv' or 'json'")

    rows = _performance_rows()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    if fmt == "csv":
        body = _to_csv(rows)
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="atlas_student_performance_{stamp}.csv"'},
        )

    body = json.dumps(rows, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="atlas_student_performance_{stamp}.json"'},
    )
