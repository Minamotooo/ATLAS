# 06 — Question generation: USER prompt template

> **What this is.** The per-tuple message. One of these is sent for every
> (skill x Bloom level) pair, alongside the system prompt in `05`.
>
> **Where it lives.** `data-gen/question_gen_common.py` -> `USER_PROMPT_TEMPLATE`
> and `BLOOM_GUIDANCE`. **The code is the source of truth.**
>
> **How the placeholders are filled:**
>
> | Placeholder | Source |
> |---|---|
> | `{N}` | questions wanted per tuple |
> | `{SUBJECT}` `{SKILL_ID}` `{SKILL_FULL}` `{TOPIC_LABEL}` | the ontology tuple |
> | `{BLOOM_LEVEL}` | one of six — every skill is expanded to all six levels |
> | `{BLOOM_GUIDANCE}` | looked up from the table below |
> | `{PREREQ_LIST}` | the skill's prerequisite chain, from `prereqs.json` |
> | `{REFERENCE_BLOCKS}` | top-k similar real exam items, retrieved by the RAG layer |
>
> **The two things this template is really doing:**
>
> 1. **Grounding.** `{REFERENCE_BLOCKS}` injects real retrieved past-paper items
>    so the model copies authentic Bangla exam phrasing, notation and difficulty
>    rather than inventing a generic textbook voice. It is told to borrow style,
>    never content.
> 2. **Diagnostic wiring.** `{PREREQ_LIST}` is what lets a wrong answer mean
>    something. Each distractor is tied to a specific missing prerequisite, so
>    picking option C tells the engine *which* upstream skill is weak — not
>    merely that the student was wrong.
>
> ⚠️ **Note on Bloom expansion.** `expand_bloom_levels()` emits every skill at
> all six levels regardless of the skill's own stored level. That means
> Create-level questions get generated for pure recall facts
> (*"Recall the formula of Prussian blue"*), which is both wasteful and low
> quality. The skill's own `bloom` field is exactly the data needed to bound the
> range sensibly — consider using it before a full run.

---

## Bloom level guidance table

Substituted into `{BLOOM_GUIDANCE}`. The higher tiers are where most of the
work is: without them the model produces another calculation question and
labels it "Analyze".

**Remember**

> কোনো সংজ্ঞা, সূত্র, বা তথ্য সরাসরি স্মরণ করতে বলো।

**Understand**

> ধারণাটি ব্যাখ্যা করতে বলো।

**Apply**

> সুনির্দিষ্ট মান/তথ্য দিয়ে সরাসরি সমস্যা সমাধান করতে বলো।

**Analyze**

> স্টেমের মধ্যে অবশ্যই একটি সম্পূর্ণ, ধাপে-ধাপে সমাধান উপস্থাপন করতে হবে যেখানে ঠিক একটি নির্দিষ্ট, নামযোগ্য ভুল ধাপ আছে (যেমন: ভুল সাইন, ভুল সূত্র প্রয়োগ, একটি ধাপ বাদ পড়া)। প্রশ্ন হবে 'উপরের সমাধানে ভুলটি কোথায়?' বা 'কোন ধাপটি ভুল?' ধরনের — নিছক আরেকটি হিসাব-নির্ভর প্রশ্ন নয়। প্রতিটি option একটি সম্ভাব্য ভুল-ধাপকে নির্দেশ করবে।

**Evaluate**

> স্টেমে অবশ্যই দুটি ভিন্ন সমাধান-পদ্ধতি বা দুটি চূড়ান্ত উত্তর পাশাপাশি উপস্থাপন করতে হবে, এবং শিক্ষার্থীকে বিচার করতে বলতে হবে কোনটি সঠিক/বৈধ এবং কেন। প্রশ্নটি অবশ্যই এই একই স্কিলের মধ্যে থাকতে হবে — সম্পূর্ণ ভিন্ন বিষয়ের তুলনা নয়।

**Create**

> শিক্ষার্থীকে একটি নতুন সমীকরণ/ম্যাট্রিক্স/পরিস্থিতি নিজে তৈরি বা নির্বাচন করতে বলো যা একটি নির্দিষ্ট শর্ত পূরণ করে (যেমন: 'নিচের কোন ম্যাট্রিক্সটির নির্ণায়ক শূন্য হবে?')। এটি অবশ্যই একই স্কিল পরীক্ষা করবে — সম্পূর্ণ ভিন্ন কোনো গণনা বা সূত্র (যেমন adjugate, inverse) প্রবর্তন করা যাবে না যদি না তা স্পষ্টভাবে skill description-এর অংশ হয়।

---

## The template

```text
নিচের টুপলের জন্য {N}টি আলাদা MCQ প্রশ্ন তৈরি করো।
প্রতিটি প্রশ্ন অবশ্যই ৪টি অপশন (A/B/C/D)সহ MCQ হতে হবে — Written/খোলা প্রশ্ন নয়।
প্রতিটি প্রশ্ন আলাদা JSON object হবে — সবগুলো মিলে একটি JSON array হিসেবে output দাও।

TUPLE:
- Subject      : {SUBJECT}
- Bloom's Level : {BLOOM_LEVEL}
- Skill ID      : {SKILL_ID}
- Skill         : {SKILL_FULL}
- Topic         : {TOPIC_LABEL}

BLOOM LEVEL GUIDANCE:
{BLOOM_GUIDANCE}

THIS SKILL'S PREREQUISITE CHAIN (use these for missing_prerequisites only):
{PREREQ_LIST}

If the chain above is empty, set missing_prerequisites to [] for all options.

REFERENCE MATERIAL FROM KNOWLEDGE BASE (style/notation/solution patterns only —
do not copy; generate NEW MCQ questions for the skill/subject above.
If a ref is Written, convert the idea into an MCQ with four selectable options.):
{REFERENCE_BLOCKS}

For every generated question, set "subject" to "{SUBJECT}" and set source_refs to the
reference item_ids listed above (or the ones you actually used).

MCQ CHECKLIST (must all be true):
- stem is closed-ended (student picks one option)
- exactly 4 options A–D
- exactly one correct option
- no "লিখুন/ব্যাখ্যা কর/উত্তর দাও" written-style stems

DISTRACTOR HINT:
প্রতিটি ভুল option-এর জন্য উপরের prerequisite chain থেকে
একটি নির্দিষ্ট skill-এর অভাবকে কেন্দ্র করে distractor তৈরি করো।
```
