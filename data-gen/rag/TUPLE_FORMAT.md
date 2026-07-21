# Tuple + prerequisite format (for ontology teammate)

Yes — producing tuples like before is fine. Keep the same shape, and **add `subject`**.

This project targets **BUET / university admission** exams for **Mathematics, Physics, Chemistry** (Bangla stems).

## `tuples.json` — one object per (skill × bloom × topic)

```json
{
  "bloom": "Apply",
  "skillId": "CHEM_KSP1",
  "skillFull": "Calculate ionic product and compare with Ksp to decide precipitation",
  "topicKey": "CHEM_EQ",
  "topicLabel": "Chemical Equilibrium — Solubility Product",
  "subject": "Chemistry"
}
```

### Required fields

| Field | Type | Notes |
|--------|------|--------|
| `bloom` | string | Exactly one of: `Remember`, `Understand`, `Apply`, `Analyze`, `Evaluate`, `Create` |
| `skillId` | string | Stable ID (e.g. `MATH_ALG2`, `PHY_EM1`, `CHEM_KSP1`) |
| `skillFull` | string | Full English skill description (used in prompts + retrieval query) |
| `topicKey` | string | Short topic code for ontology grouping |
| `topicLabel` | string | Human-readable topic name |
| `subject` | string | **Required for multi-subject RAG.** One of: `Mathematics`, `Physics`, `Chemistry` |

Generate one tuple for **each** Bloom level × skill × topic (same pattern as the old BCS math ontology).

## `prereqs.json` — ancestors per skill (unchanged idea)

```json
{
  "CHEM_KSP1": [
    { "id": "CHEM_EQ1", "full": "Write equilibrium expressions", "depth": 0 },
    { "id": "CHEM_CONC1", "full": "Compute molar concentration", "depth": 1 }
  ],
  "MATH_ALG2": []
}
```

Rules:
- Keys = `skillId`
- Values = list of ancestor skills only (not the skill itself)
- Empty list `[]` for root skills is fine
- `id` / `full` must match ontology nodes exactly (generator uses these for `missing_prerequisites`)

## Output questions (what RAG generates)

Same MCQ schema as before, plus `subject`:

```json
{
  "bloom_level": "Apply",
  "skill_id": "CHEM_KSP1",
  "skill_description": "...",
  "subject": "Chemistry",
  "topic": "Chemical Equilibrium — Solubility Product",
  "question_stem": "...",
  "options": [ ... ],
  "source_refs": [ ... ]
}
```

## Knowledge base (`documents/*.txt`)

Final format example: `documents/1-20.txt`.

- Extension: `.txt` (JSON content inside)
- One file may contain **several JSON arrays** back-to-back (batched by pages)
- Each object:

```json
{
  "question_number": "05",
  "question_type": "MCQ",
  "subject": "Chemistry",
  "source_tag": "[KUET'16-17]",
  "question_text": "...",
  "options": { "a": "...", "b": "...", "c": "...", "d": "..." },
  "answer": "c",
  "solution": null,
  "page_number": 3
}
```

For Written items, use `"options": {}` (empty object) and usually `"answer": null` with a filled `"solution"`.

`subject` should be `Mathematics` | `Physics` | `Chemistry` (Bangla aliases also OK).
Legacy single-array `*.json` files are still ingested if present.
