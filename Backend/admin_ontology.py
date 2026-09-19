"""
admin_ontology.py
------------------
Admin-only API for browsing and editing the full-corpus ontology rebuild
(Ontology/full_corpus_rebuild/{tuples.json, prereqs.json}).

This is deliberately isolated from server.py's runtime skill tree
(Backend/tree_data/, SKILL_TREE): it never reads from or writes to the
legacy catalog the live student app serves. Editing here has no effect on
what students see until someone deliberately re-runs
Backend/tree_data/build_from_ontology.py against this dataset (see
HANDOFF5.md) — that adoption step stays a separate, conscious action.

Data model (unchanged from the rebuild's existing files):
  tuples.json  - flat list of skills: {bloom, skillId, skillFull, topicKey,
                 topicLabel, subject}
  prereqs.json - {childSkillId: [{id: parentSkillId, full: <cached parent
                 description>, depth: 0}, ...]}. All entries are depth 0
                 (direct edges only). The cached `full` text must track the
                 parent's current skillFull, or _validate_ontology.py's E3
                 check will flag drift.

Topics/subjects are not separate registries: they are denormalized fields
per skill. "Adding" a topic or subject is just using a new string; renaming
one rewrites that string across every skill that carries it.
"""
from __future__ import annotations

import json
import os
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
REBUILD_DIR = BASE_DIR.parent / "Ontology" / "full_corpus_rebuild"
TUPLES_PATH = REBUILD_DIR / "tuples.json"
PREREQS_PATH = REBUILD_DIR / "prereqs.json"


def _admin_usernames() -> Set[str]:
    raw = os.environ.get("ADMIN_USERNAMES", "")
    return {u.strip() for u in raw.split(",") if u.strip()}


def require_admin(x_user_name: Optional[str] = Header(default=None)) -> str:
    if not x_user_name or x_user_name not in _admin_usernames():
        raise HTTPException(status_code=403, detail="Admin access required")
    return x_user_name


def _find_cycle_from(children: Dict[str, Set[str]], start: str) -> bool:
    """True if `start` can reach itself by following `children` (prereq -> dependents)."""
    stack = list(children.get(start, ()))
    seen: Set[str] = set()
    while stack:
        node = stack.pop()
        if node == start:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(children.get(node, ()))
    return False


class SkillCreate(BaseModel):
    skill_id: str = Field(..., min_length=1)
    skill_full: str = Field(..., min_length=1)
    topic_key: str = Field(..., min_length=1)
    topic_label: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    bloom: str = Field(..., min_length=1)
    prerequisite_ids: List[str] = Field(default_factory=list)


class SkillUpdate(BaseModel):
    skill_full: Optional[str] = None
    topic_key: Optional[str] = None
    topic_label: Optional[str] = None
    subject: Optional[str] = None
    bloom: Optional[str] = None


class EdgeMutation(BaseModel):
    from_id: str
    to_id: str


class TopicRename(BaseModel):
    topic_label: Optional[str] = None
    subject: Optional[str] = None


class RebuildOntologyStore:
    """In-memory index over the full-corpus rebuild, backed by tuples.json/prereqs.json."""

    def __init__(self, tuples_path: Path, prereqs_path: Path):
        self._tuples_path = tuples_path
        self._prereqs_path = prereqs_path
        self._lock = threading.Lock()
        self._skills: Dict[str, dict] = {}
        self._prereqs: Dict[str, List[dict]] = {}
        self._reload()

    def _reload(self) -> None:
        tuples = json.loads(self._tuples_path.read_text(encoding="utf-8"))
        self._skills = {t["skillId"]: dict(t) for t in tuples}
        self._prereqs = json.loads(self._prereqs_path.read_text(encoding="utf-8"))

    def _children_map(self) -> Dict[str, Set[str]]:
        children: Dict[str, Set[str]] = defaultdict(set)
        for child, parents in self._prereqs.items():
            for p in parents:
                children[p["id"]].add(child)
        return children

    def _save(self) -> None:
        # tuples.json and prereqs.json were originally written with different
        # indent widths (1 and 2 respectively) by different rebuild scripts.
        # Match each one so a save only diffs the lines that actually changed.
        tuples = list(self._skills.values())
        tmp_t = self._tuples_path.with_suffix(".tmp")
        tmp_t.write_text(json.dumps(tuples, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp_t.replace(self._tuples_path)

        tmp_p = self._prereqs_path.with_suffix(".tmp")
        tmp_p.write_text(json.dumps(self._prereqs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp_p.replace(self._prereqs_path)

    # ---------------------------------------------------------------- reads
    def meta(self) -> dict:
        topics: Dict[str, dict] = {}
        subjects: Dict[str, int] = defaultdict(int)
        for s in self._skills.values():
            subjects[s["subject"]] += 1
            t = topics.setdefault(s["topicKey"], {
                "topic_key": s["topicKey"],
                "topic_label": s["topicLabel"],
                "subject": s["subject"],
                "skill_count": 0,
            })
            t["skill_count"] += 1
        return {
            "total_skills": len(self._skills),
            "total_edges": sum(len(v) for v in self._prereqs.values()),
            "subjects": [{"subject": k, "skill_count": v} for k, v in sorted(subjects.items())],
            "topics": sorted(topics.values(), key=lambda t: (t["subject"], t["topic_key"])),
        }

    def query_graph(
        self,
        subject: Optional[str] = None,
        topics: Optional[Set[str]] = None,
        search: Optional[str] = None,
        bloom: Optional[str] = None,
        include_isolated: bool = True,
    ) -> dict:
        children = self._children_map()
        parents = self._prereqs
        needle = search.lower() if search else None

        def matches(s: dict) -> bool:
            if subject and s["subject"] != subject:
                return False
            if topics and s["topicKey"] not in topics:
                return False
            if bloom and s["bloom"] != bloom:
                return False
            if needle and needle not in s["skillId"].lower() and needle not in s["skillFull"].lower():
                return False
            return True

        core = {sid for sid, s in self._skills.items() if matches(s)}
        if not include_isolated:
            core = {sid for sid in core if children.get(sid) or parents.get(sid)}

        # Drilling into one or more topics also pulls in their immediate
        # cross-topic neighbors (marked external) so the admin can see what
        # those topics connect to without rendering the whole subject at once.
        context: Set[str] = set()
        if topics:
            for sid in core:
                for p in parents.get(sid, ()):
                    pid = p["id"]
                    if pid not in core and self._skills[pid]["topicKey"] not in topics:
                        context.add(pid)
                for cid in children.get(sid, ()):
                    if cid not in core and self._skills[cid]["topicKey"] not in topics:
                        context.add(cid)

        selected = core | context

        nodes = []
        for sid in selected:
            s = self._skills[sid]
            degree = len(children.get(sid, ())) + len(parents.get(sid, ()))
            nodes.append({
                "id": sid,
                "label": s["skillFull"],
                "topic_key": s["topicKey"],
                "topic_label": s["topicLabel"],
                "subject": s["subject"],
                "bloom": s["bloom"],
                "degree": degree,
                "external": sid in context,
                "role": (
                    "isolated" if degree == 0 else
                    "root" if not parents.get(sid) else
                    "leaf" if not children.get(sid) else
                    "intermediate"
                ),
            })

        edges = []
        for child in selected:
            for p in parents.get(child, ()):
                pid = p["id"]
                # Skip context-to-context edges; they're only there for
                # orientation, not to sprout a second graph off to the side.
                if pid in selected and (child in core or pid in core):
                    edges.append({"from": pid, "to": child})

        return {"nodes": nodes, "edges": edges, "count": len(nodes), "core_count": len(core)}

    def topic_graph(self, subject: str) -> dict:
        """Topic-level overview for a subject: one node per topic, edges
        aggregated from skill-level prerequisites that cross topic boundaries.
        This is the default view for a subject so the admin never has to look
        at every skill in it at once."""
        topics: Dict[str, dict] = {}
        for s in self._skills.values():
            if s["subject"] != subject:
                continue
            t = topics.setdefault(s["topicKey"], {
                "topic_key": s["topicKey"],
                "topic_label": s["topicLabel"],
                "skill_count": 0,
            })
            t["skill_count"] += 1

        edge_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        for child_id, plist in self._prereqs.items():
            child = self._skills.get(child_id)
            if not child or child["subject"] != subject:
                continue
            for p in plist:
                parent = self._skills.get(p["id"])
                if not parent or parent["subject"] != subject:
                    continue
                if parent["topicKey"] == child["topicKey"]:
                    continue
                edge_counts[(parent["topicKey"], child["topicKey"])] += 1

        edges = [{"from": a, "to": b, "weight": n} for (a, b), n in edge_counts.items()]
        return {
            "subject": subject,
            "topics": sorted(topics.values(), key=lambda t: -t["skill_count"]),
            "edges": edges,
        }

    # --------------------------------------------------------------- writes
    def add_skill(self, payload: SkillCreate) -> dict:
        with self._lock:
            if payload.skill_id in self._skills:
                raise HTTPException(status_code=409, detail=f"Skill {payload.skill_id} already exists")
            for pid in payload.prerequisite_ids:
                if pid not in self._skills:
                    raise HTTPException(status_code=400, detail=f"Unknown prerequisite {pid}")

            self._skills[payload.skill_id] = {
                "bloom": payload.bloom,
                "skillId": payload.skill_id,
                "skillFull": payload.skill_full,
                "topicKey": payload.topic_key,
                "topicLabel": payload.topic_label,
                "subject": payload.subject,
            }
            if payload.prerequisite_ids:
                self._prereqs[payload.skill_id] = [
                    {"id": pid, "full": self._skills[pid]["skillFull"], "depth": 0}
                    for pid in payload.prerequisite_ids
                ]
            self._save()
            return self._skills[payload.skill_id]

    def update_skill(self, skill_id: str, payload: SkillUpdate) -> dict:
        with self._lock:
            if skill_id not in self._skills:
                raise HTTPException(status_code=404, detail="Skill not found")
            s = self._skills[skill_id]
            data = payload.model_dump(exclude_unset=True)
            description_changed = "skill_full" in data

            if "skill_full" in data:
                s["skillFull"] = data["skill_full"]
            if "topic_key" in data:
                s["topicKey"] = data["topic_key"]
            if "topic_label" in data:
                s["topicLabel"] = data["topic_label"]
            if "subject" in data:
                s["subject"] = data["subject"]
            if "bloom" in data:
                s["bloom"] = data["bloom"]

            if description_changed:
                # E3: keep every cached parent-text reference in sync.
                for plist in self._prereqs.values():
                    for p in plist:
                        if p["id"] == skill_id:
                            p["full"] = s["skillFull"]

            self._save()
            return s

    def delete_skill(self, skill_id: str, force: bool = False) -> None:
        with self._lock:
            if skill_id not in self._skills:
                raise HTTPException(status_code=404, detail="Skill not found")
            children = self._children_map()
            dependents = children.get(skill_id, set())
            if dependents and not force:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{len(dependents)} skill(s) depend on this as a prerequisite; "
                        "pass force=true to remove those edges too"
                    ),
                )
            del self._skills[skill_id]
            self._prereqs.pop(skill_id, None)
            for plist in self._prereqs.values():
                plist[:] = [p for p in plist if p["id"] != skill_id]
            self._save()

    def add_edge(self, from_id: str, to_id: str) -> None:
        with self._lock:
            if from_id not in self._skills or to_id not in self._skills:
                raise HTTPException(status_code=404, detail="Both skills must exist")
            if from_id == to_id:
                raise HTTPException(status_code=400, detail="A skill cannot be its own prerequisite")
            existing = self._prereqs.setdefault(to_id, [])
            if any(p["id"] == from_id for p in existing):
                raise HTTPException(status_code=409, detail="Edge already exists")

            children = self._children_map()
            children[from_id].add(to_id)
            if _find_cycle_from(children, from_id):
                raise HTTPException(status_code=400, detail="This edge would create a cycle")

            existing.append({"id": from_id, "full": self._skills[from_id]["skillFull"], "depth": 0})
            self._save()

    def remove_edge(self, from_id: str, to_id: str) -> None:
        with self._lock:
            plist = self._prereqs.get(to_id, [])
            new_list = [p for p in plist if p["id"] != from_id]
            if len(new_list) == len(plist):
                raise HTTPException(status_code=404, detail="Edge not found")
            if new_list:
                self._prereqs[to_id] = new_list
            else:
                self._prereqs.pop(to_id, None)
            self._save()

    def rename_topic(self, topic_key: str, payload: TopicRename) -> dict:
        with self._lock:
            affected = [s for s in self._skills.values() if s["topicKey"] == topic_key]
            if not affected:
                raise HTTPException(status_code=404, detail="Topic not found")
            for s in affected:
                if payload.topic_label is not None:
                    s["topicLabel"] = payload.topic_label
                if payload.subject is not None:
                    s["subject"] = payload.subject
            self._save()
            return {
                "topic_key": topic_key,
                "topic_label": affected[0]["topicLabel"],
                "subject": affected[0]["subject"],
                "skill_count": len(affected),
            }


store = RebuildOntologyStore(TUPLES_PATH, PREREQS_PATH)

router = APIRouter(prefix="/admin/ontology", tags=["admin-ontology"], dependencies=[Depends(require_admin)])


@router.get("/meta")
def get_meta():
    return store.meta()


@router.get("/topic-graph")
def get_topic_graph(subject: str):
    return store.topic_graph(subject)


@router.get("/graph")
def get_graph(
    subject: Optional[str] = None,
    topics: Optional[str] = None,
    search: Optional[str] = None,
    bloom: Optional[str] = None,
    include_isolated: bool = True,
):
    topic_set = {t.strip() for t in topics.split(",") if t.strip()} if topics else None
    return store.query_graph(subject=subject, topics=topic_set, search=search, bloom=bloom, include_isolated=include_isolated)


@router.post("/skills", status_code=201)
def create_skill(payload: SkillCreate):
    return store.add_skill(payload)


@router.patch("/skills/{skill_id}")
def edit_skill(skill_id: str, payload: SkillUpdate):
    return store.update_skill(skill_id, payload)


@router.delete("/skills/{skill_id}", status_code=204)
def remove_skill(skill_id: str, force: bool = False):
    store.delete_skill(skill_id, force=force)


@router.post("/edges", status_code=201)
def create_edge(payload: EdgeMutation):
    store.add_edge(payload.from_id, payload.to_id)
    return {"from": payload.from_id, "to": payload.to_id}


@router.delete("/edges", status_code=204)
def remove_edge_endpoint(payload: EdgeMutation):
    store.remove_edge(payload.from_id, payload.to_id)


@router.patch("/topics/{topic_key}")
def edit_topic(topic_key: str, payload: TopicRename):
    return store.rename_topic(topic_key, payload)
