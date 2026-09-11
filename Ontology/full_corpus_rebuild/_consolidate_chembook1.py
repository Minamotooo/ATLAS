import json, re, collections

BASE = '.'
CAND = BASE + '/candidates'
FILES = ['ChemBook1_b01.json', 'ChemBook1_b02.json', 'ChemBook1_b03.json', 'ChemBook1_b04.json']

skills = []
prereqs_raw = []
new_topics_raw = []
skipped = []
for f in FILES:
    d = json.load(open(CAND + '/' + f, encoding='utf-8'))
    skills.extend(d.get('skills', []))
    prereqs_raw.extend(d.get('prereqs', []))
    new_topics_raw.extend(d.get('newTopicsProposed', []))
    skipped.extend(d.get('skippedItems', []))

by_temp = {s['tempId']: s for s in skills}

# -----------------------------------------------------------------------
# Manually-reviewed merge groups (near-duplicate detection + manual read),
# and legacy-skillId reuse decisions (checked against Ontology/tuples.json).
# Each group: canonical tempId to keep (its wording wins) -> list of
# tempIds that merge into it (their sourceItemIds get unioned in).
# reuse_legacy: tempId (post-merge canonical) -> legacy skillId to reuse.
# -----------------------------------------------------------------------
MERGE_GROUPS = [
    ['ChemBook1_b03_s12', 'ChemBook1_b02_s10', 'ChemBook1_b04_s26'],
    ['ChemBook1_b02_s69', 'ChemBook1_b03_s5'],
    ['ChemBook1_b03_s1', 'ChemBook1_b02_s70'],
    ['ChemBook1_b03_s17', 'ChemBook1_b02_s11'],
    ['ChemBook1_b01_s46', 'ChemBook1_b02_s15'],
    ['ChemBook1_b03_s27', 'ChemBook1_b02_s12'],
    ['ChemBook1_b02_s4', 'ChemBook1_b03_s49'],
    ['ChemBook1_b04_s121', 'ChemBook1_b01_s29'],
    ['ChemBook1_b02_s40', 'ChemBook1_b03_s16'],
    ['ChemBook1_b04_s120', 'ChemBook1_b01_s26'],
    ['ChemBook1_b03_s33', 'ChemBook1_b02_s73'],
    ['ChemBook1_b03_s32', 'ChemBook1_b02_s72'],
    ['ChemBook1_b03_s53', 'ChemBook1_b01_s39'],
]

REUSE_LEGACY = {
    'ChemBook1_b03_s12': 'CHEM_AT1',
    'ChemBook1_b03_s17': 'CHE_ATOMIC2',
    'ChemBook1_b03_s53': 'CHEM_REDOX2',
    'ChemBook1_b01_s66': 'CHEM_ATOMIC5',
}

# tempId -> canonical tempId (the one whose wording survives)
merge_of = {}
for group in MERGE_GROUPS:
    canon = group[0]
    for t in group:
        merge_of[t] = canon

# Build final skill list: one entry per canonical tempId (survivors), with
# sourceItemIds unioned across everything that merged into it.
canon_ids = []
seen_canon = set()
for s in skills:
    t = s['tempId']
    canon = merge_of.get(t, t)
    if canon not in seen_canon:
        seen_canon.add(canon)
        canon_ids.append(canon)

merged_source_items = collections.defaultdict(list)
for s in skills:
    canon = merge_of.get(s['tempId'], s['tempId'])
    merged_source_items[canon].extend(s.get('sourceItemIds', []))

# Legacy ids already used per topicKey prefix (to avoid collisions when
# minting new ones). Legacy tuples.json is the project's existing ontology.
legacy = json.load(open('../tuples.json', encoding='utf-8'))
legacy_ids_by_prefix = collections.defaultdict(set)
for s in legacy:
    m = re.match(r'^([A-Za-z_]+?)(\d+)$', s['skillId'])
    if m:
        legacy_ids_by_prefix[m.group(1)].add(int(m.group(2)))

next_num = collections.defaultdict(int)
for prefix, nums in legacy_ids_by_prefix.items():
    next_num[prefix] = max(nums) + 1

tempid_to_final = {}
final_skills = []
for canon in canon_ids:
    s = dict(by_temp[canon])
    tempid_to_final[canon] = None  # filled below
    if canon in REUSE_LEGACY:
        final_id = REUSE_LEGACY[canon]
    else:
        prefix = s['topicKey']
        n = next_num[prefix]
        while n in legacy_ids_by_prefix.get(prefix, set()):
            n += 1
        final_id = f'{prefix}{n}'
        next_num[prefix] = n + 1
        legacy_ids_by_prefix.setdefault(prefix, set()).add(n)
    tempid_to_final[canon] = final_id
    final_skills.append({
        'bloom': s['bloom'],
        'skillId': final_id,
        'skillFull': s['skillFull'],
        'topicKey': s['topicKey'],
        'topicLabel': s['topicLabel'],
        'subject': s['subject'],
    })

# every merged-away tempId also needs to resolve to the same final id
for t, canon in merge_of.items():
    tempid_to_final[t] = tempid_to_final[canon]

STOP = set('a an the of to for in on with and or is are be from that this which its it as by at into using use given named recall define identify recognize'.split())
def tokset(s):
    return set(w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2)

final_tok = {fs['skillId']: tokset(fs['skillFull']) for fs in final_skills}
final_by_id = {fs['skillId']: fs for fs in final_skills}

resolved_prereqs = collections.defaultdict(list)
unresolved = collections.defaultdict(list)
seen_edges = set()

for p in prereqs_raw:
    from_final = tempid_to_final.get(p['fromTempId'])
    if not from_final:
        continue  # fromTempId not in our skill set (shouldn't happen)
    to_final = None
    if p.get('toTempId'):
        to_final = tempid_to_final.get(p['toTempId'])
    if not to_final:
        # fuzzy match toDescription against final skill descriptions
        desc_tok = tokset(p.get('toDescription', ''))
        best, best_score = None, 0.0
        for sid, tok in final_tok.items():
            if sid == from_final or not tok or not desc_tok:
                continue
            inter = len(tok & desc_tok)
            union = len(tok | desc_tok)
            score = inter / union if union else 0
            if score > best_score:
                best, best_score = sid, score
        if best_score >= 0.6:
            to_final = best
    if to_final and to_final != from_final:
        edge = (from_final, to_final)
        if edge not in seen_edges:
            seen_edges.add(edge)
            resolved_prereqs[from_final].append({
                'id': to_final, 'full': final_by_id[to_final]['skillFull'], 'depth': 0,
            })
    elif not to_final:
        unresolved[from_final].append({
            'description': p.get('toDescription', ''),
            'topicKeyGuess': p.get('toTopicKeyGuess', ''),
        })

# dedupe new topic proposals
seen_topics = set()
new_topics = []
for t in new_topics_raw:
    key = t.get('topicKey')
    if key and key not in seen_topics:
        seen_topics.add(key)
        new_topics.append(t)

json.dump(final_skills, open(BASE + '/tuples.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(dict(resolved_prereqs), open(BASE + '/prereqs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(dict(unresolved), open(BASE + '/unresolved_prereqs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(new_topics, open(BASE + '/new_topics_proposed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(skipped, open(BASE + '/skipped_items.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print('raw candidate skills:', len(skills))
print('final consolidated skills:', len(final_skills))
print('legacy ids reused:', len(REUSE_LEGACY))
print('resolved prereq edges:', sum(len(v) for v in resolved_prereqs.values()))
print('unresolved prereq mentions:', sum(len(v) for v in unresolved.values()))
print('new topics proposed:', len(new_topics))
print('skipped items:', len(skipped))
