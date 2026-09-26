# 01 — Build the topic taxonomy from the HSC/NCTB syllabus

> **What this is.** The prompt that turns the official Bangladesh HSC (NCTB)
> syllabus for Physics, Chemistry and Higher Mathematics into the fixed topic
> vocabulary that every skill in the ontology is filed under.
>
> **Why it exists.** The first ontology invented its own 66 topic codes from
> whatever the source questions happened to cover. That produced a taxonomy no
> teacher recognised and no syllabus backed: Mathematics got 9.4 topics per 100
> skills while Chemistry got 23.1, purely because Physics had been sampled with a
> dedicated 1,379-question run and Maths had only appeared inside a 300-question
> mixed paper. Anchoring to the published syllabus removes that arbitrariness —
> the taxonomy is now defensible to an examiner, not just internally consistent.
>
> **When it runs.** Once, before extraction. Its output is a generator script,
> not a hand-edited file, so the taxonomy can be regenerated and diffed.
>
> **What it produced.** `Backend/tree_data/build_syllabus_config.py` →
> `Backend/tree_data/ontology_config.json`: **51 chapters, 183 topics**
> (Physics 21 ch / 72 topics, Chemistry 10 / 59, Mathematics 20 / 52).
>
> **Status.** Reconstructed. The original run was conversational — the syllabus
> was pasted in and the mapping worked out in dialogue. This file is that
> exchange written up as a reusable prompt, and it reflects the decisions the
> final taxonomy actually embodies.

---

## System framing

You are a curriculum architect working on an adaptive-learning platform for
Bangladeshi university admission tests (BUET, KUET, RUET, CUET, SUST).

Your job is to convert an official syllabus into a **machine-readable topic
taxonomy** that a skill ontology will be filed against. You are not writing
learning objectives and you are not extracting skills — you are defining the
folder structure those skills will later be sorted into.

The taxonomy is the thing everything else inherits. Get it wrong and every
downstream decision inherits the error, so bias toward matching the published
syllabus exactly over inventing a structure you find tidier.

---

## Instruction

I will give you the full HSC/NCTB syllabus for three subjects: Physics (1st and
2nd Paper), Chemistry (1st and 2nd Paper), and Higher Mathematics (1st and 2nd
Paper).

Convert it into a three-level taxonomy and emit it as a **Python generator
script**, not as JSON.

### The three levels

| Level | Maps to | Example |
|---|---|---|
| **Course** | one subject | Physics |
| **Section** | one syllabus **chapter** | `phy2_ch08_modern` — "Introduction to Modern Physics" |
| **Topic** | one sub-topic inside that chapter | `PHY2_RELATIVITY` — "Special Relativity" |

### Rules

1. **Chapters come from the syllabus verbatim.** Do not merge two chapters
   because they feel related, and do not split one because it looks large. The
   chapter list is given, not decided.

2. **Sub-topics are yours to derive, and you should invent them where the
   syllabus is coarse.** A syllabus chapter often names a broad area with no
   internal divisions. Break it into 2–8 sub-topics that a teacher would
   recognise as the natural teaching units of that chapter. This is the one
   place you are expected to add structure rather than transcribe it.

3. **Size each topic for diagnosis, not for tidiness.** The platform tests one
   skill at a time and must be able to tell a student *which* part of a chapter
   they are weak in. A topic that will end up holding 40+ skills cannot do that;
   one holding 2 cannot localise anything either. Aim for sub-topics that will
   attract roughly 5–25 skills each.

4. **Topic codes are stable identifiers.** `SUBJECT+PAPER_CONCEPT`, uppercase,
   e.g. `PHY2_PHOTOELECTRIC`, `CHE1_REDOX`, `MAT1_DETERMINANT`. These get
   embedded in data and must never be renamed casually once skills reference
   them.

5. **Every topic carries an English label and the Bangla syllabus wording.** The
   platform is bilingual; the Bangla is the syllabus's own phrasing, not a
   translation you produce.

6. **Where a topic's placement is non-obvious, follow the NCTB book, not
   physics-textbook logic.** Example: gas laws sit in *Chemistry 2nd Paper
   Chapter 1, Environmental Chemistry*, because that is where the NCTB book
   teaches them — as the groundwork for studying the atmosphere — even though
   every other curriculum treats them as physical chemistry. Put a comment in
   the script wherever you make a call like this, explaining why, so the next
   reader does not "fix" it.

### Also produce, in the same script

- **`ALIASES`** — a map from the *previous* taxonomy's topic codes to the new
  syllabus codes, so an existing ontology can be re-filed without re-extracting.
  ⚠️ **Record the limitation explicitly:** this is a *code-to-code* map, so one
  old code collapses onto exactly one new code. Where the syllabus splits an old
  bucket into several topics, the alias sends everything to one of them and
  leaves the siblings empty. That is not a fixable property of an alias map — it
  needs a per-skill retag afterwards (see prompt `04`). Say so in a comment.

- **`SPLIT_CANDIDATES`** — the old codes you know are being over-collapsed, each
  with a one-line note naming what will end up mis-filed. This is the worklist
  for the retag pass.

### Output format

A single Python file that, when run, writes `ontology_config.json`. Structure it
as plain literal lists so it reads as data:

```python
PHYSICS = [
    ("phy2_ch08_modern", "Introduction to Modern Physics", "আধুনিক পদার্থবিজ্ঞানের সূচনা", [
        ("PHY2_RELATIVITY",   "Special Relativity"),
        ("PHY2_PHOTOELECTRIC","Photoelectric Effect and Photons"),
        ("PHY2_XRAY",         "X-rays"),
        ("PHY2_MATTER_WAVES", "Matter Waves and the Uncertainty Principle"),
    ]),
    ...
]
```

The script is the source of truth. `ontology_config.json` is generated output
and must never be hand-edited — put that warning in the file's header, because
someone will try.

---

## Verification checklist

- [ ] Every syllabus chapter appears exactly once, with its syllabus number.
- [ ] Every chapter has at least two sub-topics.
- [ ] No topic code is used twice across subjects.
- [ ] Every topic has both an English and a Bangla label.
- [ ] Every non-obvious placement carries a comment explaining it.
- [ ] `SPLIT_CANDIDATES` names every old code the aliases over-collapse.
- [ ] Re-running the script produces a byte-identical file.
