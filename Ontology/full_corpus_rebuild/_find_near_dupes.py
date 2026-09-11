import json, collections, re, itertools

files = ['ChemBook1_b01.json','ChemBook1_b02.json','ChemBook1_b03.json','ChemBook1_b04.json']
all_skills = []
for f in files:
    d = json.load(open('candidates/' + f, encoding='utf-8'))
    all_skills.extend(d.get('skills', []))

STOP = set('a an the of to for in on with and or is are be from that this which its it as by at into using use given named recall define identify recognize'.split())

def tokset(s):
    words = re.findall(r"[a-z0-9]+", s.lower())
    return set(w for w in words if w not in STOP and len(w) > 2)

by_topic = collections.defaultdict(list)
for s in all_skills:
    by_topic[s['topicKey']].append(s)

pairs = []
for topic, skills in by_topic.items():
    toks = [tokset(s['skillFull']) for s in skills]
    for i, j in itertools.combinations(range(len(skills)), 2):
        a, b = toks[i], toks[j]
        if not a or not b:
            continue
        inter = len(a & b)
        union = len(a | b)
        jac = inter / union if union else 0
        if jac >= 0.45:
            pairs.append((jac, topic, skills[i]['tempId'], skills[i]['skillFull'], skills[j]['tempId'], skills[j]['skillFull']))

pairs.sort(reverse=True)
with open('_near_dupes_report.txt', 'w', encoding='utf-8') as out:
    out.write(f'{len(pairs)} candidate near-duplicate pairs (jaccard >= 0.45)\n\n')
    for jac, topic, id1, s1, id2, s2 in pairs:
        out.write(f'[{jac:.2f}] {topic}\n')
        out.write(f'  {id1}: {s1}\n')
        out.write(f'  {id2}: {s2}\n\n')
print('done')
