"""
smoke_test_engine.py
--------------------
End-to-end exercise of the adaptive engine against an in-memory stand-in for
Supabase. No network, no credentials, no live database.

What it proves:
  1. The ontology in tree_data/ loads into SkillTree and the catalog agrees with it.
  2. A section diagnostic runs start -> next -> answer to completion and moves mastery.
  3. Tier 1 of the question search (skill + bloom + TOPIC) actually matches rows.
     This is the regression guard for the topic-code bug: questions.topic is a FK to
     ontology_topics(topic_code), so filtering it by a display label silently matched
     nothing and every question fell through to the no-topic tier.
  4. Correct answers propagate up the prerequisite DAG (ancestor pull-up).
  5. Topic practice runs, and prerequisite spillover fires on repeated wrong answers.

Run:
    Backend/.venv/Scripts/python.exe Backend/smoke_test_engine.py
"""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

os.environ.setdefault("SUPABASE_URL", "http://stub.local")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "stub-key")
os.environ.setdefault("NEXT_QUESTION_DEBUG_LOGS", "false")

BLOOMS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


# ---------------------------------------------------------------------------
# In-memory Supabase stand-in
# ---------------------------------------------------------------------------
class FakeQuery:
    def __init__(self, db, table, rows):
        self.db, self.table_name, self.rows = db, table, list(rows)
        self._single = False
        self._mode = "select"
        self._payload = None
        self._conflict = None

    # -- filters
    def select(self, *_a, **_k):
        self._mode = "select"
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def in_(self, col, vals):
        allowed = set(vals)
        self.rows = [r for r in self.rows if r.get(col) in allowed]
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def maybe_single(self):
        self._single = True
        return self

    # -- writes
    def insert(self, payload):
        self._mode, self._payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._mode, self._payload, self._conflict = "upsert", payload, on_conflict
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def execute(self):
        if self._mode == "select":
            rows = self._expand(self.rows)
            data = (rows[0] if rows else None) if self._single else rows
            return types.SimpleNamespace(data=data, error=None)

        if self._mode in ("insert", "upsert"):
            payload = self._payload
            items = payload if isinstance(payload, list) else [payload]
            written = []
            for item in items:
                written.append(self.db.write(self.table_name, dict(item), self._mode, self._conflict))
            return types.SimpleNamespace(data=written, error=None)

        if self._mode == "delete":
            keep = [r for r in self.db.tables[self.table_name] if r not in self.rows]
            self.db.tables[self.table_name] = keep
            return types.SimpleNamespace(data=self.rows, error=None)

        raise AssertionError(self._mode)

    def _expand(self, rows):
        """Emulate the nested PostgREST select used for questions."""
        if self.table_name != "questions":
            return rows
        out = []
        for row in rows:
            options = [
                {
                    **opt,
                    "option_missing_prerequisites": [
                        {"missing_skill_id": m["missing_skill_id"]}
                        for m in self.db.tables["option_missing_prerequisites"]
                        if m["option_id"] == opt["id"]
                    ],
                }
                for opt in self.db.tables["question_options"]
                if opt["question_id"] == row["id"]
            ]
            out.append({**row, "question_options": options})
        return out


class FakeSupabase:
    PKS = {
        "users": ("user_id",),
        "skills": ("skill_id",),
        "user_skill": ("user_id", "skill_id"),
        "questions": ("id",),
        "question_options": ("id",),
        "option_missing_prerequisites": ("option_id", "missing_skill_id"),
        "ontology_topics": ("topic_code",),
    }

    def __init__(self):
        self.tables = {name: [] for name in self.PKS}
        self._seq = {"questions": 0, "question_options": 0}

    def table(self, name):
        self.tables.setdefault(name, [])
        return FakeQuery(self, name, self.tables[name])

    def write(self, table, row, mode, conflict):
        if table in self._seq and "id" not in row:
            self._seq[table] += 1
            row["id"] = self._seq[table]
        keys = self.PKS.get(table, ())
        if keys and all(k in row for k in keys):
            for existing in self.tables[table]:
                if all(existing.get(k) == row[k] for k in keys):
                    if mode == "upsert":
                        existing.update(row)
                        return existing
                    raise RuntimeError(f"duplicate key on {table}")
        self.tables[table].append(row)
        return row


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------
def seed(db, tree_dir: Path, section, topic_skills, skill_descriptions, skill_edges):
    for code in topic_skills:
        db.tables["ontology_topics"].append({"topic_code": code, "topic_label": code})
    for sid, desc in skill_descriptions.items():
        db.tables["skills"].append({"skill_id": sid, "skill_description": desc or sid})

    parents = {}
    for edge in skill_edges:
        parents.setdefault(edge["target"], []).append(edge["source"])

    codes = [t["skill_topic_code"] for t in section["topics"]]
    made = 0
    for code in codes:
        for sid in topic_skills[code]:
            for bloom in BLOOMS:
                q = db.write(
                    "questions",
                    {
                        "skill_id": sid,
                        "bloom_level": bloom,
                        "topic": code,
                        "question_stem": f"[{sid}/{bloom}] synthetic stem",
                    },
                    "insert",
                    None,
                )
                for i, label in enumerate("ABCD"):
                    opt = db.write(
                        "question_options",
                        {
                            "question_id": q["id"],
                            "option_label": label,
                            "option_text": f"option {label}",
                            "is_correct": i == 0,
                            "explanation": "because",
                        },
                        "insert",
                        None,
                    )
                    # Wrong options blame the skill's first prerequisite, which is
                    # the evidence topic-practice spillover reads.
                    if i != 0 and parents.get(sid):
                        db.tables["option_missing_prerequisites"].append(
                            {"option_id": opt["id"], "missing_skill_id": parents[sid][0]}
                        )
                made += 1
    return made


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
PASS, FAIL = [], []


def check(label, condition, detail=""):
    (PASS if condition else FAIL).append(label)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  -- {detail}" if detail else ""))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    db = FakeSupabase()
    import supabase as _supabase

    _supabase.create_client = lambda *a, **k: db

    import server

    tree = HERE / "tree_data"
    topic_skills = json.loads((tree / "topic_skills.json").read_text(encoding="utf-8"))
    skill_desc = json.loads((tree / "skill_descriptions.json").read_text(encoding="utf-8"))
    skill_edges = json.loads((tree / "skill_edges.json").read_text(encoding="utf-8"))

    print("=== 1. ontology ===")
    check("SkillTree built", len(server.SKILL_TREE) > 0, f"{len(server.SKILL_TREE)} skills")
    catalog_codes = {
        t["skill_topic_code"]
        for c in server.PLATFORM_CATALOG["courses"]
        for s in c["sections"]
        for t in s["topics"]
    }
    check("catalog topics all exist in ontology", catalog_codes <= set(topic_skills),
          f"{len(catalog_codes)} topics")
    check("no BCS topic codes remain",
          not ({"RNUM", "HCF", "LCM", "PCT", "SCP", "RAP", "PAL"} & set(topic_skills)))

    course = server.PLATFORM_CATALOG["courses"][0]
    section = course["sections"][0]
    print(f"\n  using section: {course['title']} / {section['title']}")

    made = seed(db, tree, section, topic_skills, skill_desc, skill_edges)
    server.EXISTING_SKILL_IDS = {r["skill_id"] for r in db.tables["skills"]}
    print(f"  seeded {made} questions, {len(db.tables['skills'])} skills")

    print("\n=== 2. topic-coded question search (regression guard) ===")
    code = section["topics"][0]["skill_topic_code"]
    sid = topic_skills[code][0]
    by_code = server._query_questions(skill_ids=[sid], bloom_levels=["Apply"], topic=code)
    check("Tier-1 topic filter matches by topic CODE", len(by_code) > 0, f"{len(by_code)} rows")
    label = section["topics"][0]["title"]
    by_label = server._query_questions(skill_ids=[sid], bloom_levels=["Apply"], topic=label)
    check("filtering by display label matches nothing (the old bug)", len(by_label) == 0)

    print("\n=== 3. diagnostic flow ===")
    user_id = "11111111-1111-1111-1111-111111111111"
    db.tables["users"].append({"user_id": user_id, "user_name": "smoke"})

    start = server.start_diagnostic(
        server.DiagnosticStartRequest(user_id=user_id, section_id=section["id"])
    )
    sess = start["session_id"]
    total = start["total_questions"]
    check("diagnostic started", start["question"] is not None, f"length {total}")
    check("question carries subject", bool(start["question"].get("subject")),
          start["question"].get("subject", ""))
    check("topic shown as display label, not code",
          start["question"]["topic"] != start["question"]["topic_code"],
          f"{start['question']['topic_code']} -> {start['question']['topic']}")

    answered, guard = 0, 0
    while guard < total * 3:
        guard += 1
        status = server.get_diagnostic_status(sess)
        if status["completed"]:
            break
        nxt = server.get_next_diagnostic_question(sess)
        if nxt.get("completed") or not nxt.get("question"):
            break
        correct = next(o["label"] for o in nxt["question"]["options"] if o["label"] == "A")
        res = server.submit_diagnostic_answer(
            sess, server.DiagnosticAnswerRequest(selected_option_label=correct)
        )
        answered += 1
        if res["completed"]:
            break

    check("diagnostic answered every question", answered == total, f"{answered}/{total}")
    state = server.get_section_state(user_id, section["id"])
    check("mastery unlocked after diagnostic", not state["mastery_locked"])
    check("section state reports subject", state.get("subject") == course["subject"],
          str(state.get("subject")))

    rows = [r for r in db.tables["user_skill"] if r["user_id"] == user_id]
    moved = [r for r in rows if r["mastery_level"] > 0]
    check("mastery written to user_skill", len(moved) > 0, f"{len(moved)} skills > 0")

    print("\n=== 4. ancestor pull-up ===")
    section_skills = server._section_skill_ids(section)
    mastery = server._mastery_map_for_user(user_id, section_skills)
    violations = []
    for edge in skill_edges:
        p, c = edge["source"], edge["target"]
        if p in mastery and c in mastery and mastery[c] > 0:
            if mastery[p] + 1e-6 < mastery[c]:
                violations.append((p, c))
    check("no ancestor sits below its descendant", not violations,
          f"{len(violations)} violations" if violations else "invariant held")

    print("\n=== 5. mastery view ===")
    view = server.get_section_mastery(user_id, section["id"])
    check("mastery view unlocked", not view["locked"])
    check("map has nodes and edges", len(view["map"]["nodes"]) > 0 and len(view["map"]["edges"]) > 0,
          f"{len(view['map']['nodes'])} nodes / {len(view['map']['edges'])} edges")
    check("table rows carry subject", all("subject" in r for r in view["table"]))

    print("\n=== 6. topic practice + spillover ===")
    tp = server.start_topic_practice(
        server.TopicPracticeStartRequest(
            user_id=user_id, section_id=section["id"], topic_code=code
        )
    )
    if tp.get("question") is None:
        check("topic practice produced a question", tp.get("completed") is True,
              "already mastered — acceptable")
    else:
        tp_sess = tp["session_id"]
        wrong_streak, spill = 0, None
        for _ in range(12):
            nxt = server.get_next_topic_practice_question(tp_sess)
            if not nxt.get("question"):
                break
            res = server.submit_topic_practice_answer(
                tp_sess, server.TopicPracticeAnswerRequest(selected_option_label="B")
            )
            wrong_streak += 1
            if res.get("spillover_activated"):
                spill = res["spillover_activated"]
                break
        check("topic practice served questions", wrong_streak > 0, f"{wrong_streak} answered")
        check("spillover fired on repeated wrong answers", spill is not None,
              str(spill.get("reason")) if spill else "did not trigger")

    print(f"\n=== {len(PASS)} passed, {len(FAIL)} failed ===")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
