import json
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2 import service_account

# ── 1. Load your data ──────────────────────────────────────────────────────────
with open("tuples.json", "r", encoding="utf-8") as f:
    tuples = json.load(f)

with open("prereqs.json", "r", encoding="utf-8") as f:
    prereqs_raw = json.load(f)

# ── 2. Build prerequisite list string ─────────────────────────────────────────
def build_prereq_list(prereqs):
    items = prereqs if isinstance(prereqs, list) else [prereqs]
    return "\n".join(f"- [{p['id']}] {p['full']}" for p in items)

def get_prereq_list_for_skill(skill_id):
    return build_prereq_list(prereqs_raw.get(skill_id, []))

# ── 3. Bloom guidance lookup ───────────────────────────────────────────────────
BLOOM_GUIDANCE = {
    "Remember":   "কোনো সংজ্ঞা, সূত্র, বা তথ্য সরাসরি স্মরণ করতে বলো।",
    "Understand": "ধারণাটি ব্যাখ্যা বা ব্যাখ্যা করতে বলো।",
    "Apply":      "সুনির্দিষ্ট সংখ্যা দিয়ে সরাসরি গাণিতিক সমস্যা সমাধান করতে বলো।",
    "Analyze":    "একটি সমাধান উপস্থাপন করো যেখানে ভুল আছে — শিক্ষার্থীকে ভুলটি চিহ্নিত করতে বলো।",
    "Evaluate":   "দুটি সমাধান বা পদ্ধতি তুলনা করতে বলো এবং কোনটি সঠিক বিচার করতে বলো।",
    "Create":     "একটি সমীকরণ স্থাপন করতে, শর্ত তৈরি করতে, বা পরিস্থিতি নির্মাণ করতে বলো।",
}

# ── 4. Prompt templates ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert question writer for the Bangladesh Civil Service (BCS) Examination, 
specializing in the Mathematical Reasoning section — specifically the "Arithmetic and 
Real Numbers" subsection covering: Real Numbers, HCF, LCM, Percentage, Simple & 
Compound Profit, Ratio & Proportions, and Profit & Loss.

Your candidates are adult civil service exam aspirants. Every question must match 
authentic BCS exam standard in style, difficulty, and presentation.

════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════
Output a JSON array of question objects. Each object must follow this exact schema:

{
  "bloom_level": string,
  "skill_id": string,
  "skill_description": string,
  "topic": string,
  "question_stem": string,
  "options": [
    {
      "label": "A",
      "text": string,
      "is_correct": boolean,
      "explanation": string,
      "missing_prerequisites": [
        {
          "id": string,
          "full": string
        }
      ]
    },
    ... (B, C, D)
  ]
}

════════════════════════════════════════
LANGUAGE RULES
════════════════════════════════════════
- question_stem: বাংলায় লিখুন (write in Bangla)
- option text: numerical expressions may stay as-is (e.g. "Tk 360", "25%"), 
  but word-based options must be in Bangla
- explanation: সকল ব্যাখ্যা বাংলায় লিখুন (all explanations in Bangla)
- missing_prerequisites: English only (skill IDs and descriptions)

════════════════════════════════════════
OPTION RULES
════════════════════════════════════════
1. Exactly ONE option must have is_correct: true.

2. EVERY option — including the correct one — must have a non-empty explanation.
   - Correct option explanation: বাংলায় ধাপে ধাপে সঠিক সমাধান দেখাও।
   - Wrong option explanation: বাংলায় সুনির্দিষ্টভাবে বলো শিক্ষার্থী ঠিক কোথায় 
     এবং কেন ভুল করেছে।

3. Wrong option missing_prerequisites: list only ancestor skills from the provided 
   prerequisite chain whose absence directly caused this specific error.
   Each entry must be an object with exactly two fields:
     - "id": the skill ID (e.g. "PRE3")
     - "full": the full skill description (e.g. "Multiply whole numbers")
   STRICT RULE: The skill being tested (skill_id) must NEVER appear in any 
    missing_prerequisites list. Only ancestors.
    CRITICAL: If the prerequisite chain is empty (e.g., PRE1: []), then
    missing_prerequisites MUST be [] for every option. Do not invent any.
    CRITICAL: The "id" and "full" values MUST match exactly one entry from the
    provided prerequisite chain. Do not create new IDs or descriptions.

4. Correct option missing_prerequisites: always empty [].

5. The correct answer must NOT always be in position A. Vary it across A/B/C/D.

════════════════════════════════════════
DISTRACTOR DESIGN RULES
════════════════════════════════════════
Each wrong option must be a number or expression a real BCS student would 
actually compute if they made one specific, nameable error:
- WRONG BASE, WRONG OPERATION, PARTIAL FORMULA, INVERTED FRACTION,
  WRONG METHOD CONFUSION, UNIT/DECIMAL ERROR

════════════════════════════════════════
BCS QUESTION STYLE RULES
════════════════════════════════════════
- Stem must be concise: one or two sentences maximum
- NEVER tell the student which method to use in the stem
- No textbook phrasing
- Numbers must be realistic BCS values: 2-3 digit whole numbers, clean integer results

CRITICAL: Do NOT output anything outside the JSON array. No markdown, no explanation."""

USER_PROMPT_TEMPLATE = """নিচের ৩-টুপলের জন্য {N}টি আলাদা MCQ প্রশ্ন তৈরি করো।
প্রতিটি প্রশ্ন আলাদা JSON object হবে — সবগুলো মিলে একটি JSON array হিসেবে output দাও।

TUPLE:
- Bloom's Level : {BLOOM_LEVEL}
- Skill ID      : {SKILL_ID}
- Skill         : {SKILL_FULL}
- Topic         : {TOPIC_LABEL}

BLOOM LEVEL GUIDANCE:
{BLOOM_GUIDANCE}

THIS SKILL'S PREREQUISITE CHAIN (use these for missing_prerequisites only):
{PREREQ_LIST}

If the chain above is empty, set missing_prerequisites to [] for all options.

DISTRACTOR HINT:
প্রতিটি ভুল option-এর জন্য উপরের prerequisite chain থেকে 
একটি নির্দিষ্ট skill-এর অভাবকে কেন্দ্র করে distractor তৈরি করো।"""

# ── 5. Configure Gemini ────────────────────────────────────────────────────────
SERVICE_ACCOUNT_PATH = Path(__file__).resolve().parent / "credentials.json"
if not SERVICE_ACCOUNT_PATH.exists():
    raise FileNotFoundError(
        f"Missing service account file: {SERVICE_ACCOUNT_PATH}. "
        "Place your Google service account JSON here as credentials.json."
    )

credentials = service_account.Credentials.from_service_account_file(
    str(SERVICE_ACCOUNT_PATH),
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

client = genai.Client(
    vertexai=True,
    project="focal-column-492108-d4",
    location="us-central1",
    credentials=credentials,
)

GENERATION_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    temperature=0.7,
    response_mime_type="application/json",
)

MODEL_NAME = "gemini-2.5-flash"

OUTPUT_PATH = Path(__file__).resolve().parent / "output_questions.json"
RAW_OUTPUT_DIR = Path(__file__).resolve().parent / "raw_responses"
START_TUPLE_INDEX = 506
  # 1-based index; 506 means start from tuples_list[505]

def save_questions(questions):
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

def parse_questions(raw_text, tuple_number):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        RAW_OUTPUT_DIR.mkdir(exist_ok=True)
        raw_path = RAW_OUTPUT_DIR / f"tuple_{tuple_number}_raw.txt"
        raw_path.write_text(raw_text, encoding="utf-8")

        fix_prompt = (
            "Fix the following into valid JSON. Output ONLY a JSON array of question objects. "
            "Do not add or remove questions, only fix JSON formatting.\n\n"
            f"RAW:\n{raw_text}"
        )
        fix_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=fix_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        fixed_text = (fix_response.text or "").strip()
        return json.loads(fixed_text)

# ── 6. Generate questions for each tuple ──────────────────────────────────────
N_QUESTIONS = 3
if OUTPUT_PATH.exists():
    try:
        with OUTPUT_PATH.open("r", encoding="utf-8") as f:
            existing_questions = json.load(f)
        all_questions = existing_questions if isinstance(existing_questions, list) else []
    except json.JSONDecodeError:
        all_questions = []
else:
    all_questions = []

tuples_list = tuples if isinstance(tuples, list) else [tuples]

start_index = max(START_TUPLE_INDEX - 1, 0)
for i, tup in enumerate(tuples_list):
    if i < start_index:
        continue
    print(f"Generating tuple {i+1}/{len(tuples_list)}: {tup['skillId']} @ {tup['bloom']}...")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        N              = N_QUESTIONS,
        BLOOM_LEVEL    = tup["bloom"],
        SKILL_ID       = tup["skillId"],
        SKILL_FULL     = tup["skillFull"],
        TOPIC_LABEL    = tup["topicLabel"],
        BLOOM_GUIDANCE = BLOOM_GUIDANCE.get(tup["bloom"], ""),
        PREREQ_LIST    = get_prereq_list_for_skill(tup["skillId"]),
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=GENERATION_CONFIG,
    )
    raw_text = (response.text or "").strip()

    # Strip markdown fences just in case
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    questions = parse_questions(raw_text, i + 1)
    if isinstance(questions, dict):       # sometimes Gemini wraps in an object
        questions = list(questions.values())[0]

    all_questions.extend(questions)
    save_questions(all_questions)
    print(f"  ✓ Got {len(questions)} questions")

# ── 7. Save output ─────────────────────────────────────────────────────────────
save_questions(all_questions)

print(f"\nDone! {len(all_questions)} total questions saved to {OUTPUT_PATH.name}")