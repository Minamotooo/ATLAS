# HITL Review Log — Parameter Efficient Fine Tuning (LoRA)
**CSE 329: Machine Learning | Student ID: 2105066**
**LLM Used: Claude Sonnet 4.6 (Anthropic) via claude.ai**

---

## Overview

This log documents the Human-in-the-Loop (HITL) review process applied to each module's LLM-generated output. Each entry follows the structure: Raw Output Issues → Corrections Made → Rationale.

---

## Module 1: Lecture Note

### Step 1 — Raw LLM Output Summary
The initial draft covered the three required components but had the following issues:

### Step 2 — Technical Accuracy Review

**Issue 1.1 — Incorrect parameter count formula**
- *Raw output*: The initial draft stated "A ∈ ℝ^{d×r}, B ∈ ℝ^{r×k}" (A was d×r, B was r×k)
- *Problem*: This reverses the roles. In the LoRA paper (Hu et al. 2021), A is the down-projection (r×k) and B is the up-projection (d×r). The mistake would make the formula ΔW = BA mathematically inconsistent (BA would be d×r × r×k = d×k, which is correct dimensionally but the *naming* was wrong versus the canonical paper convention).
- *Correction*: Verified against original paper: A ∈ ℝ^{r×k} (down-projection), B ∈ ℝ^{d×r} (up-projection). Updated all references in Section A.2.1.
- *Rationale*: Students who read the original paper alongside the lecture note would be confused by inconsistent notation. Technical accuracy on mathematical definitions is non-negotiable.

**Issue 1.2 — DistilBERT module names were wrong**
- *Raw output*: Used `"query"` and `"value"` as target module names in the code example
- *Problem*: DistilBERT uses `"q_lin"` and `"v_lin"` (not `"query"/"value"` which are BERT's naming convention). Using wrong module names causes a `ValueError` at runtime.
- *Correction*: Verified by running `{name: type(m).__name__ for name, m in DistilBertModel.named_modules()}` locally. Updated target modules to `["q_lin", "v_lin"]` across all code examples and config.
- *Rationale*: All code must be runnable. A lecture note code example that fails on the first try destroys student trust.

**Issue 1.3 — Incomplete initialization explanation**
- *Raw output*: Stated "B is initialized to zero to ensure the adapter starts without contribution" without explaining *why* A cannot also be zero.
- *Problem*: Students could reasonably ask "why not initialize both to zero?" The dead gradient problem is the critical insight.
- *Correction*: Added explicit explanation: if both A and B are zero, ∂L/∂A ∝ Bᵀ = 0, making gradients zero permanently. The asymmetric initialization is mathematically necessary.
- *Rationale*: The pedagogical value of this section depends on explaining *why*, not just *what*.

### Step 3 — Pedagogical Quality Review

**Issue 1.4 — Bloom's learning objectives used non-action verbs**
- *Raw output*: LO1 read "Students will understand LoRA's mathematical foundations"
- *Problem*: "Understand" by itself is not a measurable Bloom's action verb. The assignment requires specific verbs from each level.
- *Correction*: Rewrote all 6 LOs with specific Bloom's action verbs: Define, Explain, Calculate, Contrast, Evaluate, Design — one per level.
- *Rationale*: The grading rubric explicitly checks "Bloom's correctly mapped at all 6 levels." Vague LOs fail this criterion.

**Issue 1.5 — Ethics section was generic**
- *Raw output*: Ethics section opened with "Like all AI systems, LoRA can be biased if the training data is biased." This is the boilerplate the assignment explicitly prohibits.
- *Problem*: The assignment requires topic-specific ethical analysis tied to LoRA's mechanics, not generic AI ethics.
- *Correction*: Rewrote Section C entirely. The revised version ties bias specifically to LoRA's concentrated low-rank updates (Section C.1), addresses the unique privacy risk of shareable adapter files being subject to membership inference attacks (Section C.2), and develops a detailed medical LLM scenario with HIPAA implications (Section C.5).
- *Rationale*: The rubric awards 5 marks for ethical integration. Generic ethics content scores in the "Weak" band. This was the highest-priority rewrite.

**Issue 1.6 — Comparison table missing "when to use each" column**
- *Raw output*: Comparison table had columns for "method, where params, overhead, performance"
- *Problem*: The module prompt explicitly requires "when to use each" as a column.
- *Correction*: Added "Best For" column with specific, actionable guidance per method.
- *Rationale*: Constructive alignment — students should be able to make method selection decisions (Evaluate level).

### Step 4 — Code Testing

**Issue 1.7 — Code example used deprecated `TrainingArguments` syntax**
- *Raw output*: Used `evaluation_strategy="epoch"` which is deprecated in transformers>=4.38 in favor of `eval_strategy="epoch"`.
- *Problem*: Students following the example would get a deprecation warning or error on library versions as specified in the assignment header.
- *Correction*: Updated to `eval_strategy="epoch"` and verified against transformers 4.38.0 changelog.
- *Rationale*: Library API accuracy. The lecture note code is a reference; it must match the specified library versions.

**Issue 1.8 — Pseudocode used undefined variable**
- *Raw output*: Pseudocode line `return W₀ @ x + (α / r) * B @ A @ x` used `@` notation that wasn't explained
- *Problem*: `@` is Python matrix multiplication — valid in context, but pseudocode should be notation-agnostic.
- *Correction*: Changed to explicit `B · A · x` notation in the pseudocode and reserved `@` only for the Python code sections.
- *Rationale*: Pseudocode should be readable without Python knowledge.

---

## Module 2: Theory Assessment

### Step 2 — Technical Accuracy Review

**Issue 2.1 — Q5 calculation had arithmetic error**
- *Raw output*: Q5 memory calculation used 2× multiplier for Adam (params + 1 moment copy) instead of 3× (params + 2 moment copies).
- *Problem*: Adam stores: (1) parameter, (2) first moment (momentum), (3) second moment (variance). The correct multiplier is 3, not 2.
- *Correction*: Updated Q5 answer key to use 3× multiplier. Recalculated: Full FT memory = 50.3M × 3 × 4 bytes = 603.6 MB. LoRA memory = 1.57M × 3 × 4 = 18.8 MB.
- *Rationale*: Numerical errors in answer keys directly harm students who use them for self-study.

**Issue 2.2 — Q12 proposal was vague ("use a higher rank")**
- *Raw output*: The Create-level question's answer key suggested "increasing r dynamically" without mathematical specificity.
- *Problem*: A Create-level answer key must demonstrate original synthesis at a level that "a peer researcher could implement it" (per the module prompt).
- *Correction*: Developed a concrete proposal with mathematical formulation: residual gradient projection, threshold τ criterion, rank-1 addition rule with SVD-based initialization. Added experimental validation design.
- *Rationale*: Bloom's Level 6 requires original synthesis with implementation-level detail. The answer key models what students should produce.

### Step 3 — Pedagogical Quality Review

**Issue 2.3 — Two questions initially mislabeled as Analyze (were Understand)**
- *Raw output*: Two questions asking students to "describe how LoRA differs from adapters" were labeled Bloom's Level 4: Analyze.
- *Problem*: Describing a difference without decomposing a failure or examining relationships is Bloom's Level 2: Understand (action verb: "compare"). The assignment explicitly warns against this error.
- *Correction*: Moved comparison questions to Level 2 (Q4). Wrote new novel-scenario questions for Level 4 (Q7: novel failure diagnosis, Q8: VLM component analysis). Verified using the action verbs table: Q7 uses "Diagnose," Q8 uses "Differentiate" — both genuine Level 4 verbs.
- *Rationale*: Mislabeled Bloom's levels is a specific error the assignment warns against. Correct labeling is required for full marks under the Theory Assessment rubric.

**Issue 2.4 — No question at Evaluate/Create level addressed ethical dimension**
- *Raw output*: All questions were technically focused; none engaged with ethics at the Evaluate or Create level.
- *Problem*: The module prompt explicitly requires "at least one question at Evaluate or Create level must engage with an ethical dimension."
- *Correction*: Added Q10 (Evaluate | Critique) specifically addressing the justification fallacy of using parameter count as a proxy for bias potential — a LoRA-specific ethical concern.
- *Rationale*: Explicit assignment requirement. Also, integrating ethics at the Evaluate level models the kind of critical technical+ethical reasoning students should develop.

**Issue 2.5 — Answer key for Q9 did not include legal domain risks**
- *Raw output*: Q9's answer key discussed only memory and performance, not domain-specific risks.
- *Problem*: Q9 specifically mentions "legal domain" — a full-mark answer must address risks specific to that context.
- *Correction*: Added legal domain risks: need for diverse jurisdiction coverage in validation set, precision requirements for legal summarization, risk of jurisdiction-specific bias.
- *Rationale*: Constructive alignment — the question explicitly asks about legal domain risks, so the answer key must model that reasoning.

---

## Module 3: Coding Assessment

### Step 2 — Technical Accuracy Review

**Issue 3.1 — Wrong target module names (same as Issue 1.2)**
- Corrected from `["query", "value"]` to `["q_lin", "v_lin"]` in both boilerplate and solution config blocks. Verified by importing distilbert-base-uncased and listing module names.

**Issue 3.2 — Scheduler was called inside warmup incorrectly**
- *Raw output*: Initial solution called `scheduler.step()` only at epoch boundaries, not per step.
- *Problem*: `LinearLR` with `total_iters=warmup_steps` expects to be stepped at each training step during warmup. Calling it per epoch would make the warmup span only `NUM_EPOCHS` steps (3 steps) instead of the intended `warmup_ratio × total_steps` (~670 steps).
- *Correction*: Moved `scheduler.step()` inside the training step function, called after each batch.
- *Rationale*: Incorrect scheduler usage produces suboptimal training dynamics. The solution must demonstrate correct PyTorch training loop practices.

**Issue 3.3 — merge_and_export did not save tokenizer**
- *Raw output*: Solution only saved merged model weights, not the tokenizer.
- *Problem*: A merged model directory without a tokenizer is incomplete — it cannot be loaded and used for inference independently. This is a real-world practice gap.
- *Correction*: Added tokenizer loading and saving in merge_and_export(). Also added directory listing log to show students what a complete model directory looks like.
- *Rationale*: Teaching correct model artifact practices is part of the Skill Component's learning objective.

### Step 4 — Code Testing

**Issue 3.4 — Boilerplate ran partially with a non-obvious error**
- *Raw output*: The boilerplate's `main()` function called `apply_lora_to_model()` before `build_lora_config()` returned a value — a sequencing error.
- *Problem*: The boilerplate must run cleanly (raising NotImplementedError for TODOs) without other errors.
- *Correction*: Reordered calls in main() to: load data → build_lora_config (T1) → load base model → apply_lora (T2) → efficiency analysis (T5). This matches the logical dependency order.
- *Rationale*: "Runs without errors (TODOs raise NotImplementedError)" is an explicit Pre-Submission Checklist requirement.

**Issue 3.5 — evaluate_loop had incorrect loss accumulation**
- *Raw output*: Computed mean loss as `total_loss / len(val_loader.dataset)` (dividing by number of examples instead of number of batches).
- *Problem*: This underestimates the loss by a factor of BATCH_SIZE.
- *Correction*: Changed to `total_loss / num_batches` where `num_batches` is counted inside the loop.
- *Rationale*: Numerical correctness. The expected output comment "val_loss ≈ 0.22–0.28" would be completely wrong with the original calculation.

**Issue 3.6 — T6 TODO difficulty was "Medium" but involves non-obvious merge semantics**
- *Raw output*: T6 was labeled "Medium"
- *Problem*: merge_and_unload() requires understanding of why merging is mathematically valid and what it means for inference — non-trivial for students at this level.
- *Correction*: Changed T6 to "Hard" and expanded the conceptual hint to explain the merge formula and the zero-latency benefit explicitly.
- *Rationale*: Difficulty labels should reflect genuine cognitive demand. Mislabeling affects how students allocate time.

### Step 5 — Cross-Module Consistency Check

**Issue 3.7 — Theory assessment Q5 referenced 1024×1024 matrices but code used DistilBERT (768-dim)**
- *Raw output*: Q5 used model dimensions not matching the coding assignment's model.
- *Problem*: Constructive alignment requires consistency across modules. Students could be confused about which dimensions apply.
- *Correction*: Retained Q5's 1024×1024 example (to test general calculation skill, not model-specific knowledge) but added a note in Q5 that this is a hypothetical architecture, distinct from the coding assignment's DistilBERT (768-dim).
- *Rationale*: Q5 tests Apply-level calculation skill, which should generalize beyond the specific model used in code. The distinction needs to be explicit.

---

## Summary of Changes

| Module | Issues Found | Technical | Pedagogical | Code | Cross-Module |
|--------|-------------|-----------|-------------|------|--------------|
| Lecture Note | 8 | 4 | 3 | 1 | 0 |
| Theory Assessment | 5 | 2 | 3 | 0 | 0 |
| Coding Assessment | 7 | 1 | 1 | 4 | 1 |
| **Total** | **20** | **7** | **7** | **5** | **1** |

**Most critical corrections**: Ethics section rewrite (1.5), Bloom's mislabeling fix (2.3), DistilBERT module names (1.2/3.1), scheduler placement (3.2), Adam memory multiplier (2.1).

The HITL process identified genuine errors that would have either produced incorrect results (Issues 1.2, 2.1, 3.2, 3.5), mislead students about ML concepts (1.3, 1.4), violated assignment requirements (1.5, 2.4), or broken code at runtime (1.7, 3.4). No module was submitted as raw LLM output.
