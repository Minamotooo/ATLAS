"""
server.py
---------
FastAPI backend for ATLAS:
- Username + password login/signup with bearer tokens (see auth.py)
- Course/section/topic catalog API
- Section state API (diagnostic gate + lock state)
- Fixed-length diagnostic flow (30 questions, one-by-one)
- Mastery map/table API for section visualization
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client

from admin_ontology import router as admin_ontology_router
from admin_stats import router as admin_stats_router
from auth import (
    PASSWORD_MIN_LENGTH,
    AuthUser,
    admin_usernames,
    check_login_throttle,
    clear_login_failures,
    current_user,
    hash_password,
    issue_token,
    record_login_failure,
    require_self,
    verify_password,
)
from bloom_taxonomy import BloomLevel, get_level_from_mastery
from diagnostic import DiagnosticSession, QuestionSpec
from mastery_updater import MasteryUpdater, UpdateMode
from skill_tree import SkillTree

load_dotenv()

# ------------------------------------------------------------------ setup
app = FastAPI(title="Adaptive Engine Server")

# Comma-separated; a deployment can pin this to its frontend's origin.
CORS_ORIGINS = [o.strip() for o in (os.getenv("CORS_ORIGINS") or "*").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_ontology_router)
app.include_router(admin_stats_router)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

BASE_DIR = Path(__file__).resolve().parent
TREE_DIR = BASE_DIR / "tree_data"

TOPIC_SKILLS_PATH = TREE_DIR / "topic_skills.json"
SKILL_EDGES_PATH = TREE_DIR / "skill_edges.json"
SKILL_DESCRIPTIONS_PATH = TREE_DIR / "skill_descriptions.json"
PLATFORM_CATALOG_PATH = TREE_DIR / "platform_catalog.json"
TOPIC_LABELS_PATH = TREE_DIR / "topic_labels.json"
SKILL_SUBJECTS_PATH = TREE_DIR / "skill_subjects.json"

# Target diagnostic length. A run is capped at the section's skill count, since
# DiagnosticSession tests each skill at most once (see _diagnostic_length_for_section).
DIAGNOSTIC_QUESTION_COUNT = int(os.getenv("DIAGNOSTIC_QUESTION_COUNT", "30"))
# Demo aid: send each option's is_correct with the question (see _question_payload).
DEMO_SHOW_ANSWERS = os.getenv("DEMO_SHOW_ANSWERS", "0") == "1"
DIAGNOSTIC_MIN_QUESTION_COUNT = 5
MASTERY_NOTIFY_THRESHOLD = 95.0
TOPIC_PRACTICE_MASTERY_THRESHOLD = 95.0

TOPIC_PRACTICE_SPILLOVER_WINDOW = 5
TOPIC_PRACTICE_SPILLOVER_WRONG_TRIGGER_COUNT = 3
TOPIC_PRACTICE_ACCURACY_WINDOW = 8
TOPIC_PRACTICE_ACCURACY_TRIGGER = 0.40
TOPIC_PRACTICE_PREREQ_MASTERY_TRIGGER = 0.60
TOPIC_PRACTICE_SPILLOVER_QUESTION_COUNT = 2

# Testing switch: set to true only for profiling; default keeps the real policy flow.
DIAGNOSTIC_RANDOM_SELECTION = os.getenv("DIAGNOSTIC_RANDOM_SELECTION", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DIAGNOSTIC_RANDOM_QUERY_LIMIT = int(os.getenv("DIAGNOSTIC_RANDOM_QUERY_LIMIT", "1000"))

NEXT_QUESTION_DEBUG_LOGS = os.getenv("NEXT_QUESTION_DEBUG_LOGS", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

def _debug_search_log(message: str) -> None:
    if NEXT_QUESTION_DEBUG_LOGS:
        print(f"[nextq-debug] {message}", flush=True)


def _preview_values(values: Optional[List[str]], max_items: int = 4) -> str:
    if values is None:
        return "*"
    if not values:
        return "none"
    if len(values) <= max_items:
        return ",".join(values)
    head = ",".join(values[:max_items])
    return f"{head},...(+{len(values) - max_items})"


# ------------------------------------------------------------------ models
class Credentials(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class DiagnosticStartRequest(BaseModel):
    user_id: str
    section_id: str = Field(..., min_length=1)


class DiagnosticAnswerRequest(BaseModel):
    selected_option_label: str = Field(..., min_length=1, max_length=1)


class TopicPracticeStartRequest(BaseModel):
    user_id: str
    section_id: str = Field(..., min_length=1)
    topic_code: str = Field(..., min_length=1)


class TopicPracticeAnswerRequest(BaseModel):
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
    dirty_skill_ids: set[str] = field(default_factory=set)
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

        # Defer writes and flush once per answer to avoid N round-trips to Supabase.
        self.dirty_skill_ids.add(skill_id)

    def clear_dirty_states(self) -> None:
        self.dirty_skill_ids.clear()

    def flush_dirty_states(self) -> int:
        if not self.dirty_skill_ids:
            return 0

        skill_ids = sorted(self.dirty_skill_ids)
        rows = []
        for sid in skill_ids:
            state = self.state_cache.get(sid)
            if state is None:
                continue
            rows.append(
                {
                    "user_id": self.user_id,
                    "skill_id": sid,
                    "mastery_level": max(0.0, min(100.0, float(state["mastery"]))),
                }
            )

        if not rows:
            self.dirty_skill_ids.clear()
            return 0

        try:
            upsert_result = (
                db.table("user_skill")
                .upsert(rows, on_conflict="user_id,skill_id")
                .execute()
            )
            _, error = _extract_supabase_payload(upsert_result)
            if error:
                raise RuntimeError(f"Failed to upsert user_skill: {error}")
            self.dirty_skill_ids.clear()
            return len(rows)
        except Exception as exc:
            msg = str(exc)
            if "user_skill_skill_id_fkey" in msg or ("Key (skill_id)=" in msg and "is not present in table \"skills\"" in msg):
                persisted = 0
                for row in rows:
                    try:
                        single_upsert = (
                            db.table("user_skill")
                            .upsert(row, on_conflict="user_id,skill_id")
                            .execute()
                        )
                        _, single_error = _extract_supabase_payload(single_upsert)
                        if single_error:
                            raise RuntimeError(f"Failed to upsert user_skill row: {single_error}")
                        persisted += 1
                    except Exception as inner:
                        inner_msg = str(inner)
                        if "user_skill_skill_id_fkey" in inner_msg or (
                            "Key (skill_id)=" in inner_msg and "is not present in table \"skills\"" in inner_msg
                        ):
                            continue
                        raise RuntimeError(f"Failed to upsert user_skill row: {inner}") from inner
                self.dirty_skill_ids.clear()
                return persisted
            raise RuntimeError(f"Failed to upsert user_skill: {exc}") from exc


@dataclass
class TopicPracticeRun:
    session_id: str
    user_id: str
    section_id: str
    topic_code: str
    topic_display: str
    topic_skill_ids: List[str]
    section_skill_ids: List[str]
    traversal_skill_ids: List[str]
    topic_code_to_display: Dict[str, str]
    traversal_index: int = 0
    asked_count: int = 0
    used_question_ids: set[int] = field(default_factory=set)
    state_cache: Dict[str, Dict[str, float]] = field(default_factory=dict)
    dirty_skill_ids: set[str] = field(default_factory=set)
    exhausted_topic_skills: set[str] = field(default_factory=set)
    recent_topic_attempts: List[Dict[str, object]] = field(default_factory=list)
    current_question_row: Optional[dict] = None
    current_skill_id: Optional[str] = None
    current_bloom_level: Optional[BloomLevel] = None
    current_mode: str = "topic"
    spillover_skill_id: Optional[str] = None
    spillover_remaining: int = 0
    last_delivery_mode: Optional[str] = None
    last_spillover_reason: Optional[str] = None
    last_spillover_skill_id: Optional[str] = None
    last_spillover_trigger_answer_count: Optional[int] = None
    completed: bool = False
    completion_reason: Optional[str] = None

    def db_fetch(self, userid: str, skill_id: str) -> Dict[str, float]:
        if userid != self.user_id:
            raise RuntimeError("Topic practice state fetch received unexpected user id.")

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
            raise RuntimeError("Topic practice state update received unexpected user id.")

        mastery_value = max(0.0, min(100.0, float(mastery)))
        p_learned_value = max(0.0, min(1.0, float(p_learned)))

        self.state_cache[skill_id] = {
            "mastery": mastery_value,
            "p_learned": p_learned_value,
            "p_transition": 0.01 if p_transition is None else float(p_transition),
        }

        if EXISTING_SKILL_IDS and skill_id not in EXISTING_SKILL_IDS:
            return

        self.dirty_skill_ids.add(skill_id)

    def flush_dirty_states(self) -> int:
        if not self.dirty_skill_ids:
            return 0

        skill_ids = sorted(self.dirty_skill_ids)
        rows = []
        for sid in skill_ids:
            state = self.state_cache.get(sid)
            if state is None:
                continue
            rows.append(
                {
                    "user_id": self.user_id,
                    "skill_id": sid,
                    "mastery_level": max(0.0, min(100.0, float(state["mastery"]))),
                }
            )

        if not rows:
            self.dirty_skill_ids.clear()
            return 0

        try:
            upsert_result = (
                db.table("user_skill")
                .upsert(rows, on_conflict="user_id,skill_id")
                .execute()
            )
            _, error = _extract_supabase_payload(upsert_result)
            if error:
                raise RuntimeError(f"Failed to upsert user_skill: {error}")
            self.dirty_skill_ids.clear()
            return len(rows)
        except Exception as exc:
            msg = str(exc)
            if "user_skill_skill_id_fkey" in msg or ("Key (skill_id)=" in msg and "is not present in table \"skills\"" in msg):
                persisted = 0
                for row in rows:
                    try:
                        single_upsert = (
                            db.table("user_skill")
                            .upsert(row, on_conflict="user_id,skill_id")
                            .execute()
                        )
                        _, single_error = _extract_supabase_payload(single_upsert)
                        if single_error:
                            raise RuntimeError(f"Failed to upsert user_skill row: {single_error}")
                        persisted += 1
                    except Exception as inner:
                        inner_msg = str(inner)
                        if "user_skill_skill_id_fkey" in inner_msg or (
                            "Key (skill_id)=" in inner_msg and "is not present in table \"skills\"" in inner_msg
                        ):
                            continue
                        raise RuntimeError(f"Failed to upsert user_skill row: {inner}") from inner
                self.dirty_skill_ids.clear()
                return persisted
            raise RuntimeError(f"Failed to upsert user_skill: {exc}") from exc


# ------------------------------------------------------------------ in-memory runtime state
DIAGNOSTIC_RUNS: Dict[str, DiagnosticRun] = {}
TOPIC_PRACTICE_RUNS: Dict[str, TopicPracticeRun] = {}
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

with open(TOPIC_LABELS_PATH, "r", encoding="utf-8") as f:
    TOPIC_LABELS: Dict[str, str] = json.load(f)

with open(SKILL_SUBJECTS_PATH, "r", encoding="utf-8") as f:
    SKILL_SUBJECTS: Dict[str, str] = json.load(f)

SKILL_TREE = SkillTree()
SKILL_TREE.build_tree_json(
    str(TOPIC_SKILLS_PATH),
    str(SKILL_EDGES_PATH),
    str(SKILL_DESCRIPTIONS_PATH),
)
MASTERY_UPDATER = MasteryUpdater(SKILL_TREE)


# ------------------------------------------------------------------ helpers

def _extract_supabase_payload(response):
    if response is None:
        return None, None
    if isinstance(response, dict):
        return response.get("data"), response.get("error")
    return getattr(response, "data", None), getattr(response, "error", None)


def _load_existing_skill_ids() -> set[str]:
    """
    Return all known skill IDs from DB; fallback to empty set on query issues.

    PostgREST silently caps every response at the project's max-rows (1000),
    whatever .limit() asks for. The skills table holds more than that, and
    _section_skill_ids filters every section through this set, so a single
    unpaged select silently emptied most Mathematics and Physics sections.
    """
    try:
        ids: set[str] = set()
        page_size = 1000
        offset = 0
        while True:
            result = (
                db.table("skills")
                .select("skill_id")
                .order("skill_id")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            data, error = _extract_supabase_payload(result)
            if error:
                print(f"WARN: could not load skills table IDs: {error}")
                return set()

            rows = data or []
            if isinstance(rows, dict):
                rows = [rows]
            ids.update(row["skill_id"] for row in rows if row.get("skill_id"))
            if len(rows) < page_size:
                return ids
            offset += page_size
    except Exception as exc:
        print(f"WARN: failed loading skills table IDs: {exc}")
        return set()


EXISTING_SKILL_IDS = _load_existing_skill_ids()


def _stored_mastery_for_user(user_id: str) -> Dict[str, float]:
    """
    Every mastery value already recorded for this user, paged past the
    1000-row response cap. Seeds a diagnostic so it builds on real progress
    instead of starting each skill from the depth prior and overwriting it.
    """
    stored: Dict[str, float] = {}
    page_size = 1000
    offset = 0
    while True:
        result = (
            db.table("user_skill")
            .select("skill_id, mastery_level")
            .eq("user_id", user_id)
            .order("skill_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        data, error = _extract_supabase_payload(result)
        if error:
            raise HTTPException(status_code=500, detail=f"Could not load stored mastery: {error}")
        rows = data or []
        for row in rows:
            if row.get("skill_id") is not None:
                stored[row["skill_id"]] = float(row.get("mastery_level") or 0.0)
        if len(rows) < page_size:
            return stored
        offset += page_size


def _diagnostic_length_for_section(section_skill_ids: List[str]) -> int:
    """
    DiagnosticSession tests each skill at most once, so a section with fewer skills
    than DIAGNOSTIC_QUESTION_COUNT can never reach the target length. Cap it so the
    UI's "question X of Y" is truthful.
    """
    if not section_skill_ids:
        return DIAGNOSTIC_MIN_QUESTION_COUNT
    return max(
        DIAGNOSTIC_MIN_QUESTION_COUNT,
        min(DIAGNOSTIC_QUESTION_COUNT, len(section_skill_ids)),
    )


def _section_subject(section_id: str) -> Optional[str]:
    """Subject of the course that owns this section."""
    course = _get_course_for_section(section_id)
    return course.get("subject") if course else None


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
    """
    Topic code -> display label. Starts from the ontology-wide labels so codes
    outside this section (a skill can belong to several topics) still resolve,
    then lets the section's own titles win.
    """
    mapping: Dict[str, str] = dict(TOPIC_LABELS)
    for topic in section.get("topics", []):
        mapping[topic["skill_topic_code"]] = topic["title"]
    return mapping


def _section_topic_display_name(section: dict, topic_code: str) -> str:
    for topic in section.get("topics", []):
        if topic.get("skill_topic_code") == topic_code:
            return topic.get("title") or topic_code
    return topic_code


def _topic_skill_ids_for_section(section: dict, topic_code: str) -> List[str]:
    allowed = set(_section_skill_ids(section))
    topic_skill_ids = []
    for sid in TOPIC_SKILLS.get(topic_code, []):
        if sid in allowed:
            topic_skill_ids.append(sid)
    return list(dict.fromkeys(topic_skill_ids))


def _topic_topological_order(skill_ids: List[str]) -> List[str]:
    skill_id_set = set(skill_ids)
    return [skill.skill_id for skill in SKILL_TREE.topological_order() if skill.skill_id in skill_id_set]


def _rotate_skill_order(skill_ids: List[str], start_skill_id: str) -> List[str]:
    if not skill_ids or start_skill_id not in skill_ids:
        return skill_ids
    start_index = skill_ids.index(start_skill_id)
    return skill_ids[start_index:] + skill_ids[:start_index]


def _pick_zpd_start_skill(mastery_map: Dict[str, float], topic_skill_ids: List[str]) -> Optional[str]:
    candidates = [sid for sid in topic_skill_ids if mastery_map.get(sid, 0.0) < TOPIC_PRACTICE_MASTERY_THRESHOLD]
    if not candidates:
        return None
    random.shuffle(candidates)
    candidates.sort(key=lambda sid: mastery_map.get(sid, 0.0), reverse=True)
    return candidates[0]


def _practice_bloom_for_skill(run: TopicPracticeRun, skill_id: str) -> BloomLevel:
    mastery = run.db_fetch(run.user_id, skill_id)["mastery"]
    current_level = get_level_from_mastery(mastery)
    next_value = min(current_level.value + 1, max(level.value for level in BloomLevel))
    return BloomLevel(next_value)


def _topic_all_skills_mastered(run: TopicPracticeRun) -> bool:
    for sid in run.topic_skill_ids:
        if run.db_fetch(run.user_id, sid)["mastery"] < TOPIC_PRACTICE_MASTERY_THRESHOLD:
            return False
    return True


def _pick_question_row_for_skill(
    used_question_ids: set[int],
    skill_id: str,
    bloom_level: BloomLevel,
) -> Optional[dict]:
    bloom_candidates = _nearby_bloom_labels(bloom_level)

    for bloom_label in bloom_candidates:
        rows = _query_questions(skill_ids=[skill_id], bloom_levels=[bloom_label], topic=None)
        picked = _pick_unseen_question(rows, used_question_ids)
        if picked is not None:
            return picked

    rows = _query_questions(skill_ids=[skill_id], bloom_levels=None, topic=None)
    picked = _pick_unseen_question(rows, used_question_ids)
    if picked is not None:
        return picked

    return _pick_any_question(rows)


def _extract_missing_prerequisites(option: Optional[dict]) -> List[str]:
    if not option:
        return []
    missing_rows = option.get("option_missing_prerequisites") or []
    missing = [row.get("missing_skill_id") for row in missing_rows if row.get("missing_skill_id")]
    return list(dict.fromkeys(missing))


def _topic_spillover_target(run: TopicPracticeRun) -> tuple[Optional[str], Optional[str]]:
    last_five = run.recent_topic_attempts[-TOPIC_PRACTICE_SPILLOVER_WINDOW:]
    repeated_missing_counts: Dict[str, int] = {}
    for item in last_five:
        if item.get("is_correct"):
            continue
        for sid in item.get("missing_prereq_ids", []):
            repeated_missing_counts[sid] = repeated_missing_counts.get(sid, 0) + 1

    if repeated_missing_counts:
        candidate_skill, count = max(repeated_missing_counts.items(), key=lambda entry: entry[1])
        if count >= TOPIC_PRACTICE_SPILLOVER_WRONG_TRIGGER_COUNT:
            return candidate_skill, "rule_a_repeated_missing_prerequisite"

    last_eight = run.recent_topic_attempts[-TOPIC_PRACTICE_ACCURACY_WINDOW:]
    if len(last_eight) < TOPIC_PRACTICE_ACCURACY_WINDOW:
        return None, None

    correct = sum(1 for item in last_eight if item.get("is_correct"))
    accuracy = correct / max(1, len(last_eight))
    if accuracy >= TOPIC_PRACTICE_ACCURACY_TRIGGER:
        return None, None

    candidate_skill_ids = set()
    for item in last_eight:
        if item.get("is_correct"):
            continue
        for sid in item.get("missing_prereq_ids", []):
            candidate_skill_ids.add(sid)

    weakest_skill_id = None
    weakest_mastery = 1.0
    for sid in candidate_skill_ids:
        mastery_probability = run.db_fetch(run.user_id, sid)["p_learned"]
        if mastery_probability < TOPIC_PRACTICE_PREREQ_MASTERY_TRIGGER and mastery_probability < weakest_mastery:
            weakest_skill_id = sid
            weakest_mastery = mastery_probability

    if weakest_skill_id is not None:
        return weakest_skill_id, "rule_b_low_topic_accuracy_and_low_prerequisite_mastery"
    return None, None


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


def _question_select_query(
    skill_ids: List[str] | None,
    bloom_levels: List[str] | None,
    topic: str | None,
    limit: int = 200,
):
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

    query = query.limit(limit)
    return query


def _query_questions(
    skill_ids: List[str] | None,
    bloom_levels: List[str] | None,
    topic: str | None,
    limit: int = 200,
) -> List[dict]:
    started_at = time.perf_counter()
    result = _question_select_query(skill_ids=skill_ids, bloom_levels=bloom_levels, topic=topic, limit=limit).execute()
    data, error = _extract_supabase_payload(result)
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    if error:
        _debug_search_log(
            "query failed "
            f"skills={_preview_values(skill_ids)} bloom={_preview_values(bloom_levels)} "
            f"topic={topic or '*'} limit={limit} elapsed_ms={elapsed_ms:.1f} error={error}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch questions: {error}")

    if data is None:
        rows: List[dict] = []
    elif isinstance(data, dict):
        rows = [data]
    else:
        rows = data

    _debug_search_log(
        "query ok "
        f"skills={_preview_values(skill_ids)} bloom={_preview_values(bloom_levels)} "
        f"topic={topic or '*'} limit={limit} rows={len(rows)} elapsed_ms={elapsed_ms:.1f}"
    )
    return rows


def _pick_unseen_question(rows: List[dict], used_ids: set[int]) -> Optional[dict]:
    candidates = [row for row in rows if int(row["id"]) not in used_ids]
    if not candidates:
        return None
    return random.choice(candidates)


def _pick_any_question(rows: List[dict]) -> Optional[dict]:
    if not rows:
        return None
    return random.choice(rows)


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


def _parse_bloom_level(raw: str | None) -> BloomLevel:
    if isinstance(raw, str):
        try:
            return BloomLevel[raw.strip().upper()]
        except KeyError:
            pass
    return BloomLevel.UNDERSTAND


def _select_random_question_row(
    run: DiagnosticRun,
    include_tested_skills: bool,
    allow_seen_questions: bool,
) -> Optional[dict]:
    if run.diagnostic_session is None:
        return None

    if include_tested_skills:
        candidate_skill_ids = list(run.section_skill_ids)
    else:
        allowed = set(run.section_skill_ids)
        candidate_skill_ids = [
            sid
            for sid, tested in run.diagnostic_session.tested.items()
            if (not tested) and sid in allowed
        ]

    if not candidate_skill_ids:
        return None

    rows = _query_questions(
        skill_ids=candidate_skill_ids,
        bloom_levels=None,
        topic=None,
        limit=DIAGNOSTIC_RANDOM_QUERY_LIMIT,
    )
    if allow_seen_questions:
        return _pick_any_question(rows)
    return _pick_unseen_question(rows, run.used_question_ids)


# Option text that points at another option by letter ("উত্তর খ সঠিক") or by
# position ("all of the above"). Moving such options would break the reference.
_POSITIONAL_OPTION_RE = re.compile(
    r"\b(?:option|choice|answer)s?\s*\(?[A-D]\)?(?![A-Za-z])"
    r"|(?:উত্তর|বিকল্প|অপশন)\s*\(?[কখগঘ]\)?"
    r"|\babove\b|উপরের|ওপরের|উপরোক্ত",
    re.IGNORECASE,
)


def _shuffle_options(row: dict) -> dict:
    """
    Return a copy of a question row with its options in random order, relabelled
    A, B, C... in that order.

    In the bank the correct answer is skewed heavily towards A and B. Shuffling once,
    when the question is served, means that skew can't be used to guess. The copy is
    what gets stored as the run's current question, so a re-fetch shows the same order
    and the answer handlers, which match on the displayed label, need no mapping.
    The source row is left untouched. Questions whose options refer to one another
    keep their original order.
    """
    options = sorted(row.get("question_options") or [], key=lambda item: item.get("option_label", ""))
    if len(options) < 2 or any(_POSITIONAL_OPTION_RE.search(o.get("option_text") or "") for o in options):
        return row

    labels = [o.get("option_label") for o in options]
    shuffled = random.sample(options, len(options))
    relabelled = [
        {**option, "option_label": label, "original_option_label": option.get("option_label")}
        for option, label in zip(shuffled, labels)
    ]
    return {**row, "question_options": relabelled}


def _question_payload(row: dict, topic_code_to_display: Dict[str, str]) -> dict:
    # questions.topic holds a topic_code (FK -> ontology_topics). Resolve it to the
    # catalog display name so the UI shows "Matrices and Determinants", not "MAT_MATRIX".
    topic_code = row.get("topic")
    if topic_code:
        topic_value = topic_code_to_display.get(topic_code, topic_code)
    else:
        topic_value = ""
        skill = SKILL_TREE.get_skill(row["skill_id"])
        if skill and skill.topics:
            topic_value = topic_code_to_display.get(skill.topics[0], skill.topics[0])

    # Only label and text go out before the answer. Each option's explanation and
    # missing prerequisites stay server-side: the correct option is the one with no
    # missing prerequisites, so sending them would give the answer away.
    # The explanation for the chosen option comes back in the answer response.
    # DEMO_SHOW_ANSWERS=1 is the one exception: it marks the correct option so a
    # presenter can steer a live demo. Never enable it for real students.
    options = row.get("question_options") or []
    normalized_options = []
    for option in sorted(options, key=lambda item: item.get("option_label", "")):
        item = {"label": option.get("option_label"), "text": option.get("option_text")}
        if DEMO_SHOW_ANSWERS:
            item["is_correct"] = bool(option.get("is_correct"))
        normalized_options.append(item)

    return {
        "question_id": row["id"],
        "bloom_level": row.get("bloom_level"),
        "skill_id": row["skill_id"],
        "skill_description": SKILL_DESCRIPTIONS.get(row["skill_id"], ""),
        "subject": SKILL_SUBJECTS.get(row["skill_id"], ""),
        "topic": topic_value,
        "topic_code": topic_code or "",
        "question_stem": row.get("question_stem"),
        "options": normalized_options,
    }


def _next_topic_practice_question(run: TopicPracticeRun) -> Optional[dict]:
    started_at = time.perf_counter()
    _debug_search_log(
        f"topic-next start session={run.session_id} answered={run.asked_count} "
        f"pending_skills={len([sid for sid in run.topic_skill_ids if run.db_fetch(run.user_id, sid)['mastery'] < TOPIC_PRACTICE_MASTERY_THRESHOLD])} "
        f"spillover_remaining={run.spillover_remaining}"
    )

    if run.completed:
        _debug_search_log(f"topic-next session={run.session_id} already completed")
        return None

    # Spillover always takes precedence once activated.
    if run.spillover_remaining > 0 and run.spillover_skill_id:
        spillover_skill = run.spillover_skill_id
        bloom_level = _practice_bloom_for_skill(run, spillover_skill)
        row = _pick_question_row_for_skill(
            used_question_ids=run.used_question_ids,
            skill_id=spillover_skill,
            bloom_level=bloom_level,
        )
        if row is not None:
            row = _shuffle_options(row)
            run.current_question_row = row
            run.current_skill_id = spillover_skill
            run.current_bloom_level = bloom_level
            run.current_mode = "spillover"
            run.last_delivery_mode = "spillover"
            run.used_question_ids.add(int(row["id"]))
            payload = _question_payload(row, run.topic_code_to_display)
            payload["delivery_mode"] = "spillover"
            _debug_search_log(
                f"topic-next hit session={run.session_id} mode=spillover skill={spillover_skill} "
                f"qid={row.get('id')} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
            )
            return payload

        # Could not generate spillover question; drop back to topic flow.
        run.spillover_remaining = 0
        run.spillover_skill_id = None

    if _topic_all_skills_mastered(run):
        run.completed = True
        run.completion_reason = "All topic skills reached mastery threshold."
        _debug_search_log(
            f"topic-next complete session={run.session_id} reason=all_mastered elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return None

    traversal_len = len(run.traversal_skill_ids)
    for _ in range(traversal_len):
        skill_id = run.traversal_skill_ids[run.traversal_index]
        run.traversal_index = (run.traversal_index + 1) % traversal_len

        if skill_id in run.exhausted_topic_skills:
            continue
        if run.db_fetch(run.user_id, skill_id)["mastery"] >= TOPIC_PRACTICE_MASTERY_THRESHOLD:
            continue

        bloom_level = _practice_bloom_for_skill(run, skill_id)
        row = _pick_question_row_for_skill(
            used_question_ids=run.used_question_ids,
            skill_id=skill_id,
            bloom_level=bloom_level,
        )
        if row is None:
            run.exhausted_topic_skills.add(skill_id)
            _debug_search_log(
                f"topic-next miss session={run.session_id} mode=topic skill={skill_id} action=mark_exhausted"
            )
            continue

        row = _shuffle_options(row)
        run.current_question_row = row
        run.current_skill_id = skill_id
        run.current_bloom_level = bloom_level
        run.current_mode = "topic"
        run.last_delivery_mode = "topic"
        run.used_question_ids.add(int(row["id"]))
        payload = _question_payload(row, run.topic_code_to_display)
        payload["delivery_mode"] = "topic"
        _debug_search_log(
            f"topic-next hit session={run.session_id} mode=topic skill={skill_id} qid={row.get('id')} "
            f"elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return payload

    unresolved = [
        sid
        for sid in run.topic_skill_ids
        if run.db_fetch(run.user_id, sid)["mastery"] < TOPIC_PRACTICE_MASTERY_THRESHOLD
    ]
    unresolved_not_exhausted = [sid for sid in unresolved if sid not in run.exhausted_topic_skills]

    if not unresolved:
        run.completed = True
        run.completion_reason = "All topic skills reached mastery threshold."
    elif not unresolved_not_exhausted:
        run.completed = True
        run.completion_reason = "Question bank has no remaining coverage for unresolved topic skills."

    _debug_search_log(
        f"topic-next no-question session={run.session_id} unresolved={len(unresolved)} "
        f"unresolved_not_exhausted={len(unresolved_not_exhausted)} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
    )

    return None


def _topic_practice_progress_payload(run: TopicPracticeRun) -> dict:
    pending_skill_ids = [
        sid
        for sid in run.topic_skill_ids
        if run.db_fetch(run.user_id, sid)["mastery"] < TOPIC_PRACTICE_MASTERY_THRESHOLD
    ]

    last_five = run.recent_topic_attempts[-TOPIC_PRACTICE_SPILLOVER_WINDOW:]
    repeated_missing_counts: Dict[str, int] = {}
    for item in last_five:
        if item.get("is_correct"):
            continue
        for sid in item.get("missing_prereq_ids", []):
            repeated_missing_counts[sid] = repeated_missing_counts.get(sid, 0) + 1

    last_eight = run.recent_topic_attempts[-TOPIC_PRACTICE_ACCURACY_WINDOW:]
    rolling_accuracy_last_8 = None
    if last_eight:
        correct = sum(1 for item in last_eight if item.get("is_correct"))
        rolling_accuracy_last_8 = correct / max(1, len(last_eight))

    next_traversal_skill_id = None
    if run.traversal_skill_ids:
        next_traversal_skill_id = run.traversal_skill_ids[run.traversal_index]

    return {
        "session_id": run.session_id,
        "user_id": run.user_id,
        "section_id": run.section_id,
        "topic_code": run.topic_code,
        "topic_display": run.topic_display,
        "answered_count": run.asked_count,
        "pending_skill_count": len(pending_skill_ids),
        "pending_skill_ids": pending_skill_ids,
        "spillover_active": run.spillover_remaining > 0 and bool(run.spillover_skill_id),
        "spillover_skill_id": run.spillover_skill_id,
        "spillover_remaining": run.spillover_remaining,
        "completed": run.completed,
        "completion_reason": run.completion_reason,
        "debug": {
            "traversal_index": run.traversal_index,
            "traversal_length": len(run.traversal_skill_ids),
            "next_traversal_skill_id": next_traversal_skill_id,
            "current_question_skill_id": run.current_skill_id,
            "current_question_mode": run.current_mode if run.current_question_row is not None else None,
            "last_delivery_mode": run.last_delivery_mode,
            "rolling_accuracy_last_8": rolling_accuracy_last_8,
            "rolling_accuracy_window_size": len(last_eight),
            "missing_prereq_counts_last_5": repeated_missing_counts,
            "missing_prereq_window_size": len(last_five),
            "last_spillover_reason": run.last_spillover_reason,
            "last_spillover_skill_id": run.last_spillover_skill_id,
            "last_spillover_trigger_answer_count": run.last_spillover_trigger_answer_count,
            "exhausted_topic_skill_count": len(run.exhausted_topic_skills),
            "exhausted_topic_skill_ids": sorted(run.exhausted_topic_skills),
        },
    }


def _select_question_row_for_spec(run: DiagnosticRun, spec: QuestionSpec) -> Optional[dict]:
    if DIAGNOSTIC_RANDOM_SELECTION:
        return _select_random_question_row(
            run,
            include_tested_skills=False,
            allow_seen_questions=False,
        )

    started_at = time.perf_counter()
    _debug_search_log(
        f"diag-select start session={run.session_id} asked={run.asked_count + 1} "
        f"skill={spec.skill_id} bloom={spec.bloom_level.name} topic={spec.topic} used={len(run.used_question_ids)}"
    )

    bloom_candidates = _nearby_bloom_labels(spec.bloom_level)
    # questions.topic is FK -> ontology_topics(topic_code), so it stores a topic CODE.
    # Filtering by the catalog display name here could never match a row.
    topic_filter = spec.topic

    # Tier 1: same skill + nearby bloom
    tier1_queries = 0
    tier1_started = time.perf_counter()
    for bloom_label in bloom_candidates:
        tier1_queries += 1
        rows = _query_questions(skill_ids=[spec.skill_id], bloom_levels=[bloom_label], topic=topic_filter)
        picked = _pick_unseen_question(rows, run.used_question_ids)
        if picked is not None:
            _debug_search_log(
                f"diag-select hit tier=1 session={run.session_id} skill={spec.skill_id} bloom={bloom_label} "
                f"qid={picked.get('id')} queries={tier1_queries} tier_elapsed_ms={(time.perf_counter() - tier1_started) * 1000.0:.1f} "
                f"total_elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
            )
            return picked

    _debug_search_log(
        f"diag-select miss tier=1 session={run.session_id} skill={spec.skill_id} queries={tier1_queries} "
        f"tier_elapsed_ms={(time.perf_counter() - tier1_started) * 1000.0:.1f}"
    )

    # Tier 1 fallback: same skill + nearby bloom without topic filter
    tier1b_queries = 0
    tier1b_started = time.perf_counter()
    for bloom_label in bloom_candidates:
        tier1b_queries += 1
        rows = _query_questions(skill_ids=[spec.skill_id], bloom_levels=[bloom_label], topic=None)
        picked = _pick_unseen_question(rows, run.used_question_ids)
        if picked is not None:
            _debug_search_log(
                f"diag-select hit tier=1b session={run.session_id} skill={spec.skill_id} bloom={bloom_label} "
                f"qid={picked.get('id')} queries={tier1b_queries} tier_elapsed_ms={(time.perf_counter() - tier1b_started) * 1000.0:.1f} "
                f"total_elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
            )
            return picked

    _debug_search_log(
        f"diag-select miss tier=1b session={run.session_id} skill={spec.skill_id} queries={tier1b_queries} "
        f"tier_elapsed_ms={(time.perf_counter() - tier1b_started) * 1000.0:.1f}"
    )

    # Tier 2: same topic + nearby skills (distance based), nearby bloom
    tier2_started = time.perf_counter()
    tier2_queries = 0
    mastery_map = {sid: run.db_fetch(run.user_id, sid)["mastery"] for sid in run.section_skill_ids}
    nearby_by_distance = _nearby_topic_skills(run, target_skill_id=spec.skill_id, topic_code=spec.topic)
    for distance in sorted(nearby_by_distance.keys()):
        nearby_skills = nearby_by_distance[distance]
        for bloom_label in bloom_candidates:
            tier2_queries += 1
            rows = _query_questions(skill_ids=nearby_skills, bloom_levels=[bloom_label], topic=topic_filter)
            picked = _pick_unseen_low_mastery_question(rows, run.used_question_ids, mastery_map)
            if picked is not None:
                _debug_search_log(
                    f"diag-select hit tier=2 session={run.session_id} distance={distance} bloom={bloom_label} "
                    f"qid={picked.get('id')} queries={tier2_queries} tier_elapsed_ms={(time.perf_counter() - tier2_started) * 1000.0:.1f} "
                    f"total_elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
                )
                return picked

    _debug_search_log(
        f"diag-select miss tier=2 session={run.session_id} skill={spec.skill_id} queries={tier2_queries} "
        f"nearby_groups={len(nearby_by_distance)} tier_elapsed_ms={(time.perf_counter() - tier2_started) * 1000.0:.1f} "
        f"total_elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
    )

    return None


def _next_question_for_run(run: DiagnosticRun) -> Optional[dict]:
    if run.diagnostic_session is None:
        raise HTTPException(status_code=500, detail="Diagnostic session is not initialized.")

    started_at = time.perf_counter()
    _debug_search_log(
        f"diag-next start session={run.session_id} asked={run.asked_count} max={run.max_questions} random_mode={DIAGNOSTIC_RANDOM_SELECTION}"
    )

    if DIAGNOSTIC_RANDOM_SELECTION:
        # First prefer untested-skill unseen questions; then progressively relax constraints
        # so sparse question banks can still reach the configured diagnostic length.
        row = _select_random_question_row(
            run,
            include_tested_skills=False,
            allow_seen_questions=False,
        )
        if row is None:
            row = _select_random_question_row(
                run,
                include_tested_skills=True,
                allow_seen_questions=False,
            )
        if row is None:
            row = _select_random_question_row(
                run,
                include_tested_skills=True,
                allow_seen_questions=True,
            )
        if row is None:
            # Absolute fallback for under-populated section coverage.
            row = _pick_any_question(
                _query_questions(
                    skill_ids=None,
                    bloom_levels=None,
                    topic=None,
                    limit=DIAGNOSTIC_RANDOM_QUERY_LIMIT,
                )
            )
        if row is None:
            _debug_search_log(
                f"diag-next no-question session={run.session_id} mode=random elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
            )
            return None

        skill_id = row["skill_id"]
        bloom_level = _parse_bloom_level(row.get("bloom_level"))
        skill = SKILL_TREE.get_skill(skill_id)
        # Fall back to the question's own topic code rather than a hardcoded one.
        topic_code = skill.topics[0] if skill and skill.topics else row.get("topic")

        run.current_spec = QuestionSpec(
            topic=topic_code,
            skill_id=skill_id,
            bloom_level=bloom_level,
        )
        row = _shuffle_options(row)
        run.current_question_row = row
        run.used_question_ids.add(int(row["id"]))
        _debug_search_log(
            f"diag-next hit session={run.session_id} mode=random qid={row.get('id')} skill={skill_id} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return _question_payload(row, run.topic_code_to_display)

    attempts = 0
    while run.asked_count < run.max_questions:
        attempts += 1
        spec = run.diagnostic_session.next_question_spec()
        if spec is None:
            _debug_search_log(
                f"diag-next stop session={run.session_id} reason=no_spec attempts={attempts} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
            )
            return None

        row = _select_question_row_for_spec(run, spec)
        if row is None:
            # No question found for this selected spec; skip this skill and continue.
            run.diagnostic_session.tested[spec.skill_id] = True
            _debug_search_log(
                f"diag-next skip-spec session={run.session_id} skill={spec.skill_id} attempts={attempts}"
            )
            continue

        run.current_spec = spec
        row = _shuffle_options(row)
        run.current_question_row = row
        run.used_question_ids.add(int(row["id"]))
        _debug_search_log(
            f"diag-next hit session={run.session_id} qid={row.get('id')} skill={spec.skill_id} attempts={attempts} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return _question_payload(row, run.topic_code_to_display)

    _debug_search_log(
        f"diag-next stop session={run.session_id} reason=asked_limit attempts={attempts} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
    )
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
        "subject": _section_subject(section_id),
        "diagnostic_required": diagnostic_required,
        "diagnostic_completed": diagnostic_completed,
        "mastery_locked": not diagnostic_completed,
        "diagnostic_answered_count": int(progress.get("answered_count", 0)),
        "diagnostic_total_questions": _diagnostic_length_for_section(skill_ids),
        "active_diagnostic_session_id": progress.get("active_session_id"),
    }


def _reset_section_journey(user_id: str, section_id: str) -> dict:
    section = _get_section(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Unknown section '{section_id}'.")

    section_skill_ids = _section_skill_ids(section)
    deleted_rows = 0

    if section_skill_ids:
        existing_rows_result = (
            db.table("user_skill")
            .select("skill_id")
            .eq("user_id", user_id)
            .in_("skill_id", section_skill_ids)
            .execute()
        )
        existing_rows_data, existing_rows_error = _extract_supabase_payload(existing_rows_result)
        if existing_rows_error:
            raise HTTPException(status_code=500, detail=f"Failed to inspect user skill data: {existing_rows_error}")

        if isinstance(existing_rows_data, list):
            deleted_rows = len(existing_rows_data)
        elif isinstance(existing_rows_data, dict) and existing_rows_data:
            deleted_rows = 1

        delete_result = (
            db.table("user_skill")
            .delete()
            .eq("user_id", user_id)
            .in_("skill_id", section_skill_ids)
            .execute()
        )
        _, delete_error = _extract_supabase_payload(delete_result)
        if delete_error:
            raise HTTPException(status_code=500, detail=f"Failed to reset user skill data: {delete_error}")

    removed_session_ids = []
    for session_id, run in list(DIAGNOSTIC_RUNS.items()):
        if run.user_id == user_id and run.section_id == section_id:
            removed_session_ids.append(session_id)
            DIAGNOSTIC_RUNS.pop(session_id, None)

    for session_id, run in list(TOPIC_PRACTICE_RUNS.items()):
        if run.user_id == user_id and run.section_id == section_id:
            removed_session_ids.append(session_id)
            TOPIC_PRACTICE_RUNS.pop(session_id, None)

    SECTION_PROGRESS.pop(_progress_key(user_id, section_id), None)

    return {
        "user_id": user_id,
        "section_id": section_id,
        "deleted_skill_rows": deleted_rows,
        "cleared_session_ids": removed_session_ids,
    }


def _section_is_diagnosed(
    user_id: str, section: dict, skill_ids: List[str], stored: Dict[str, float]
) -> bool:
    """Same rule as _section_state, but against an already-loaded mastery dict."""
    progress = SECTION_PROGRESS.get(_progress_key(user_id, section["id"]), {})
    has_records = any(sid in stored for sid in skill_ids)
    return bool(progress.get("diagnostic_completed", has_records))


def _user_payload(row: dict) -> dict:
    return {
        "user_id": row["user_id"],
        "user_name": row["user_name"],
        "is_admin": row["user_name"] in admin_usernames(),
    }


def _session_payload(row: dict) -> dict:
    return {"token": issue_token(row["user_id"], row["user_name"]), "user": _user_payload(row)}


def _require_own_session(runs: dict):
    """Route guard: a diagnostic/practice session is only usable by the learner who started it."""
    def guard(session_id: str, auth: AuthUser = Depends(current_user)) -> None:
        run = runs.get(session_id)
        if run is not None and run.user_id != auth.user_id:
            raise HTTPException(status_code=403, detail="This session belongs to another learner.")
    return guard


def _require_same_user(auth: AuthUser, user_id: str) -> None:
    if user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="You can only start sessions for your own account.")


def _user_row_by_name(user_name: str) -> Optional[dict]:
    result = db.table("users").select("*").eq("user_name", user_name).maybe_single().execute()
    data, error = _extract_supabase_payload(result)
    if error:
        raise HTTPException(status_code=500, detail=str(error))
    return data


# ------------------------------------------------------------------ endpoints: catalog + user auth
@app.get("/catalog")
def get_catalog():
    return PLATFORM_CATALOG


# Cached for a few minutes: counting the question bank pages through ~20k rows.
_PUBLIC_STATS_TTL_SEC = 600.0
_PUBLIC_STATS_CACHE: Dict[str, object] = {"at": 0.0, "data": None}


def _count_served_questions() -> int:
    """Questions whose skill is in the served ontology (legacy-keyed items excluded)."""
    served = set(SKILL_DESCRIPTIONS)
    total, offset, page_size = 0, 0, 1000
    while True:
        result = (db.table("questions").select("skill_id").order("id")
                  .range(offset, offset + page_size - 1).execute())
        data, error = _extract_supabase_payload(result)
        if error:
            raise HTTPException(status_code=500, detail=f"Could not count questions: {error}")
        rows = data or []
        total += sum(1 for row in rows if row.get("skill_id") in served)
        if len(rows) < page_size:
            return total
        offset += page_size


@app.get("/stats/public")
def get_public_stats():
    """Real platform figures for the landing page (no learner data beyond a count)."""
    now = time.time()
    cached = _PUBLIC_STATS_CACHE.get("data")
    if cached is not None and now - float(_PUBLIC_STATS_CACHE["at"]) < _PUBLIC_STATS_TTL_SEC:
        return cached

    courses = PLATFORM_CATALOG.get("courses", [])
    sections = [s for c in courses for s in c.get("sections", []) if s.get("enabled")]
    learners_result = db.table("users").select("user_id", count="exact").limit(1).execute()
    data = {
        "subjects": len(courses),
        "sections": len(sections),
        "topics": sum(len(s.get("topics", [])) for s in sections),
        "skills": len(SKILL_DESCRIPTIONS),
        "skills_by_subject": {
            subject: sum(1 for sid in SKILL_DESCRIPTIONS if SKILL_SUBJECTS.get(sid) == subject)
            for subject in sorted({c.get("subject") for c in courses if c.get("subject")})
        },
        "prerequisite_edges": len(SKILL_EDGES),
        "questions": _count_served_questions(),
        "learners": int(getattr(learners_result, "count", 0) or 0),
    }
    _PUBLIC_STATS_CACHE.update(at=now, data=data)
    return data


@app.on_event("startup")
def _warm_public_stats() -> None:
    """Fill the stats cache off the request path so the landing page never waits on it."""
    import threading

    def _run():
        try:
            get_public_stats()
        except Exception as exc:  # the endpoint recomputes on demand if this fails
            print(f"WARN: could not pre-compute public stats: {exc}")

    threading.Thread(target=_run, daemon=True).start()


@app.get("/users/{user_id}/progress", dependencies=[Depends(require_self)])
def get_user_progress(user_id: str):
    """
    One learner's progress across the whole catalogue in a single request.

    A section counts as diagnosed by the same rule _section_state uses, so the
    courses dashboard and the section pages always agree. Mastery for a section
    is the mean over all of its skills (an untouched skill counts as 0); course and
    overall figures average the skills of diagnosed sections only.
    """
    stored = _stored_mastery_for_user(user_id)
    out_courses: List[dict] = []
    overall_values: List[float] = []
    mastered_total = 0
    first_unlocked: Optional[dict] = None

    for course in PLATFORM_CATALOG.get("courses", []):
        course_values: List[float] = []
        out_sections: List[dict] = []
        for section in course.get("sections", []):
            if not section.get("enabled"):
                continue
            skill_ids = _section_skill_ids(section)
            diagnosed = _section_is_diagnosed(user_id, section, skill_ids, stored)
            values = [stored.get(sid, 0.0) for sid in skill_ids]
            mastered = sum(1 for v in values if v >= MASTERY_NOTIFY_THRESHOLD)
            if diagnosed and values:
                course_values += values
                mastered_total += mastered
                if first_unlocked is None:
                    first_unlocked = {"course_id": course["id"], "section_id": section["id"]}
            out_sections.append({
                "section_id": section["id"],
                "diagnosed": diagnosed,
                "skills": len(skill_ids),
                "skills_mastered": mastered if diagnosed else 0,
                "mastery": round(sum(values) / len(values), 1) if diagnosed and values else None,
            })
        overall_values += course_values
        out_courses.append({
            "course_id": course["id"],
            "subject": course.get("subject"),
            "sections_total": len(out_sections),
            "sections_diagnosed": sum(1 for s in out_sections if s["diagnosed"]),
            "mastery": round(sum(course_values) / len(course_values), 1) if course_values else None,
            "sections": out_sections,
        })

    return {
        "user_id": user_id,
        "courses": out_courses,
        "active_courses": sum(1 for c in out_courses if c["sections_diagnosed"] > 0),
        "average_mastery": round(sum(overall_values) / len(overall_values), 1) if overall_values else None,
        "skills_mastered": mastered_total,
        "first_unlocked_section": first_unlocked,
    }


@app.post("/auth/signup")
def signup(payload: Credentials):
    user_name = payload.user_name.strip()
    if not user_name:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")
    if len(payload.password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    # Admin accounts are created with set_password.py, never by self-signup:
    # otherwise the first visitor to register an allow-listed name becomes admin.
    if user_name in admin_usernames():
        raise HTTPException(status_code=403, detail="This username is reserved.")

    try:
        if _user_row_by_name(user_name) is not None:
            raise HTTPException(status_code=409, detail=f"User '{user_name}' already exists.")

        insert_result = (
            db.table("users")
            .insert({"user_name": user_name, "password_hash": hash_password(payload.password)})
            .execute()
        )
        insert_data, insert_error = _extract_supabase_payload(insert_result)

        if insert_error:
            if "duplicate" in str(insert_error).lower() or "unique" in str(insert_error).lower():
                raise HTTPException(status_code=409, detail=f"User '{user_name}' already exists.")
            raise HTTPException(status_code=500, detail=f"Insert failed: {insert_error}")

        if insert_data is None:
            insert_data = _user_row_by_name(user_name)
            if insert_data is None:
                raise HTTPException(status_code=500, detail="Insert succeeded but no user row was returned.")

        row = insert_data[0] if isinstance(insert_data, list) else insert_data
        return _session_payload(row)

    except HTTPException:
        raise
    except Exception as exc:
        print("ERROR:", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/auth/login")
def login(payload: Credentials, request: Request):
    user_name = payload.user_name.strip()
    throttle_key = f"{request.client.host if request.client else '-'}|{user_name}"
    check_login_throttle(throttle_key)

    row = _user_row_by_name(user_name)
    if row is not None and not row.get("password_hash"):
        raise HTTPException(
            status_code=403,
            detail="This account has no password yet. Ask an administrator to set one.",
        )
    if row is None or not verify_password(payload.password, row["password_hash"]):
        record_login_failure(throttle_key)
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    clear_login_failures(throttle_key)
    return _session_payload(row)


@app.get("/auth/me")
def get_me(auth: AuthUser = Depends(current_user)):
    result = db.table("users").select("*").eq("user_id", auth.user_id).maybe_single().execute()
    data, error = _extract_supabase_payload(result)
    if error:
        raise HTTPException(status_code=500, detail=str(error))
    if data is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return _user_payload(data)


# ------------------------------------------------------------------ endpoints: section state + mastery
@app.get("/users/{user_id}/sections/{section_id}/state", dependencies=[Depends(require_self)])
def get_section_state(user_id: str, section_id: str):
    return _section_state(user_id=user_id, section_id=section_id)


@app.get("/users/{user_id}/sections/{section_id}/mastery", dependencies=[Depends(require_self)])
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
            "subject": SKILL_SUBJECTS.get(sid, ""),
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


@app.get("/users/{user_id}/mastery", dependencies=[Depends(require_self)])
def get_user_mastery(user_id: str, subject: Optional[str] = None):
    """
    One learner's mastery across every section they have diagnosed, as a single
    table + map. Unlike the per-section view, prerequisite edges that cross
    section boundaries are kept (flagged cross_section), so a skill shows the
    prerequisite it depends on from another chapter. `subject` narrows the
    table/map; the section list and subject counts always cover everything.
    """
    stored = _stored_mastery_for_user(user_id)
    out_sections: List[dict] = []
    skill_sections: Dict[str, List[str]] = {}
    subject_skills: Dict[str, set] = {}

    for course in PLATFORM_CATALOG.get("courses", []):
        course_subject = course.get("subject") or ""
        for section in course.get("sections", []):
            if not section.get("enabled"):
                continue
            skill_ids = _section_skill_ids(section)
            if not skill_ids or not _section_is_diagnosed(user_id, section, skill_ids, stored):
                continue
            values = [stored.get(sid, 0.0) for sid in skill_ids]
            out_sections.append({
                "course_id": course["id"],
                "section_id": section["id"],
                "title": section.get("title") or section["id"],
                "title_bn": section.get("title_bn"),
                "subject": course_subject,
                "skills": len(skill_ids),
                "skills_mastered": sum(1 for v in values if v >= MASTERY_NOTIFY_THRESHOLD),
                "mastery": round(sum(values) / len(values), 1),
            })
            subject_skills.setdefault(course_subject, set()).update(skill_ids)
            if subject and course_subject != subject:
                continue
            for sid in skill_ids:
                skill_sections.setdefault(sid, []).append(section.get("title") or section["id"])

    rows: List[dict] = []
    for sid in sorted(skill_sections):
        skill = SKILL_TREE.get_skill(sid)
        rows.append({
            "skill_id": sid,
            "skill_description": SKILL_DESCRIPTIONS.get(sid, ""),
            "subject": SKILL_SUBJECTS.get(sid, ""),
            "topics": [TOPIC_LABELS.get(code, code) for code in (skill.topics if skill else [])],
            "sections": skill_sections[sid],
            "mastery": round(stored.get(sid, 0.0), 2),
        })

    edges: List[dict] = []
    for edge in SKILL_EDGES:
        src, dst = edge["source"], edge["target"]
        if src in skill_sections and dst in skill_sections:
            shared = set(skill_sections[src]) & set(skill_sections[dst])
            edges.append({"source": src, "target": dst, "cross_section": not shared})

    return {
        "user_id": user_id,
        "subject": subject,
        "subjects": [
            {"subject": name, "skills": len(ids)} for name, ids in subject_skills.items()
        ],
        "sections": out_sections,
        "table": rows,
        "map": {"nodes": rows, "edges": edges},
        "cross_section_edges": sum(1 for e in edges if e["cross_section"]),
    }


@app.post("/users/{user_id}/sections/{section_id}/diagnostic/retake", dependencies=[Depends(require_self)])
def retake_section_diagnostic(user_id: str, section_id: str):
    reset_result = _reset_section_journey(user_id=user_id, section_id=section_id)
    return {
        "ok": True,
        "message": "Section journey reset. Start diagnostic to begin again.",
        **reset_result,
        "state": _section_state(user_id=user_id, section_id=section_id),
    }


# ------------------------------------------------------------------ endpoints: topic practice flow
@app.post("/topic-practice/start")
def start_topic_practice(request: TopicPracticeStartRequest, auth: AuthUser = Depends(current_user)):
    _require_same_user(auth, request.user_id)
    section = _get_section(request.section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Unknown section '{request.section_id}'.")
    if not section.get("enabled", False):
        raise HTTPException(status_code=400, detail=f"Section '{request.section_id}' is not available yet.")

    section_topic_codes = set(_section_topic_codes(section))
    if request.topic_code not in section_topic_codes:
        raise HTTPException(status_code=404, detail=f"Topic '{request.topic_code}' is not available in this section.")

    state = _section_state(user_id=request.user_id, section_id=request.section_id)
    if not state["diagnostic_completed"]:
        raise HTTPException(status_code=400, detail="Complete section diagnostic before starting topic practice.")

    topic_skill_ids = _topic_skill_ids_for_section(section, request.topic_code)
    if not topic_skill_ids:
        raise HTTPException(status_code=404, detail="No ontology skills are mapped to this topic.")

    topic_mastery = _mastery_map_for_user(user_id=request.user_id, skill_ids=topic_skill_ids)
    start_skill_id = _pick_zpd_start_skill(topic_mastery, topic_skill_ids)

    if start_skill_id is None:
        return {
            "completed": True,
            "message": "All topic skills are already at or above mastery threshold.",
            "question": None,
            "topic_code": request.topic_code,
            "topic_display": _section_topic_display_name(section, request.topic_code),
            "pending_skill_count": 0,
        }

    traversal = _topic_topological_order(topic_skill_ids)
    if not traversal:
        raise HTTPException(status_code=500, detail="Topic skill traversal could not be prepared.")
    traversal = _rotate_skill_order(traversal, start_skill_id)

    session_id = str(uuid.uuid4())
    run = TopicPracticeRun(
        session_id=session_id,
        user_id=request.user_id,
        section_id=request.section_id,
        topic_code=request.topic_code,
        topic_display=_section_topic_display_name(section, request.topic_code),
        topic_skill_ids=topic_skill_ids,
        section_skill_ids=_section_skill_ids(section),
        traversal_skill_ids=traversal,
        topic_code_to_display=_topic_code_to_display_name(section),
    )
    TOPIC_PRACTICE_RUNS[session_id] = run

    question = _next_topic_practice_question(run)
    payload = _topic_practice_progress_payload(run)
    if question is None:
        return {
            **payload,
            "question": None,
        }

    return {
        **payload,
        "question_index": run.asked_count + 1,
        "question": question,
    }


@app.get("/topic-practice/{session_id}/status", dependencies=[Depends(_require_own_session(TOPIC_PRACTICE_RUNS))])
def get_topic_practice_status(session_id: str):
    run = TOPIC_PRACTICE_RUNS.get(session_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Topic practice session not found.")

    return {
        **_topic_practice_progress_payload(run),
        "awaiting_answer": run.current_question_row is not None,
    }


@app.get("/topic-practice/{session_id}/next", dependencies=[Depends(_require_own_session(TOPIC_PRACTICE_RUNS))])
def get_next_topic_practice_question(session_id: str):
    started_at = time.perf_counter()
    run = TOPIC_PRACTICE_RUNS.get(session_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Topic practice session not found.")

    if run.completed:
        _debug_search_log(
            f"topic-next-endpoint session={session_id} state=completed elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return {
            **_topic_practice_progress_payload(run),
            "question": None,
        }

    if run.current_question_row is not None and run.current_skill_id is not None:
        question = _question_payload(run.current_question_row, run.topic_code_to_display)
        question["delivery_mode"] = run.current_mode
        _debug_search_log(
            f"topic-next-endpoint session={session_id} state=existing_question skill={run.current_skill_id} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return {
            **_topic_practice_progress_payload(run),
            "question_index": run.asked_count + 1,
            "question": question,
        }

    question = _next_topic_practice_question(run)
    if question is None:
        _debug_search_log(
            f"topic-next-endpoint session={session_id} state=no_question elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return {
            **_topic_practice_progress_payload(run),
            "question": None,
        }

    _debug_search_log(
        f"topic-next-endpoint session={session_id} state=next_question skill={question.get('skill_id')} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
    )
    return {
        **_topic_practice_progress_payload(run),
        "question_index": run.asked_count + 1,
        "question": question,
    }


@app.post("/topic-practice/{session_id}/answer", dependencies=[Depends(_require_own_session(TOPIC_PRACTICE_RUNS))])
def submit_topic_practice_answer(session_id: str, request: TopicPracticeAnswerRequest):
    run = TOPIC_PRACTICE_RUNS.get(session_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Topic practice session not found.")
    if run.current_question_row is None or run.current_skill_id is None or run.current_bloom_level is None:
        raise HTTPException(status_code=400, detail="No active topic practice question is awaiting an answer.")

    selected_label = request.selected_option_label.strip().upper()
    options = run.current_question_row.get("question_options") or []
    selected_option = None
    for option in options:
        if str(option.get("option_label", "")).upper() == selected_label:
            selected_option = option
            break

    if selected_option is None:
        raise HTTPException(status_code=400, detail="Selected option label is invalid for the current question.")

    is_correct = bool(selected_option.get("is_correct", False))
    missing_prereq_ids = [] if is_correct else _extract_missing_prerequisites(selected_option)

    MASTERY_UPDATER.update_answer(
        userid=run.user_id,
        skill_id=run.current_skill_id,
        bloom_level=run.current_bloom_level,
        is_correct=is_correct,
        db_fetch=run.db_fetch,
        db_update=run.db_update,
        mode=UpdateMode.REGULAR,
    )
    run.flush_dirty_states()
    run.asked_count += 1

    spillover_activated = None
    if run.current_mode == "topic":
        run.recent_topic_attempts.append(
            {
                "is_correct": is_correct,
                "missing_prereq_ids": missing_prereq_ids,
            }
        )
        run.recent_topic_attempts = run.recent_topic_attempts[-32:]

        if (not is_correct) and run.spillover_remaining <= 0 and missing_prereq_ids:
            spillover_skill_id, spillover_reason = _topic_spillover_target(run)
            if spillover_skill_id:
                run.spillover_skill_id = spillover_skill_id
                run.spillover_remaining = TOPIC_PRACTICE_SPILLOVER_QUESTION_COUNT
                run.last_spillover_skill_id = spillover_skill_id
                run.last_spillover_reason = spillover_reason
                run.last_spillover_trigger_answer_count = run.asked_count
                spillover_activated = {
                    "skill_id": spillover_skill_id,
                    "reason": spillover_reason,
                    "injected_question_count": TOPIC_PRACTICE_SPILLOVER_QUESTION_COUNT,
                }
    elif run.current_mode == "spillover":
        run.spillover_remaining = max(0, run.spillover_remaining - 1)
        if run.spillover_remaining == 0:
            run.spillover_skill_id = None

    run.current_question_row = None
    run.current_skill_id = None
    run.current_bloom_level = None
    run.current_mode = "topic"

    if _topic_all_skills_mastered(run) and run.spillover_remaining <= 0:
        run.completed = True
        if run.completion_reason is None:
            run.completion_reason = "All topic skills reached mastery threshold."

    return {
        **_topic_practice_progress_payload(run),
        "selected_option_label": selected_label,
        "selected_option_explanation": selected_option.get("explanation") or "",
        "is_correct": is_correct,
        "spillover_activated": spillover_activated,
        "next_question": None,
    }


# ------------------------------------------------------------------ endpoints: diagnostic flow
@app.post("/diagnostic/start")
def start_diagnostic(request: DiagnosticStartRequest, auth: AuthUser = Depends(current_user)):
    _require_same_user(auth, request.user_id)
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
        max_questions=_diagnostic_length_for_section(section_skill_ids),
    )

    # The full tree still drives propagation (ancestor pull-up, successor
    # gating), but only the section's skills are ever selected for testing.
    run.diagnostic_session = DiagnosticSession(
        skill_tree=SKILL_TREE,
        userid=request.user_id,
        db_fetch=run.db_fetch,
        db_update=run.db_update,
        stop_threshold=0.0,
        candidate_skill_ids=section_skill_ids,
        stored_mastery=_stored_mastery_for_user(request.user_id),
    )

    # Seeded values are runtime state for this session, not new evidence;
    # don't write them back. Only answers produce writes.
    run.clear_dirty_states()

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


@app.get("/diagnostic/{session_id}/status", dependencies=[Depends(_require_own_session(DIAGNOSTIC_RUNS))])
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


@app.get("/diagnostic/{session_id}/next", dependencies=[Depends(_require_own_session(DIAGNOSTIC_RUNS))])
def get_next_diagnostic_question(session_id: str):
    started_at = time.perf_counter()
    run = DIAGNOSTIC_RUNS.get(session_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found.")

    if run.asked_count >= run.max_questions:
        _debug_search_log(
            f"diag-next-endpoint session={session_id} state=completed elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return {
            "session_id": run.session_id,
            "answered_count": run.asked_count,
            "total_questions": run.max_questions,
            "completed": True,
            "question": None,
        }

    # If a question is already active and unanswered, return it as-is.
    if run.current_question_row is not None and run.current_spec is not None:
        _debug_search_log(
            f"diag-next-endpoint session={session_id} state=existing_question skill={run.current_spec.skill_id} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )
        return {
            "session_id": run.session_id,
            "answered_count": run.asked_count,
            "total_questions": run.max_questions,
            "completed": False,
            "question_index": run.asked_count + 1,
            "question": _question_payload(run.current_question_row, run.topic_code_to_display),
        }

    question = _next_question_for_run(run)
    if question is None:
        progress_key = _progress_key(run.user_id, run.section_id)
        progress = SECTION_PROGRESS.get(progress_key, {})
        progress["diagnostic_completed"] = True
        progress["active_session_id"] = None
        progress["answered_count"] = run.asked_count
        SECTION_PROGRESS[progress_key] = progress

        _debug_search_log(
            f"diag-next-endpoint session={session_id} state=no_question answered={run.asked_count} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
        )

        return {
            "session_id": run.session_id,
            "answered_count": run.asked_count,
            "total_questions": run.max_questions,
            "completed": True,
            "question": None,
        }

    _debug_search_log(
        f"diag-next-endpoint session={session_id} state=next_question skill={question.get('skill_id')} elapsed_ms={(time.perf_counter() - started_at) * 1000.0:.1f}"
    )
    return {
        "session_id": run.session_id,
        "answered_count": run.asked_count,
        "total_questions": run.max_questions,
        "completed": False,
        "question_index": run.asked_count + 1,
        "question": question,
    }


@app.post("/diagnostic/{session_id}/answer", dependencies=[Depends(_require_own_session(DIAGNOSTIC_RUNS))])
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

    # In random testing mode with sparse banks, we may intentionally retest skills.
    # Reset the tested flag so DiagnosticSession accepts the answer update.
    if DIAGNOSTIC_RANDOM_SELECTION and run.current_spec.skill_id in run.diagnostic_session.tested:
        run.diagnostic_session.tested[run.current_spec.skill_id] = False

    run.diagnostic_session.record_answer(
        skill_id=run.current_spec.skill_id,
        bloom_level=run.current_spec.bloom_level,
        is_correct=is_correct,
    )
    run.flush_dirty_states()

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

    # Clear current question state after answer is processed.
    run.current_spec = None
    run.current_question_row = None

    completed = run.asked_count >= run.max_questions
    if completed:
        progress["diagnostic_completed"] = True
        progress["active_session_id"] = None
    else:
        progress["diagnostic_completed"] = False
        progress["active_session_id"] = run.session_id
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
        "next_question": None,
    }

    return response
