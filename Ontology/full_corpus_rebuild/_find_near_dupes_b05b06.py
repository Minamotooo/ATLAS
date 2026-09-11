"""Near-duplicate detector for the ChemBook1 b05/b06 batch.

Same Jaccard-within-topic idea as _find_near_dupes.py, but compares the NEW
candidate skills against three reference sets instead of only against each
other:
  1. the other new candidates (b05 + b06),
  2. the already-consolidated rebuild tuples.json (388 skills),
  3. the legacy Ontology/tuples.json Chemistry skills (117).

It only FLAGS pairs; every flagged pair still needs a human/agent judgement
(see HANDOFF3 section 6 for the decision rules that apply).
"""
import json, collections, re, itertools

CAND_FILES = ['ChemBook1_b05.json', 'ChemBook1_b06.json']

new_skills = []
for f in CAND_FILES:
    d = json.load(open('candidates/' + f, encoding='utf-8'))
    new_skills.extend(d.get('skills', []))

existing = json.load(open('tuples.json', encoding='utf-8'))
legacy = [s for s in json.load(open('../tuples.json', encoding='utf-8'))
          if s.get('subject') == 'Chemistry']

STOP = set('a an the of to for in on with and or is are be from that this which '
           'its it as by at into using use given named recall define identify '
           'recognize'.split())


def tokset(s):
    words = re.findall(r"[a-z0-9]+", s.lower())
    return set(w for w in words if w not in STOP and len(w) > 2)


def flag(pairs, label, a_list, b_list, a_key, b_key, same_list=False):
    by_topic_b = collections.defaultdict(list)
    for s in b_list:
        by_topic_b[s['topicKey']].append(s)
    for sa in a_list:
        ta = tokset(sa['skillFull'])
        if not ta:
            continue
        for sb in by_topic_b.get(sa['topicKey'], []):
            if same_list and sa[a_key] >= sb[b_key]:
                continue
            tb = tokset(sb['skillFull'])
            if not tb:
                continue
            jac = len(ta & tb) / len(ta | tb)
            if jac >= 0.45:
                pairs.append((jac, label, sa['topicKey'],
                              sa[a_key], sa['skillFull'],
                              sb[b_key], sb['skillFull']))


pairs = []
flag(pairs, 'NEW-vs-NEW', new_skills, new_skills, 'tempId', 'tempId', same_list=True)
flag(pairs, 'NEW-vs-REBUILD', new_skills, existing, 'tempId', 'skillId')
flag(pairs, 'NEW-vs-LEGACY', new_skills, legacy, 'tempId', 'skillId')

pairs.sort(reverse=True)
with open('_near_dupes_b05b06_report.txt', 'w', encoding='utf-8') as out:
    out.write(f'{len(pairs)} candidate near-duplicate pairs (jaccard >= 0.45)\n')
    out.write(f'new candidates: {len(new_skills)}  rebuild: {len(existing)}  '
              f'legacy chem: {len(legacy)}\n\n')
    for jac, label, topic, id1, s1, id2, s2 in pairs:
        out.write(f'[{jac:.2f}] {label} / {topic}\n')
        out.write(f'  {id1}: {s1}\n')
        out.write(f'  {id2}: {s2}\n\n')
print(f'{len(pairs)} flagged pairs -> _near_dupes_b05b06_report.txt')
