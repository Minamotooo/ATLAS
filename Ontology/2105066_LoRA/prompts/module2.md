# Module 2 Prompt — Theory Assessment Generator

## Technique: Role Prompting + Output Structuring + Constraint Setting + Chain-of-Thought

---

## Instruction

You are PedagogyGPT (see system prompt). Generate a **theory assessment** on `{{TOPIC}}` = Parameter Efficient Fine Tuning (LoRA) that covers all six Bloom's Taxonomy levels. This assessment must be fully aligned with the lecture note produced in Module 1.

Before writing each question, reason through: (1) what cognitive operation is required, (2) which action verb signals that level, (3) whether the scenario is novel (required for levels 4–6) or recall-based (acceptable for levels 1–2).

**Common mistake to avoid**: Do not label a question "Analyze" if a student only needs to recall or restate a fact. Analysis requires decomposing, diagnosing, or examining relationships. Use the action verbs as your self-check.

---

## Bloom's Taxonomy Reference

| Level | Cognitive Skill | Action Verbs |
|-------|----------------|--------------|
| 1. Remember | Recall facts | Define, list, state, recall, identify |
| 2. Understand | Explain in own words | Explain, compare, summarize, interpret |
| 3. Apply | Use in new situation | Calculate, implement, solve, predict |
| 4. Analyze | Examine relationships | Differentiate, contrast, diagnose, examine |
| 5. Evaluate | Justify a judgment | Justify, critique, assess, argue, recommend |
| 6. Create | Produce original work | Design, propose, formulate, synthesize |

---

## Required Output Structure

### Part I: Questions

For each question, use this exact format:

```
**Q[N]. [Bloom's Level N: Level Name] | Action Verb: [verb]**
[Question text]
```

**Requirements:**
- Minimum **2 questions per Bloom's level** (minimum 12 questions total)
- Levels 4–6 must present **novel scenarios** not seen in the lecture note
- At least **one question at Evaluate or Create level** must engage with an ethical dimension
- Questions should increase in complexity and cognitive demand

**Specific question guidance:**

*Remember (2 questions minimum)*:
- Ask students to recall LoRA's decomposition formula, key hyperparameters, or define terms

*Understand (2 questions minimum)*:
- Ask students to explain *why* low-rank decomposition is effective, or compare LoRA to adapters in their own words

*Apply (2 questions minimum)*:
- Give a concrete scenario (e.g., given a BERT model with d_model=768, r=8, target modules=[q,v]), calculate parameter savings
- Ask students to predict the effect of changing rank r on model capacity

*Analyze (2 questions minimum)*:
- Present a novel failure scenario (e.g., LoRA fine-tuned model performs well on training distribution but degrades catastrophically on a shifted test set) — ask students to diagnose
- Must be a new scenario, not an example from the lecture

*Evaluate (2 questions minimum)*:
- Ask students to argue for or against using LoRA vs. full fine-tuning in a specific constrained resource setting
- At least one must include an ethical dimension

*Create (2 questions minimum)*:
- Ask students to design a LoRA-based fine-tuning strategy for a multi-task setting
- Ask students to propose a modification to LoRA to address a known limitation

---

### Part II: Complete Answer Key

For each question, provide:

```
**Answer Key — Q[N]**
**Model Answer**: [Complete, correct answer]
**Marking Scheme**:
- [Criterion 1]: [N marks]
- [Criterion 2]: [N marks]
- Partial credit rule: [specific rule, e.g., "award 1/2 marks if student identifies the right concept but miscalculates"]
**Expected Response Depth**: [1-2 sentences describing what a full-mark answer looks like vs. a partial answer]
```

---

## Quality Checklist (self-verify before output)
- [ ] All 6 Bloom's levels represented with ≥2 questions each
- [ ] Each question labeled with level name and action verb
- [ ] Levels 4–6 use novel scenarios (not lecture examples restated)
- [ ] At least one Evaluate/Create question has ethical dimension
- [ ] Every answer key has model answer + marking scheme + partial credit rules
- [ ] No recall question is mislabeled as analysis
