# 07 — Question verification

> **What this is.** The quality gate. Every generated question is checked by a
> second model call before it is accepted.
>
> **Where it lives.** `data-gen/generate_question_gemini.py` ->
> `VERIFY_SYSTEM_PROMPT` and `verify_batch_combined()`;
> `data-gen/question_gen_common.py` -> `RELEVANCE_JUDGE_PROMPT`.
> **The code is the source of truth.**
>
> **Why a separate call.** Two failures that schema validation cannot catch:
>
> 1. **Off-skill drift.** Retrieved reference material pulls the model onto a
>    neighbouring skill — a matrix-determinant tuple producing a
>    straight-line-equation question — while still tagging the output with the
>    requested `skill_id`. The JSON is perfectly valid and the question is
>    filed against the wrong skill.
> 2. **Wrong answer key.** The model marks an option correct that is not.
>
> **Why it is not folded into generation.** Asking a model to check its own
> work in the same call produces self-assessment bias. The verifier re-solves
> each question **blind** — from the stem and options only, never told which
> option was marked correct — and its answer is then compared against the key.
>
> **Batching.** Questions from many tuples go in one call, each labelled
> `tuple.question`, cutting call count ~N-fold against the RPM limit. The two
> judgments stay per-question and independent, so batching two already-
> independent judges does not reintroduce the bias that folding them into
> generation would.
>
> **Two prompts here.** The combined judge is what runs in the Gemini pipeline.
> The standalone relevance judge is the backend-agnostic version of check (1).

---

## 7a — Combined verifier (relevance + blind re-solve)

This is the one that runs. System message:

```text
You are a strict subject-matter expert grader AND relevance judge for Bangladesh university admission exams (Math/Physics/Chemistry). For each question, do two independent things: (1) judge whether it genuinely tests the stated TARGET SKILL specifically - not just the same subject/topic, the exact skill - and (2) solve the question yourself from scratch using only the stem and options given, then state which option is correct. Do not assume any option is marked correct - work it out independently.
```

User message (assembled per batch):

```text
নিচের প্রতিটি প্রশ্নের জন্য:
(ক) এটি কি তার নিজস্ব দক্ষতা (প্রতিটির পাশে বন্ধনীতে দেওয়া) সরাসরি পরীক্ষা করে?
(খ) নিজে সমাধান করে সঠিক অপশন (A/B/C/D) নির্বাচন করো — কোনো অপশনকে সঠিক ধরে না নিয়ে।

{NUMBERED_QUESTION_BLOCKS}

শুধুমাত্র JSON দাও: {"results": [{"on_topic": true/false, "correct_answer": "A"}, ...]} — উপরের ক্রম অনুযায়ী (টিউপল ১-এর সব প্রশ্ন প্রথমে, তারপর টিউপল ২, ইত্যাদি)।
```

Each question block is rendered as:

```text
টিউপল <t>.<q> (দক্ষতা: <skillFull>): <question_stem>
  A) <option text>
  B) <option text>
  C) <option text>
  D) <option text>
```

Response schema (enforced structurally, not by instruction):

```json
{
  "type": "OBJECT",
  "properties": {
    "results": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "on_topic":       {"type": "BOOLEAN"},
          "correct_answer": {"type": "STRING", "enum": ["A", "B", "C", "D"]}
        },
        "required": ["on_topic", "correct_answer"]
      }
    }
  },
  "required": ["results"]
}
```

**Acceptance:** a question passes only if `on_topic` is true **and**
`correct_answer` matches the option the generator marked correct. Either
failure rejects it; the tuple is retried up to `MAX_VERIFY_RETRIES` (2).

---

## 7b — Standalone relevance judge

The backend-agnostic version of check (1), for pipelines without the combined
verifier.

```text
তুমি একজন বাংলাদেশ ভর্তি পরীক্ষার প্রশ্ন যাচাইকারী।
নিচের প্রতিটি প্রশ্ন কেবলমাত্র এই একটি নির্দিষ্ট দক্ষতা পরীক্ষা করে কিনা যাচাই করো:

দক্ষতা: {SKILL_FULL}

প্রশ্নসমূহ:
{NUMBERED_STEMS}

প্রতিটি প্রশ্নের জন্য true দাও যদি সেটি সরাসরি উপরের দক্ষতাটি পরীক্ষা করে, নাহলে false দাও
(এমনকি যদি প্রশ্নটি একই বিষয়ের/টপিকের হলেও ভিন্ন দক্ষতা পরীক্ষা করে, তাহলে false)।

শুধুমাত্র একটি JSON boolean array output দাও, উদাহরণ: [true, false, true]
অন্য কোনো লেখা, ব্যাখ্যা, বা markdown যোগ করবে না।
```
