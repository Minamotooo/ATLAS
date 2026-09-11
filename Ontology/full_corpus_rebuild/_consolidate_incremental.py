"""Incremental consolidation of a new candidate batch into the rebuild output.

Differs from _consolidate_chembook1.py in one important way: that script rebuilt
tuples.json from scratch out of the candidate files, which would re-mint every
skillId. This one MERGES a new batch into the existing consolidated
tuples.json/prereqs.json, so the ids already assigned to the 388 ChemBook1
b01-b04 skills (and referenced by prereqs.json) stay stable.

Inputs per candidate file:
  skills               - new skills to mint (tempId, bloom, skillFull, topicKey, ...)
  reusedExistingSkills - {existingSkillId, sourceItemIds}: this batch's records
                         also exercise an already-consolidated skill. If the id
                         exists only in the LEGACY ontology, it is adopted into
                         the rebuild (id + legacy description) rather than a
                         near-duplicate being minted.
  reusedBatchSkills    - {batchTempId, sourceItemIds}: a later chunk reusing a
                         skill minted by an earlier chunk in this same batch.
  legacyIdReuse        - {tempId: legacySkillId}: a newly-extracted skill that is
                         genuinely the same concept as a legacy one, so it takes
                         the legacy id instead of a fresh number.
  prereqs              - {fromTempId, toTempId? | toSkillId?, toDescription,
                          toTopicKeyGuess?}. Prefer naming the target explicitly
                          with toTempId (a skill minted in this batch) or
                          toSkillId (an already-consolidated skill); the fuzzy
                          description match is only a fallback.

Run from Ontology/full_corpus_rebuild/.
"""
import json, re, collections, datetime

CAND_FILES = ['ChemBook2_b09.json']

# Previously-unresolved prereq mentions (from the b01-b04 batch) that this
# batch's review resolved by hand. The fuzzy matcher scored these at 0.50-0.58,
# below the 0.60 auto-accept bar, but each was read and confirmed. Keyed by
# (skillId that has the dangling prereq, start of the mention's description).
# CHE_BONDING44 is a deliberate override: its best fuzzy hit was the
# electronegativity trend, but the mention asks for the ionic-radius trend,
# which CHEM_PERIODIC6 (general "trend of a given atomic or ionic property")
# actually covers.
MANUAL_RESOLUTIONS = [
    ('CHE_BONDING47',      'Draw a Lewis (electron-dot) structure',   'CHE_BONDING24'),
    ('CHE_BONDING46',      'Draw a Lewis (electron-dot) structure',   'CHE_BONDING24'),
    ('CHE_STOICHIOMETRY2', 'Convert a given mass of a substance',     'CHE_STOICHIOMETRY12'),
    ('CHE_BONDING44',      'Recall the periodic trend in ionic radius', 'CHEM_PERIODIC6'),
]

existing = json.load(open('tuples.json', encoding='utf-8'))
existing_prereqs = json.load(open('prereqs.json', encoding='utf-8'))
existing_unresolved = json.load(open('unresolved_prereqs.json', encoding='utf-8'))
legacy = json.load(open('../tuples.json', encoding='utf-8'))

existing_by_id = {s['skillId']: s for s in existing}
legacy_by_id = {s['skillId']: s for s in legacy}

# ---------------------------------------------------------------- load batch
batch_skills, reused_existing, reused_batch, prereqs_raw = [], [], [], []
legacy_id_reuse, new_topics_raw, skipped, source_issues = {}, [], [], []
for f in CAND_FILES:
    d = json.load(open('candidates/' + f, encoding='utf-8'))
    batch_skills.extend(d.get('skills', []))
    reused_existing.extend(d.get('reusedExistingSkills', []))
    reused_batch.extend(d.get('reusedBatchSkills', []))
    prereqs_raw.extend(d.get('prereqs', []))
    legacy_id_reuse.update(d.get('legacyIdReuse', {}))
    new_topics_raw.extend(d.get('newTopicsProposed', []))
    skipped.extend(d.get('skippedItems', []))
    source_issues.extend(d.get('sourceIssues', []))

by_temp = {s['tempId']: s for s in batch_skills}

# ------------------------------------------------- id allocation (collision-safe)
# Numbers already taken per topic prefix, across BOTH the legacy ontology and the
# consolidated rebuild, so a newly minted id can never collide with either.
used_by_prefix = collections.defaultdict(set)
for s in list(legacy) + list(existing):
    m = re.match(r'^([A-Za-z_]+?)(\d+)$', s['skillId'])
    if m:
        used_by_prefix[m.group(1)].add(int(m.group(2)))


def mint(prefix):
    n = max(used_by_prefix[prefix]) + 1 if used_by_prefix[prefix] else 0
    while n in used_by_prefix[prefix]:
        n += 1
    used_by_prefix[prefix].add(n)
    return f'{prefix}{n}'


# ------------------------------------- adopt legacy-only ids that were reused
adopted = []
for r in reused_existing:
    sid = r['existingSkillId']
    if sid in existing_by_id:
        continue
    if sid not in legacy_by_id:
        raise SystemExit(f'reused id {sid} is in neither the rebuild nor the legacy ontology')
    ls = legacy_by_id[sid]
    entry = {
        'bloom': ls['bloom'], 'skillId': sid, 'skillFull': ls['skillFull'],
        'topicKey': ls['topicKey'], 'topicLabel': ls['topicLabel'],
        'subject': ls['subject'],
    }
    existing.append(entry)
    existing_by_id[sid] = entry
    adopted.append(sid)

# ------------------------------------------------------------- mint new skills
tempid_to_final = {}
minted = []
for s in batch_skills:
    t = s['tempId']
    if t in legacy_id_reuse:
        final_id = legacy_id_reuse[t]
        if final_id in existing_by_id:
            raise SystemExit(f'{t} wants legacy id {final_id}, already used in the rebuild')
        if final_id not in legacy_by_id:
            raise SystemExit(f'{t} wants legacy id {final_id}, which does not exist')
    else:
        final_id = mint(s['topicKey'])
    tempid_to_final[t] = final_id
    entry = {
        'bloom': s['bloom'], 'skillId': final_id, 'skillFull': s['skillFull'],
        'topicKey': s['topicKey'], 'topicLabel': s['topicLabel'],
        'subject': s['subject'],
    }
    existing.append(entry)
    existing_by_id[final_id] = entry
    minted.append(final_id)

# reusedBatchSkills just point at an already-minted tempId; nothing new to create
for r in reused_batch:
    if r['batchTempId'] not in tempid_to_final:
        raise SystemExit(f"reusedBatchSkills references unknown tempId {r['batchTempId']}")

# ------------------------------------------------------------------- prereqs
STOP = set('a an the of to for in on with and or is are be from that this which its '
           'it as by at into using use given named recall define identify recognize'.split())


def tokset(s):
    return set(w for w in re.findall(r"[a-z0-9]+", s.lower())
               if w not in STOP and len(w) > 2)


all_tok = {s['skillId']: tokset(s['skillFull']) for s in existing}

resolved = collections.defaultdict(list, {k: list(v) for k, v in existing_prereqs.items()})
seen_edges = {(frm, e['id']) for frm, edges in existing_prereqs.items() for e in edges}
unresolved = collections.defaultdict(list, {k: list(v) for k, v in existing_unresolved.items()})

n_new_edges, n_new_unresolved = 0, 0
for p in prereqs_raw:
    frm = tempid_to_final.get(p['fromTempId'])
    if not frm:
        raise SystemExit(f"prereq from unknown tempId {p['fromTempId']}")
    to = None
    if p.get('toTempId'):
        to = tempid_to_final.get(p['toTempId'])
        if not to:
            raise SystemExit(f"prereq to unknown tempId {p['toTempId']}")
    elif p.get('toSkillId'):
        to = p['toSkillId']
        if to not in existing_by_id:
            raise SystemExit(f"prereq to unknown skillId {to}")
    if not to:
        desc_tok = tokset(p.get('toDescription', ''))
        best, best_score = None, 0.0
        for sid, tok in all_tok.items():
            if sid == frm or not tok or not desc_tok:
                continue
            score = len(tok & desc_tok) / len(tok | desc_tok)
            if score > best_score:
                best, best_score = sid, score
        if best_score >= 0.6:
            to = best
    if to and to != frm and (frm, to) not in seen_edges:
        seen_edges.add((frm, to))
        resolved[frm].append({'id': to, 'full': existing_by_id[to]['skillFull'], 'depth': 0})
        n_new_edges += 1
    elif not to:
        unresolved[frm].append({'description': p.get('toDescription', ''),
                                'topicKeyGuess': p.get('toTopicKeyGuess', '')})
        n_new_unresolved += 1

# ------------------------------ re-check previously-unresolved prereq mentions
# HANDOFF3 section 4: "Re-check these against every new batch's output."
still_unresolved = collections.defaultdict(list)
n_recovered, n_manual = 0, 0
for frm, mentions in unresolved.items():
    for m in mentions:
        desc = m.get('description', '')
        manual = next((to for f, pre, to in MANUAL_RESOLUTIONS
                       if f == frm and desc.startswith(pre)), None)
        if manual:
            if manual not in existing_by_id:
                raise SystemExit(f'manual resolution target {manual} does not exist')
            if (frm, manual) not in seen_edges:
                seen_edges.add((frm, manual))
                resolved[frm].append({'id': manual,
                                      'full': existing_by_id[manual]['skillFull'],
                                      'depth': 0})
            n_manual += 1
            continue
        desc_tok = tokset(desc)
        best, best_score = None, 0.0
        for sid, tok in all_tok.items():
            if sid == frm or not tok or not desc_tok:
                continue
            score = len(tok & desc_tok) / len(tok | desc_tok)
            if score > best_score:
                best, best_score = sid, score
        if best_score >= 0.6 and best != frm and (frm, best) not in seen_edges:
            seen_edges.add((frm, best))
            resolved[frm].append({'id': best, 'full': existing_by_id[best]['skillFull'],
                                  'depth': 0})
            n_recovered += 1
        else:
            still_unresolved[frm].append(m)

# ---------------------------------------------------------------------- write
existing.sort(key=lambda s: (s['topicKey'], s['skillId']))
json.dump(existing, open('tuples.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
json.dump({k: v for k, v in resolved.items() if v},
          open('prereqs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump({k: v for k, v in still_unresolved.items() if v},
          open('unresolved_prereqs.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
if source_issues:
    # accumulate across batches rather than overwriting the previous batch's list
    try:
        prior = json.load(open('source_issues.json', encoding='utf-8'))
    except FileNotFoundError:
        prior = []
    seen_issues = {(i['itemId'], i['note'][:60]) for i in prior}
    for it in source_issues:
        if (it['itemId'], it['note'][:60]) not in seen_issues:
            prior.append(it)
    json.dump(prior, open('source_issues.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

print(f'batch                     : {", ".join(CAND_FILES)}')
print(f'new skills minted         : {len(minted)}')
print(f'legacy ids adopted (reuse): {len(adopted)} {adopted}')
print(f'legacy ids taken by new   : {len(legacy_id_reuse)} {sorted(legacy_id_reuse.values())}')
print(f'existing skills reused    : {len(reused_existing)} refs, '
      f'{len(reused_batch)} intra-batch refs')
print(f'total skills now          : {len(existing)}')
print(f'new prereq edges          : {n_new_edges}')
print(f'prereq edges total        : {sum(len(v) for v in resolved.values())}')
print(f'unresolved recovered      : {n_recovered} fuzzy + {n_manual} hand-reviewed')
print(f'unresolved remaining      : {sum(len(v) for v in still_unresolved.values())}')
print(f'topics touched            : {len({s["topicKey"] for s in existing})}')
print(f'source issues logged      : {len(source_issues)}')
print(f'run at                    : {datetime.datetime.now().isoformat(timespec="seconds")}')
