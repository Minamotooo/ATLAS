# CSE 329 — Prompt Engineering Assignment
## Student ID: 2105066 | Topic: Parameter Efficient Fine Tuning (LoRA)

---

## Topic Assignment

**Student ID**: 2105066  
**Calculation**: 2105066 mod 25 = 16 → Topic 17  
**Topic**: Parameter Efficient Fine Tuning (LoRA)

---

## LLM Used

**Model**: Claude Sonnet 4.6 (claude-sonnet-4-6)  
**Provider**: Anthropic  
**Platform**: claude.ai (web interface)  
**Date of generation**: April 2026

---

## Repository Structure

```
2105066_LoRA/
├── prompts/
│   ├── system_prompt.md      # Global system prompt (role, constraints, topic var)
│   ├── module1.md            # Module 1 prompt: Lecture Note generator
│   ├── module2.md            # Module 2 prompt: Theory Assessment generator
│   └── module3.md            # Module 3 prompt: Coding Assessment generator
├── outputs/
│   ├── lecture_note.md       # Complete lecture note (Knowledge + Skill + Ethics)
│   ├── theory_assessment.md  # 12 questions (all 6 Bloom's levels) + answer keys
│   ├── coding_boilerplate.py # Student-facing Python file with 6 TODO sections
│   └── coding_solution.py    # Instructor solution (all TODOs implemented)
├── hitl_log/
│   └── hitl_review_log.md    # Structured HITL review log (20 issues documented)
└── README.md                 # This file
```

---

## Prompt Engineering Approach

### Technique 1: Role Prompting
The system prompt establishes a specific expert persona ("PedagogyGPT") with explicitly defined background and pedagogical commitments. This constrains the model's register, depth, and focus throughout all modules.

### Technique 2: Chain-of-Thought
Module prompts explicitly instruct the model to reason about student needs, common misconceptions, and appropriate depth before writing each section. The module1 prompt states: "Before writing each component, briefly reason about what students most need to understand."

### Technique 3: Few-Shot Examples
Each module prompt includes at least one worked example demonstrating the expected format, depth, and style. Module 1 includes a Batch Normalization excerpt showing equation format, variable definition style, and explanation depth. Module 3 includes a complete TODO block example showing exact format.

### Technique 4: Output Structuring
All module prompts specify exact section headers, table formats, code block structures, and naming conventions. Module 3 specifies the exact TODO comment format including all required fields (Bloom's Level, Difficulty, Expected lines, Description, Hints, Expected behavior).

### Technique 5: Constraint Setting
Every module includes explicit quantitative constraints: minimum question counts, word count minimums for ethics section (≥400 words), number of code TODOs (4–8), Bloom's level distribution requirements, and cross-module consistency requirements.

### Modularity & Topic-Agnosticism
The system prompt uses a `TOPIC = "..."` variable that can be changed to any of the 25 topics in the topic list. All module prompts reference `{{TOPIC}}` rather than hardcoding LoRA-specific content, making the prompt system reusable across the entire course.

---

## HITL Summary

20 issues were identified and corrected across three modules:
- **7 technical accuracy issues** (formula notation, API calls, arithmetic)
- **7 pedagogical quality issues** (Bloom's mislabeling, generic ethics, missing alignment)
- **5 code functionality issues** (runtime errors, incorrect calculations, sequencing)
- **1 cross-module consistency issue** (dimension mismatch between theory and code)

The most significant corrections were: complete rewrite of the ethics section (which was initially generic boilerplate), correction of Bloom's level mislabeling (two Understand questions labeled as Analyze), and fixing DistilBERT-specific module name errors that would have caused runtime failures.

See `hitl_log/hitl_review_log.md` for the full structured log.

---

## Deliverable Checklist

| Deliverable | File | Status |
|-------------|------|--------|
| System Prompt | prompts/system_prompt.md | ✓ |
| Module 1 Prompt | prompts/module1.md | ✓ |
| Module 2 Prompt | prompts/module2.md | ✓ |
| Module 3 Prompt | prompts/module3.md | ✓ |
| Lecture Note | outputs/lecture_note.md | ✓ |
| Theory Assessment | outputs/theory_assessment.md | ✓ |
| Coding Boilerplate | outputs/coding_boilerplate.py | ✓ |
| Coding Solution | outputs/coding_solution.py | ✓ |
| HITL Log | hitl_log/hitl_review_log.md | ✓ |
| README | README.md | ✓ |

---

## PE Techniques Summary

| Technique | Where Applied | Purpose |
|-----------|--------------|---------|
| Role Prompting | System prompt | Constrains persona, register, depth |
| Chain-of-Thought | Module 1, 2, 3 prompts | Pre-reasoning improves content quality |
| Few-Shot Examples | Module 1, 3 prompts | Demonstrates expected format and depth |
| Output Structuring | All module prompts | Enforces exact format compliance |
| Constraint Setting | All module prompts | Enforces quantitative requirements |
