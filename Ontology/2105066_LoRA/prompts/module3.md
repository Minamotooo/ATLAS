# Module 3 Prompt — Coding Assessment Generator

## Technique: Output Structuring + Constraint Setting + Chain-of-Thought + Few-Shot

---

## Instruction

You are PedagogyGPT (see system prompt). Generate **two complete Python files** for a coding assessment on `{{TOPIC}}` = Parameter Efficient Fine Tuning (LoRA):

1. **`coding_boilerplate.py`** — Student-facing file with TODO sections
2. **`coding_solution.py`** — Complete instructor solution

Both files must be **fully runnable `.py` scripts**, not notebook fragments.

---

## Few-Shot Example: Correct TODO Format

```python
# TODO [T1]: Compute batch normalization
# Bloom's Level: Apply
# Difficulty: Easy | Expected lines: ~5
# Description: Implement the batch normalization formula: normalize inputs
#              across the batch dimension, then apply learned scale (gamma)
#              and shift (beta) parameters. This is the core operation that
#              stabilizes training by reducing internal covariate shift.
# Hints:
#   1. (Conceptual) The mean and variance are computed over the batch dimension (axis=0),
#      not the feature dimension.
#   2. (Implementation) Use torch.var with unbiased=False for the population variance.
# Expected behavior: Output tensor has same shape as input; mean ≈ 0, std ≈ 1 before scaling.
# >>> YOUR CODE HERE <<<
raise NotImplementedError("TODO T1 not yet implemented")
# >>> END YOUR CODE <<<
```

Match this exact format for all TODOs.

---

## File A: Student Boilerplate — `coding_boilerplate.py`

### Header (pre-completed, students do not touch)
```python
"""
CSE 329: Machine Learning — Coding Assessment
Topic: Parameter Efficient Fine Tuning (LoRA)
Student ID: 2105066

Python: 3.10+
Required libraries:
    torch==2.1.0
    transformers==4.38.0
    peft==0.9.0
    datasets==2.18.0
    scikit-learn==1.4.0
    matplotlib==3.8.0

Dataset: SST-2 (Stanford Sentiment Treebank) via HuggingFace datasets
Task: Sentiment classification using LoRA fine-tuned DistilBERT

Run: python coding_boilerplate.py
"""
```

### Pre-completed sections (students do not modify):
1. **All imports** with version checks using `importlib.metadata`
2. **Config block** — all hyperparameters as named constants (NO magic numbers):
   - `MODEL_NAME`, `DATASET_NAME`, `TASK`, `MAX_SEQ_LEN`
   - `LORA_R`, `LORA_ALPHA`, `LORA_DROPOUT`, `LORA_TARGET_MODULES`
   - `BATCH_SIZE`, `LEARNING_RATE`, `NUM_EPOCHS`, `SEED`
   - `OUTPUT_DIR`, `LOG_INTERVAL`
3. **Data loading and preprocessing**: Load SST-2, tokenize, create DataLoaders
4. **Logging/plotting utilities**: `plot_training_curve()`, `log_metrics()` functions
5. **`main()` entry point** that calls student functions in order
6. **Validation harness**: `validate_lora_config()`, `validate_model_output()` functions students can call

### TODO Sections (students implement — 6 TODOs):

**T1 — Apply LoRA Config** (Apply | Easy | ~8 lines)
- Create a `LoraConfig` object using the PEFT library with the config constants
- Explain: choosing target modules determines which weight matrices receive adapters

**T2 — Apply LoRA to Model** (Apply | Easy | ~5 lines)
- Wrap the base model with `get_peft_model()` and print trainable parameter count
- Must call the validation harness after completion

**T3 — Implement Training Step** (Apply | Medium | ~15 lines)
- Single training step: forward pass, loss, backward, optimizer step, scheduler step
- Must handle gradient clipping

**T4 — Implement Evaluation Loop** (Analyze | Medium | ~20 lines)
- Full evaluation loop computing accuracy and loss on validation set
- Must return metrics dict; no gradient computation

**T5 — Parameter Efficiency Analysis** (Analyze | Medium | ~10 lines)
- Write a function `compute_parameter_efficiency(model)` that returns:
  - total parameters, trainable parameters, trainable percentage, memory saving estimate
- Compare LoRA vs. full fine-tuning parameter counts programmatically

**T6 — Adapter Merging** (Create | Hard | ~10 lines)
- Implement `merge_and_export(model, output_path)` that merges LoRA weights into base model and saves
- Students must reason about *why* merging is useful at inference time

---

## File B: Instructor Solution — `coding_solution.py`

Requirements:
- Every TODO filled with correct, working code
- Each filled TODO preceded by a comment block explaining the design rationale (the *why*)
- Runs end-to-end on SST-2 without errors
- Documents expected outputs as comments:
  ```python
  # Expected output after T2:
  # trainable params: 887,042 || all params: 67,642,882 || trainable%: 1.31
  ```
- Includes performance benchmarks as comments:
  ```python
  # Benchmark (on CPU, ~5 epochs, SST-2 dev set):
  # Training time: ~15 min | Val accuracy: ~91% | Loss: ~0.24
  # Hardware: CPU only (no GPU required for this demo)
  ```

---

## Pre-Submission Checklist

| Check | Boilerplate | Solution |
|-------|------------|----------|
| Runs without errors (TODOs raise NotImplementedError) | Required | N/A |
| Runs end-to-end | N/A | Required |
| Imports present & version-pinned | Required | Required |
| Config block (no magic numbers) | Required | Required |
| TODO format matches spec | Required | N/A (filled) |
| Validation harness included | Required | Passes all checks |
| Comments explain "why" | In TODO descriptions | In solution comments |

---

## Quality Checklist (self-verify before output)
- [ ] Exactly 6 TODOs with unique IDs T1–T6
- [ ] At least one Apply, one Analyze, one Create TODO
- [ ] Every TODO has `raise NotImplementedError`
- [ ] TODO format exactly matches the example above
- [ ] Validation harness functions are present
- [ ] Solution runs end-to-end and documents expected outputs
- [ ] No magic numbers in config block
- [ ] Both files have complete, accurate headers
