"""
server.py
---------
FastAPI backend for ATLAS:
- Username-based login/signup
- Course/section/topic catalog API
- Section state API (diagnostic gate + lock state)
- Fixed-length diagnostic flow (30 questions, one-by-one)
- Mastery map/table API for section visualization
"""

from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client

from bloom_taxonomy import BloomLevel
from diagnostic import DiagnosticSession, QuestionSpec
from skill_tree import SkillTree

load_dotenv()

# ------------------------------------------------------------------ setup
app = FastAPI(title="Adaptive Engine Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

BASE_DIR = Path(__file__).resolve().parent
TREE_DIR = BASE_DIR / "tree_data"

TOPIC_SKILLS_PATH = TREE_DIR / "topic_skills.json"
SKILL_EDGES_PATH = TREE_DIR / "skill_edges.json"
SKILL_DESCRIPTIONS_PATH = TREE_DIR / "skill_descriptions.json"
PLATFORM_CATALOG_PATH = TREE_DIR / "platform_catalog.json"

DIAGNOSTIC_QUESTION_COUNT = 30
MASTERY_NOTIFY_THRESHOLD = 95.0

SECTION_1_ID = "section_1_arithmetic_real_numbers"


# ------------------------------------------------------------------ models
class UserCreate(BaseModel):
    user_name: str


class DiagnosticStartRequest(BaseModel):
    user_id: str
    section_id: str = SECTION_1_ID


class DiagnosticAnswerRequest(BaseModel):
    selected_option_label: str = Field(..., min_length=1, max_length=1)


@dataclass
class DiagnosticRun:
    session_id: str
    user_id: str
    section_id: str
    diagnostic_session: Optional[DiagnosticSession]
    section_skill_ids: List[str]
    topic_code_to_display: Dict[str, str]
    asked_count: int = 0
    max_questions: int = DIAGNOSTIC_QUESTION_COUNT
    used_question_ids: set[int] = field(default_factory=set)
    state_cache: Dict[str, Dict[str, float]] = field(default_factory=dict)
    current_spec: Optional[QuestionSpec] = None
    current_question_row: Optional[dict] = None

    def db_fetch(self, userid: str, skill_id: str) -> Dict[str, float]:
        if userid != self.user_id:
            raise RuntimeError("Diagnostic state fetch received unexpected user id.")

        cached = self.state_cache.get(skill_id)
        if cached is not None:
            return {
                "mastery": cached["mastery"],
                "p_learned": cached["p_learned"],
                "p_transition": cached.get("p_transition", 0.01),
            }

        result = (
            db.table("user_skill")
            .select("mastery_level")
            .eq("user_id", userid)
            .eq("skill_id", skill_id)
            .maybe_single()
            .execute()
        )
        data, error = _extract_supabase_payload(result)
        if error:
            raise RuntimeError(f"Failed to fetch user_skill: {error}")

        mastery = float(data["mastery_level"]) if data is not None else 0.0
        p_learned = max(0.0, min(1.0, mastery / 100.0))
        self.state_cache[skill_id] = {
            "mastery": mastery,
            "p_learned": p_learned,
            "p_transition": 0.01,
        }
        return {
            "mastery": mastery,
            "p_learned": p_learned,
            "p_transition": 0.01,
        }

    def db_update(
        self,
        userid: str,
        skill_id: str,
        mastery: float,
        p_learned: float,
        p_transition: float | None = None,
    ) -> None:
        if userid != self.user_id:
            raise RuntimeError("Diagnostic state update received unexpected user id.")

        mastery_value = max(0.0, min(100.0, float(mastery)))
        p_learned_value = max(0.0, min(1.0, float(p_learned)))

        self.state_cache[skill_id] = {
            "mastery": mastery_value,
            "p_learned": p_learned_value,
            "p_transition": 0.01 if p_transition is None else float(p_transition),
        }

        # Ontology may contain skills not present in DB yet. Keep runtime cache but skip DB write.
        if EXISTING_SKILL_IDS and skill_id not in EXISTING_SKILL_IDS:
            return

        try:
            upsert_result = (
                db.table("user_skill")
                .upsert(
                    {
                        "user_id": userid,
                        "skill_id": skill_id,
                        "mastery_level": mastery_value,
                    },
                    on_conflict="user_id,skill_id",
                )
                .execute()
            )
            _, error = _extract_supabase_payload(upsert_result)
            if error:
                raise RuntimeError(f"Failed to upsert user_skill: {error}")
        except Exception as exc:
            msg = str(exc)
            if "user_skill_skill_id_fkey" in msg or "Key (skill_id)=" in msg and "is not present in table \"skills\"" in msg:
                return
            raise RuntimeError(f"Failed to upsert user_skill: {exc}") from exc


# ------------------------------------------------------------------ in-memory runtime state
DIAGNOSTIC_RUNS: Dict[str, DiagnosticRun] = {}
SECTION_PROGRESS: Dict[str, Dict[str, object]] = {}


# ------------------------------------------------------------------ load static data
with open(TOPIC_SKILLS_PATH, "r", encoding="utf-8") as f:
    TOPIC_SKILLS: Dict[str, List[str]] = json.load(f)

with open(SKILL_EDGES_PATH, "r", encoding="utf-8") as f:
    SKILL_EDGES: List[Dict[str, str]] = json.load(f)

with open(SKILL_DESCRIPTIONS_PATH, "r", encoding="utf-8") as f:
    SKILL_DESCRIPTIONS: Dict[str, str] = json.load(f)

with open(PLATFORM_CATALOG_PATH, "r", encoding="utf-8") as f:
    PLATFORM_CATALOG: Dict[str, object] = json.load(f)

SKILL_TREE = SkillTree()
SKILL_TREE.build_tree_json(
    str(TOPIC_SKILLS_PATH),
    str(SKILL_EDGES_PATH),
    str(SKILL_DESCRIPTIONS_PATH),
)


# ------------------------------------------------------------------ helpers

def _extract_supabase_payload(response):
    if response is None:
        return None, None
    if isinstance(response, dict):
        return response.get("data"), response.get("error")
    return getattr(response, "data", None), getattr(response, "error", None)


def _load_existing_skill_ids() -> set[str]:
    """Return all known skill IDs from DB; fallback to empty set on query issues."""
    try:
        result = db.table("skills").select("skill_id").limit(10000).execute()
        data, error = _extract_supabase_payload(result)
        if error:
            print(f"WARN: could not load skills table IDs: {error}")
            return set()

        rows = data or []
        if isinstance(rows, dict):
            rows = [rows]

        return {row["skill_id"] for row in rows if row.get("skill_id")}
    except Exception as exc:
        print(f"WARN: failed loading skills table IDs: {exc}")
        return set()


EXISTING_SKILL_IDS = _load_existing_skill_ids()


def _progress_key(user_id: str, section_id: str) -> str:
    return f"{user_id}:{section_id}"


def _get_section(section_id: str) -> Optional[dict]:
    courses = PLATFORM_CATALOG.get("courses", [])
    for course in courses:
        for section in course.get("sections", []):
            if section.get("id") == section_id:
                return section
    return None


def _get_course_for_section(section_id: str) -> Optional[dict]:
    courses = PLATFORM_CATALOG.get("courses", [])
    for course in courses:
        for section in course.get("sections", []):
            if section.get("id") == section_id:
                return course
    return None


def _section_topic_codes(section: dict) -> List[str]:
    topic_codes = [topic["skill_topic_code"] for topic in section.get("topics", [])]
    topic_codes.extend(section.get("additional_skill_topic_codes", []))
    return list(dict.fromkeys(topic_codes))


def _section_skill_ids(section: dict) -> List[str]:
    skill_ids: set[str] = set()
    for code in _section_topic_codes(section):
        for sid in TOPIC_SKILLS.get(code, []):
            if not EXISTING_SKILL_IDS or sid in EXISTING_SKILL_IDS:
                skill_ids.add(sid)
    return sorted(skill_ids)


def _topic_code_to_display_name(section: dict) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for topic in section.get("topics", []):
        mapping[topic["skill_topic_code"]] = topic["title"]

    # Internal topic code used by ontology data; map to nearest user-facing topic.
    if "EXT" not in mapping:
        mapping["EXT"] = "Real Numbers"

    return mapping


def _skill_neighbors(skill_id: str, allowed_skill_ids: set[str]) -> List[str]:
    skill = SKILL_TREE.get_skill(skill_id)
    if skill is None:
        return []

    neighbors = list(skill.parent_ids) + list(skill.child_ids)
    return [sid for sid in neighbors if sid in allowed_skill_ids]


def _bloom_label(level: BloomLevel) -> str:
    return level.name.capitalize()


def _nearby_bloom_labels(level: BloomLevel) -> List[str]:
    offsets = [0, 1, -1, 2, -2, 3, -3]
    max_level = max(item.value for item in BloomLevel)
    labels: List[str] = []
    seen = set()

    for offset in offsets:
        value = level.value + offset
        if value < 1 or value > max_level:
            continue
        if value in seen:
            continue
        seen.add(value)
        labels.append(_bloom_label(BloomLevel(value)))

    return labels


def _mastery_map_for_user(user_id: str, skill_ids: List[str]) -> Dict[str, float]:
    if not skill_ids:
        return {}

    result = (
        db.table("user_skill")
        .select("skill_id, mastery_level")
        .eq("user_id", user_id)
        .in_("skill_id", skill_ids)
        .execute()
    )
    data, error = _extract_supabase_payload(result)
    if error:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mastery: {error}")

    mastery = {sid: 0.0 for sid in skill_ids}
    rows = data or []
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows:
        mastery[row["skill_id"]] = float(row["mastery_level"])

    return mastery


def _has_section_mastery_record(user_id: str, section_skill_ids: List[str]) -> bool:
    if not section_skill_ids:
        return False

    result = (
        db.table("user_skill")
        .select("skill_id")
        .eq("user_id", user_id)
        .in_("skill_id", section_skill_ids)
        .limit(1)
        .execute()
    )
    data, error = _extract_supabase_payload(result)
    if error:
        raise HTTPException(status_code=500, detail=f"Failed to check section mastery: {error}")

    if data is None:
        return False
    if isinstance(data, dict):
        return True
    return len(data) > 0


def _question_select_query(skill_ids: List[str] | None, bloom_levels: List[str] | None, topic: str | None):
    query = db.table("questions").select(
        "id,skill_id,bloom_level,topic,question_stem,"
        "question_options(id,option_label,option_text,is_correct,explanation,"
        "option_missing_prerequisites(missing_skill_id))"
    )

    if skill_ids:
        if len(skill_ids) == 1:
            query = query.eq("skill_id", skill_ids[0])
        else:
            query = query.in_("skill_id", skill_ids)

    if bloom_levels:
        if len(bloom_levels) == 1:
            query = query.eq("bloom_level", bloom_levels[0])
        else:
            query = query.in_("bloom_level", bloom_levels)

    if topic:
        query = query.eq("topic", topic)

    query = query.limit(200)
    return query


def _query_questions(skill_ids: List[str] | None, bloom_levels: List[str] | None, topic: str | None) -> List[dict]:
    result = _question_select_query(skill_ids=skill_ids, bloom_levels=bloom_levels, topic=topic).execute()
    data, error = _extract_supabase_payload(result)
    if error:
        raise HTTPException(status_code=500, detail=f"Failed to fetch questions: {error}")

    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    return data


def _pick_unseen_question(rows: List[dict], used_ids: set[int]) -> Optional[dict]:
    candidates = [row for row in rows if int(row["id"]) not in used_ids]
    if not candidates:
        return None
    return random.choice(candidates)


def _pick_unseen_low_mastery_question(rows: List[dict], used_ids: set[int], mastery_map: Dict[str, float]) -> Optional[dict]:
    candidates = [row for row in rows if int(row["id"]) not in used_ids]
    if not candidates:
        return None

    random.shuffle(candidates)
    candidates.sort(key=lambda row: mastery_map.get(row["skill_id"], 0.0))
    return candidates[0]


def _nearby_topic_skills(run: DiagnosticRun, target_skill_id: str, topic_code: str) -> Dict[int, List[str]]:
    topic_skill_ids = set(TOPIC_SKILLS.get(topic_code, []))
    topic_skill_ids = topic_skill_ids.intersection(set(run.section_skill_ids))
    if not topic_skill_ids:
        return {}

    distances: Dict[int, List[str]] = {}
    visited = {target_skill_id}
    queue: List[tuple[str, int]] = [(target_skill_id, 0)]

    while queue:
        sid, dist = queue.pop(0)
        for neighbor in _skill_neighbors(sid, allowed_skill_ids=set(run.section_skill_ids)):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            next_dist = dist + 1
            queue.append((neighbor, next_dist))
            if neighbor in topic_skill_ids:
                distances.setdefault(next_dist, []).append(neighbor)

    return distances


def _question_payload(row: dict, topic_code_to_display: Dict[str, str]) -> dict:
    topic_value = row.get("topic")
    if not topic_value:
        skill = SKILL_TREE.get_skill(row["skill_id"])
        if skill and skill.topics:
            topic_value = topic_code_to_display.get(skill.topics[0], skill.topics[0])

    options = row.get("question_options") or []
    normalized_options = []
    for option in sorted(options, key=lambda item: item.get("option_label", "")):
        missing = option.get("option_missing_prerequisites") or []
        normalized_options.append(
            {
                "label": option.get("option_label"),
                "text": option.get("option_text"),
                "explanation": option.get("explanation") or "",
                "missing_prerequisites": [m.get("missing_skill_id") for m in missing if m.get("missing_skill_id")],
            }
        )

    return {
        "question_id": row["id"],
        "bloom_level": row.get("bloom_level"),
        "skill_id": row["skill_id"],
        "skill_description": SKILL_DESCRIPTIONS.get(row["skill_id"], ""),
        "topic": topic_value,
        "question_stem": row.get("question_stem"),
        "options": normalized_options,
    }


def _select_question_row_for_spec(run: DiagnosticRun, spec: QuestionSpec) -> Optional[dict]:
    bloom_candidates = _nearby_bloom_labels(spec.bloom_level)
    topic_display = run.topic_code_to_display.get(spec.topic, spec.topic)

    # Tier 1: same skill + nearby bloom
    for bloom_label in bloom_candidates:
        rows = _query_questions(skill_ids=[spec.skill_id], bloom_levels=[bloom_label], topic=topic_display)
        picked = _pick_unseen_question(rows, run.used_question_ids)
        if picked is not None:
            return picked

    # Tier 1 fallback: same skill + nearby bloom without topic filter
    for bloom_label in bloom_candidates:
        rows = _query_questions(skill_ids=[spec.skill_id], bloom_levels=[bloom_label], topic=None)
        picked = _pick_unseen_question(rows, run.used_question_ids)
        if picked is not None:
            return picked

    # Tier 2: same topic + nearby skills (distance based), nearby bloom
    mastery_map = {sid: run.db_fetch(run.user_id, sid)["mastery"] for sid in run.section_skill_ids}
    nearby_by_distance = _nearby_topic_skills(run, target_skill_id=spec.skill_id, topic_code=spec.topic)
    for distance in sorted(nearby_by_distance.keys()):
        nearby_skills = nearby_by_distance[distance]
        for bloom_label in bloom_candidates:
            rows = _query_questions(skill_ids=nearby_skills, bloom_levels=[bloom_label], topic=topic_display)
            picked = _pick_unseen_low_mastery_question(rows, run.used_question_ids, mastery_map)
            if picked is not None:
                return picked

    return None


def _next_question_for_run(run: DiagnosticRun) -> Optional[dict]:
    if run.diagnostic_session is None:
        raise HTTPException(status_code=500, detail="Diagnostic session is not initialized.")

    while run.asked_count < run.max_questions:
        spec = run.diagnostic_session.next_question_spec()
        if spec is None:
            return None

        row = _select_question_row_for_spec(run, spec)
        if row is None:
            # No question found for this selected spec; skip this skill and continue.
            run.diagnostic_session.tested[spec.skill_id] = True
            continue

        run.current_spec = spec
        run.current_question_row = row
        run.used_question_ids.add(int(row["id"]))
        return _question_payload(row, run.topic_code_to_display)

    return None


def _section_state(user_id: str, section_id: str) -> dict:
    section = _get_section(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Unknown section '{section_id}'.")

    skill_ids = _section_skill_ids(section)
    has_records = _has_section_mastery_record(user_id=user_id, section_skill_ids=skill_ids)

    progress = SECTION_PROGRESS.get(_progress_key(user_id, section_id), {})
    diagnostic_completed = bool(progress.get("diagnostic_completed", has_records))
    diagnostic_required = not has_records

    if progress.get("active_session_id") and progress["active_session_id"] not in DIAGNOSTIC_RUNS:
        progress["active_session_id"] = None

    return {
        "user_id": user_id,
        "section_id": section_id,
        "diagnostic_required": diagnostic_required,
        "diagnostic_completed": diagnostic_completed,
        "mastery_locked": not diagnostic_completed,
        "diagnostic_answered_count": int(progress.get("answered_count", 0)),
        "diagnostic_total_questions": DIAGNOSTIC_QUESTION_COUNT,
        "active_diagnostic_session_id": progress.get("active_session_id"),
    }


# ------------------------------------------------------------------ endpoints: catalog + user auth
@app.get("/catalog")
def get_catalog():
    return PLATFORM_CATALOG


@app.get("/users/{user_name}/")
def get_user(user_name: str):
    result = (
        db.table("users")
        .select("*")
        .eq("user_name", user_name)
        .maybe_single()
        .execute()
    )

    data, error = _extract_supabase_payload(result)
    if error:
        raise HTTPException(status_code=500, detail=str(error))
    if data is None:
        raise HTTPException(status_code=404, detail=f"No data for user '{user_name}'.")

    return {
        "user_id": data["user_id"],
        "user_name": data["user_name"],
    }


@app.post("/users/")
def create_user(user: UserCreate):
    try:
        result = (
            db.table("users")
            .select("*")
            .eq("user_name", user.user_name)
            .maybe_single()
            .execute()
        )

        data, error = _extract_supabase_payload(result)
        if error:
            raise HTTPException(status_code=500, detail=str(error))
        if data is not None:
            raise HTTPException(status_code=409, detail=f"User '{user.user_name}' already exists.")

        insert_result = (
            db.table("users")
            .insert({"user_name": user.user_name})
            .execute()
        )
        insert_data, insert_error = _extract_supabase_payload(insert_result)

        if insert_error:
            if "duplicate" in str(insert_error).lower() or "unique" in str(insert_error).lower():
                raise HTTPException(status_code=409, detail=f"User '{user.user_name}' already exists.")
            raise HTTPException(status_code=500, detail=f"Insert failed: {insert_error}")

        if insert_data is None:
            lookup_result = (
                db.table("users")
                .select("*")
                .eq("user_name", user.user_name)
                .maybe_single()
                .execute()
            )
            insert_data, lookup_error = _extract_supabase_payload(lookup_result)
            if lookup_error:
                raise HTTPException(status_code=500, detail=f"Insert lookup failed: {lookup_error}")
            if insert_data is None:
                raise HTTPException(status_code=500, detail="Insert succeeded but no user row was returned.")

        row = insert_data[0] if isinstance(insert_data, list) else insert_data
        return {
            "user_id": row["user_id"],
            "user_name": row["user_name"],
        }

    except HTTPException:
        raise
    except Exception as exc:
        print("ERROR:", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ------------------------------------------------------------------ endpoints: section state + mastery
@app.get("/users/{user_id}/sections/{section_id}/state")
def get_section_state(user_id: str, section_id: str):
    return _section_state(user_id=user_id, section_id=section_id)


@app.get("/users/{user_id}/sections/{section_id}/mastery")
def get_section_mastery(user_id: str, section_id: str):
    state = _section_state(user_id=user_id, section_id=section_id)
    if state["mastery_locked"]:
        return {
            "locked": True,
            "lock_reason": "Complete diagnostic to unlock mastery views.",
            "state": state,
            "table": [],
            "map": {"nodes": [], "edges": []},
        }

    section = _get_section(section_id)
    skill_ids = _section_skill_ids(section)
    mastery = _mastery_map_for_user(user_id=user_id, skill_ids=skill_ids)
    topic_display_map = _topic_code_to_display_name(section)

    table_rows = []
    map_nodes = []
    skill_set = set(skill_ids)

    for sid in skill_ids:
        skill = SKILL_TREE.get_skill(sid)
        display_topics = []
        if skill:
            display_topics = [topic_display_map.get(code, code) for code in skill.topics]

        row = {
            "skill_id": sid,
            "skill_description": SKILL_DESCRIPTIONS.get(sid, ""),
            "topics": display_topics,
            "mastery": round(mastery.get(sid, 0.0), 2),
        }
        table_rows.append(row)
        map_nodes.append(row)

    map_edges = [
        {"source": edge["source"], "target": edge["target"]}
        for edge in SKILL_EDGES
        if edge["source"] in skill_set and edge["target"] in skill_set
    ]

    return {
        "locked": False,
        "state": state,
        "table": table_rows,
        "map": {
            "nodes": map_nodes,
            "edges": map_edges,
        },
    }


# ------------------------------------------------------------------ endpoints: diagnostic flow
@app.post("/diagnostic/start")
def start_diagnostic(request: DiagnosticStartRequest):
    section = _get_section(request.section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Unknown section '{request.section_id}'.")
    if not section.get("enabled", False):
        raise HTTPException(status_code=400, detail=f"Section '{request.section_id}' is not available yet.")

    section_skill_ids = _section_skill_ids(section)
    topic_code_to_display = _topic_code_to_display_name(section)

    session_id = str(uuid.uuid4())
    run = DiagnosticRun(
        session_id=session_id,
        user_id=request.user_id,
        section_id=request.section_id,
        diagnostic_session=None,
        section_skill_ids=section_skill_ids,
        topic_code_to_display=topic_code_to_display,
    )

    run.diagnostic_session = DiagnosticSession(
        skill_tree=SKILL_TREE,
        userid=request.user_id,
        db_fetch=run.db_fetch,
        db_update=run.db_update,
        stop_threshold=0.0,
    )

    DIAGNOSTIC_RUNS[session_id] = run

    key = _progress_key(request.user_id, request.section_id)
    SECTION_PROGRESS[key] = {
        "diagnostic_completed": False,
        "answered_count": 0,
        "active_session_id": session_id,
    }

    question = _next_question_for_run(run)
    if question is None:
        raise HTTPException(status_code=404, detail="No diagnostic question could be found for the current question bank.")

    return {
        "session_id": session_id,
        "section_id": request.section_id,
        "question_index": 1,
        "total_questions": run.max_questions,
        "question": question,
    }


@app.get("/diagnostic/{session_id}/status")
def get_diagnostic_status(session_id: str):
    run = DIAGNOSTIC_RUNS.get(session_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found.")

    return {
        "session_id": run.session_id,
        "user_id": run.user_id,
        "section_id": run.section_id,
        "answered_count": run.asked_count,
        "total_questions": run.max_questions,
        "completed": run.asked_count >= run.max_questions,
        "awaiting_answer": run.current_question_row is not None,
    }


@app.post("/diagnostic/{session_id}/answer")
def submit_diagnostic_answer(session_id: str, request: DiagnosticAnswerRequest):
    run = DIAGNOSTIC_RUNS.get(session_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found.")
    if run.diagnostic_session is None:
        raise HTTPException(status_code=500, detail="Diagnostic session is not initialized.")
    if run.current_question_row is None or run.current_spec is None:
        raise HTTPException(status_code=400, detail="No active diagnostic question is awaiting an answer.")

    selected_label = request.selected_option_label.strip().upper()
    options = run.current_question_row.get("question_options") or []
    selected_option = None
    for option in options:
        if str(option.get("option_label", "")).upper() == selected_label:
            selected_option = option
            break

    if selected_option is None:
        raise HTTPException(status_code=400, detail="Selected option label is invalid for the current question.")

    before_mastery = {sid: run.db_fetch(run.user_id, sid)["mastery"] for sid in run.section_skill_ids}

    is_correct = bool(selected_option.get("is_correct", False))
    run.diagnostic_session.record_answer(
        skill_id=run.current_spec.skill_id,
        bloom_level=run.current_spec.bloom_level,
        is_correct=is_correct,
    )

    after_mastery = {sid: run.db_fetch(run.user_id, sid)["mastery"] for sid in run.section_skill_ids}
    crossed_skills = [
        sid
        for sid in run.section_skill_ids
        if before_mastery[sid] < MASTERY_NOTIFY_THRESHOLD <= after_mastery[sid]
    ]

    run.asked_count += 1

    progress_key = _progress_key(run.user_id, run.section_id)
    progress = SECTION_PROGRESS.get(progress_key, {})
    progress["answered_count"] = run.asked_count

    completed = run.asked_count >= run.max_questions
    if completed:
        progress["diagnostic_completed"] = True
        progress["active_session_id"] = None
        run.current_spec = None
        run.current_question_row = None
    else:
        progress["diagnostic_completed"] = False
        progress["active_session_id"] = run.session_id
    SECTION_PROGRESS[progress_key] = progress

    next_question = None
    if not completed:
        next_question = _next_question_for_run(run)
        if next_question is None:
            completed = True
            progress["diagnostic_completed"] = True
            progress["active_session_id"] = None
            SECTION_PROGRESS[progress_key] = progress

    response = {
        "session_id": run.session_id,
        "is_correct": is_correct,
        "selected_option_label": selected_label,
        "selected_option_explanation": selected_option.get("explanation") or "",
        "mastery_notifications": crossed_skills,
        "answered_count": run.asked_count,
        "total_questions": run.max_questions,
        "completed": completed,
    }

    if completed:
        response["next_question"] = None
    else:
        response["next_question"] = next_question

    return response
