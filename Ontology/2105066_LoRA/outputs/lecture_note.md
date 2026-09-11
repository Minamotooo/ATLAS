# Lecture Note: Parameter Efficient Fine Tuning (LoRA)
**CSE 329: Machine Learning | Student ID: 2105066**

---

## Learning Objectives

By the end of this lecture, students will be able to:

1. **Define** the low-rank decomposition formula used in LoRA and identify its key hyperparameters (Remember)
2. **Explain** why LoRA reduces trainable parameters without significantly sacrificing model quality (Understand)
3. **Calculate** the parameter savings achieved by LoRA given a model architecture and rank configuration (Apply)
4. **Contrast** LoRA with alternative PEFT methods (adapters, prefix tuning, prompt tuning) across computational and quality dimensions (Analyze)
5. **Evaluate** when LoRA is the appropriate choice versus full fine-tuning given resource and quality constraints (Evaluate)
6. **Design** a LoRA-based fine-tuning pipeline for a novel multi-task or domain-adaptation scenario (Create)

---

## A) Knowledge Component

### A.1 Motivation & Problem Statement

Large pre-trained language models such as GPT-3 (175B parameters) and LLaMA-2 (70B parameters) have demonstrated remarkable generalization across tasks. However, adapting these models to downstream tasks via **full fine-tuning** — updating all parameters — poses three critical challenges:

1. **Memory cost**: Storing optimizer states (e.g., Adam requires 2× gradient copies) for a 7B model requires ~84GB of GPU memory in float32, far exceeding typical hardware.
2. **Storage cost**: Each fine-tuned task requires a full model copy. Deploying 100 task-specific variants of a 7B model demands 700GB+ of storage.
3. **Catastrophic forgetting**: Unrestricted weight updates can degrade the model's general capabilities while specializing it for a narrow task.

**LoRA** (Low-Rank Adaptation; Hu et al., 2021) addresses all three challenges through a key insight: *the weight updates during fine-tuning have low intrinsic rank*. That is, even though the weight matrix ΔW ∈ ℝ^{d×k} could theoretically be full rank, in practice the meaningful change is confined to a much lower-dimensional subspace. LoRA constrains ΔW to this subspace explicitly.

---

### A.2 Core Mathematical Foundations

#### A.2.1 The Low-Rank Decomposition

In full fine-tuning, a pre-trained weight matrix W₀ ∈ ℝ^{d×k} is updated to W₀ + ΔW, where ΔW is unconstrained. LoRA instead parametrizes the update as:

```
ΔW = B · A
```

where:
- **A ∈ ℝ^{r×k}**: the "down-projection" matrix (projects input to low-rank space)
- **B ∈ ℝ^{d×r}**: the "up-projection" matrix (projects back to output dimension)
- **r ≪ min(d, k)**: the rank, a hyperparameter controlling capacity

The matrices A and B together have **r(d + k)** parameters, compared to **d·k** for the full ΔW. For a typical attention weight in BERT (d=k=768, r=8): full = 589,824 parameters; LoRA = 12,288 parameters — a **48× reduction**.

#### A.2.2 Initialization Strategy

LoRA uses an asymmetric initialization:
- **A is initialized with random Gaussian**: A ~ N(0, σ²) — this introduces random low-rank directions to explore
- **B is initialized to zero**: B = 0 — this ensures ΔW = BA = 0 at training start, so the model behaves exactly like the pre-trained model initially

This initialization is critical: it means LoRA does **not** perturb the pre-trained weights at training start, preserving the model's pre-trained representations while gradually adapting.

#### A.2.3 The α Scaling Factor

The full modified forward pass for a weight layer is:

```
h = W₀x + (α / r) · B · A · x
```

where α is a constant scaling hyperparameter. The scaling factor (α/r) serves two purposes:
1. **Stabilization**: It decouples the effective learning rate of the LoRA branch from r, so that changing r doesn't require re-tuning α.
2. **Calibration**: By setting α = r, the scaling becomes 1.0, making the LoRA update directly comparable in magnitude to the base weights.

Common practice: set α = 2r (e.g., r=8 → α=16) or α=r. The ratio α/r acts as a multiplier on the LoRA learning rate.

#### A.2.4 Parameter Count Comparison

| Method | Trainable Params (7B model) | Storage per Task |
|--------|---------------------------|-----------------|
| Full Fine-Tuning | 7,000,000,000 | ~14GB (fp16) |
| LoRA (r=8, 4 modules) | ~4,000,000 | ~8MB |
| LoRA (r=16, 4 modules) | ~8,000,000 | ~16MB |
| Adapter Layers | ~3,600,000 | ~7MB |
| Prefix Tuning | ~500,000 | ~1MB |

LoRA typically achieves **<1% of full fine-tuning parameters** while matching or approaching full fine-tuning performance.

#### A.2.5 Pseudocode: Applying LoRA to a Transformer

```
Algorithm: LoRA Fine-Tuning

Input:  Pre-trained model M with weights {W_q, W_k, W_v, W_o, ...}
        Target modules T ⊆ {q, v, k, o, ...}
        Rank r, alpha α, training data D

1. FREEZE all parameters in M:
   for each parameter p in M:
       p.requires_grad = False

2. INJECT LoRA adapters into target modules:
   for each module name t in T:
       W₀ = M.get_weight(t)        # shape: [d, k]
       A_t = random_gaussian([r, k])  # down-projection
       B_t = zeros([d, r])            # up-projection
       register A_t, B_t as trainable parameters

3. DEFINE modified forward pass:
   function lora_forward(x, W₀, A, B, α, r):
       return W₀ @ x + (α / r) * B @ A @ x

4. TRAIN only A_t, B_t for all t in T:
   for each batch (x, y) in D:
       ŷ = M.forward(x)    # uses lora_forward internally
       loss = criterion(ŷ, y)
       loss.backward()
       optimizer.step()     # updates only A_t, B_t

5. SAVE only the adapter weights {A_t, B_t} for t in T
   (base model W₀ is unchanged and shared)

6. OPTIONAL — MERGE for inference efficiency:
   W_merged = W₀ + (α / r) * B @ A
   Replace W₀ with W_merged; discard A, B
```

---

### A.3 Comparison with Related PEFT Methods

| Method | Where Params Added | Inference Overhead | Task Switch Cost | Performance Gap vs Full FT | Best For |
|--------|-------------------|-------------------|-----------------|---------------------------|----------|
| **Full Fine-Tuning** | All layers | None | Full model reload | None (baseline) | Max performance, ample GPU |
| **LoRA** | Parallel to attention weights | None (if merged) | Swap adapters only | <1–2% | Most PEFT scenarios |
| **Adapter Layers** | Serial between attention & FFN | +15–30% latency | Swap adapters | ~1–3% | Modular multi-task |
| **Prefix Tuning** | Input sequence (virtual tokens) | Sequence length ↑ | Swap prefix | 2–5% on some tasks | Generative tasks, NLG |
| **Prompt Tuning** | Input embeddings only | Minimal | Swap soft prompt | 3–8% (small models) | Very large models (>11B) |
| **IA³** | Rescaling vectors in attention | None | Swap vectors | ~1–2% | Extremely constrained setups |

**Key insight**: LoRA is the dominant choice for most practical PEFT because it adds **zero inference latency** when weights are merged, adapts well across tasks, and achieves near-full-fine-tuning performance on many benchmarks.

---

### A.4 Real-World Applications

**1. Domain Adaptation of LLMs**
A medical AI company fine-tunes Mistral-7B on clinical notes using LoRA (r=16, target: q,v projections). The resulting adapter (~32MB) is served alongside the base model. Different hospital departments use different adapters (oncology, cardiology, radiology) sharing one base model instance — dramatically reducing infrastructure costs.

**2. Multilingual NLP**
Meta researchers use LoRA to adapt LLaMA-2 to low-resource languages. Since full fine-tuning on small datasets risks overfitting, the low-rank constraint acts as implicit regularization. Each language gets a separate adapter (~8MB); the base model is shared across 50+ languages.

**3. Text-to-Image Model Fine-Tuning**
In Stable Diffusion (a diffusion model), LoRA adapters are applied to the UNet's cross-attention layers to teach the model new visual styles or subjects. Users share LoRA adapter files (~2–6MB) via platforms like CivitAI, enabling community-driven style customization without distributing the full 2GB base model.

---

## B) Skill Component

### B.1 Step-by-Step Implementation Guide

**Prerequisites**: `pip install transformers==4.38.0 peft==0.9.0 datasets==2.18.0 torch==2.1.0`

**Step 1: Load and inspect the base model**
Always load the pre-trained model without modifications first, verify its architecture, and note which layers you will target.

**Step 2: Define LoRA configuration**
The `LoraConfig` object specifies: rank (r), alpha, dropout, and which modules to target. For transformer models, `q_proj` and `v_proj` (query and value projections) are the standard default targets.

**Step 3: Wrap with PEFT**
`get_peft_model(model, lora_config)` injects the LoRA adapters and freezes base weights automatically. Always call `model.print_trainable_parameters()` to verify.

**Step 4: Train normally**
The wrapped model is a standard PyTorch `nn.Module`. Use your usual training loop with AdamW optimizer. Only the adapter parameters receive gradients.

**Step 5: Save adapters**
`model.save_pretrained(output_dir)` saves only the adapter weights. The base model is not saved (it's unchanged).

**Step 6: Load and inference**
Load base model, then load adapter with `PeftModel.from_pretrained()`. Optionally merge weights for zero-latency inference.

---

### B.2 Complete Code Example

```python
# Requirements: transformers==4.38.0, peft==0.9.0, datasets==2.18.0, torch==2.1.0
from transformers import AutoModelForSequenceClassification, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from datasets import load_dataset
import torch
import numpy as np

# ── Config ──────────────────────────────────────────────────────────────────
MODEL_NAME = "distilbert-base-uncased"
DATASET_NAME = "sst2"
LORA_R = 8
LORA_ALPHA = 16         # α = 2r is a common rule of thumb
LORA_DROPOUT = 0.1
LORA_TARGET_MODULES = ["q_lin", "v_lin"]  # DistilBERT attention projections
NUM_LABELS = 2
MAX_SEQ_LEN = 128
BATCH_SIZE = 16
LEARNING_RATE = 3e-4    # LoRA can tolerate higher LR than full FT
NUM_EPOCHS = 3
OUTPUT_DIR = "./lora_sst2"

# ── 1. Load data ─────────────────────────────────────────────────────────────
dataset = load_dataset("glue", DATASET_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(examples):
    return tokenizer(examples["sentence"], truncation=True, max_length=MAX_SEQ_LEN)

tokenized = dataset.map(tokenize, batched=True)

# ── 2. Load base model ───────────────────────────────────────────────────────
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=NUM_LABELS)
print(f"Base model params: {sum(p.numel() for p in model.parameters()):,}")

# ── 3. Configure LoRA ────────────────────────────────────────────────────────
lora_config = LoraConfig(
    task_type=TaskType.SEQ_CLS,     # Sequence classification
    r=LORA_R,                        # Low-rank dimension
    lora_alpha=LORA_ALPHA,           # Scaling factor
    target_modules=LORA_TARGET_MODULES,
    lora_dropout=LORA_DROPOUT,
    bias="none",                     # Don't adapt bias terms (usually not needed)
    inference_mode=False,
)

# ── 4. Apply LoRA ─────────────────────────────────────────────────────────────
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Output: trainable params: 296,450 || all params: 66,955,010 || trainable%: 0.44

# ── 5. Train ──────────────────────────────────────────────────────────────────
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {"accuracy": (predictions == labels).mean()}

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LEARNING_RATE,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    fp16=torch.cuda.is_available(),
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["validation"],
    compute_metrics=compute_metrics,
)
trainer.train()

# ── 6. Save adapter & merge ────────────────────────────────────────────────
model.save_pretrained(OUTPUT_DIR)
print(f"Adapter saved to {OUTPUT_DIR}")

# Merge for inference (zero latency)
merged_model = model.merge_and_unload()
merged_model.save_pretrained(f"{OUTPUT_DIR}_merged")
```

---

### B.3 Common Pitfalls & Debugging Tips

**Pitfall 1: Wrong target module names**
- *Symptom*: `ValueError: Target modules not found in the model`. 
- *Fix*: Print `{name: type(m).__name__ for name, m in model.named_modules()}` to discover exact layer names. Different model families use different naming conventions (`q_proj`, `q_lin`, `query`, etc.).

**Pitfall 2: Forgetting to set `inference_mode=False` during training**
- *Symptom*: LoRA adapters don't update; validation accuracy stays at random baseline.
- *Fix*: Ensure `inference_mode=False` in `LoraConfig` during training. Set `inference_mode=True` only when loading for pure inference.

**Pitfall 3: Mismatched α/r ratio causing training instability**
- *Symptom*: Loss diverges early, or gradient norms explode.
- *Fix*: The effective LoRA LR is `learning_rate × (α/r)`. If α=64, r=4, the LoRA branch sees 16× amplified gradients. Keep α ≤ 2r for stability, or reduce the base learning rate.

**Pitfall 4: Adapter-only saving but full model loading at inference**
- *Symptom*: Loading `model.save_pretrained()` output as a plain `AutoModel` fails or loads wrong weights.
- *Fix*: Always load with `PeftModel.from_pretrained(base_model, adapter_dir)`, not `AutoModel.from_pretrained(adapter_dir)`.

**Pitfall 5: Rank too high causing overfitting on small datasets**
- *Symptom*: Training accuracy ≈ 100%, validation accuracy much lower.
- *Fix*: Reduce r. For datasets <10k examples, r=4 or r=8 with dropout=0.1 is typical. The low-rank constraint is the regularizer; defeating it by using r=64 on tiny data defeats the purpose.

---

### B.4 Hyperparameter Tuning Guide

| Hyperparameter | Role | Recommended Range | Search Strategy |
|---------------|------|-------------------|----------------|
| **r (rank)** | Capacity of adapter; higher r = more expressive | 4, 8, 16, 32 | Start at 8; increase if underfitting |
| **α (alpha)** | Scales LoRA update; effective LR multiplier = α/r | r to 2r (e.g., 8–16 for r=8) | Set α=r first; increase to 2r if underfitting |
| **dropout** | Regularization in LoRA branch | 0.0–0.1 | 0.0 for large datasets; 0.05–0.1 for small |
| **target_modules** | Which weight matrices get adapters | q,v (minimal); q,k,v,o (more capacity) | Start with q,v; add k,o if quality insufficient |
| **learning_rate** | Base LR for AdamW on adapter params | 1e-4 to 5e-4 | Much higher than full FT; start at 3e-4 |
| **bias** | Whether to adapt bias terms | "none", "all", "lora_only" | "none" works well; "lora_only" sometimes helps |

**Search strategy**: Use a sweep over r ∈ {4, 8, 16} and α ∈ {r, 2r} first (6 configs). Fix the best (r, α) pair, then sweep learning_rate ∈ {1e-4, 3e-4, 5e-4}.

---

## C) Ethical Implications & Values Component

### C.1 Bias Amplification via LoRA Fine-Tuning

LoRA's efficiency makes it easier and cheaper to fine-tune large models on narrowly curated datasets — which amplifies a specific class of risk: **targeted bias injection**. Unlike full fine-tuning, which modulates all parameters and thus requires large, diverse datasets to achieve good results, LoRA can achieve significant behavioral shifts with as few as a few hundred examples due to the concentrated, low-rank update.

**Mechanism**: When a practitioner fine-tunes a model using LoRA on a dataset reflecting a skewed subpopulation (e.g., clinical notes from a single hospital system serving a homogeneous demographic), the adapter learns to reinforce the biases present in that corpus. The base model's broader representations are frozen; only the LoRA-adapted weights shift. This creates a model that may perform well on the local distribution but systematically underperforms for out-of-distribution groups not represented in the fine-tuning data.

**Detection methods**: 
- **Demographic parity analysis**: After fine-tuning, evaluate model outputs stratified by demographic subgroup proxies in the evaluation set.
- **Adapter weight analysis**: Inspect the singular value decomposition of BA. If the dominant singular vectors align with specific linguistic or demographic features, this suggests the adapter has learned group-specific representations.
- **Red-teaming**: Use adversarial prompts to probe for group-specific failures before deployment.

### C.2 Privacy and Data Protection Concerns

LoRA introduces **novel privacy attack surfaces** not fully present in full fine-tuning:

**Adapter leakage**: Because LoRA adapters are small files (a few MB) that are commonly shared (e.g., on HuggingFace Hub or CivitAI), sensitive information encoded in the adapter during fine-tuning on private data may be extracted. Research has shown that **membership inference attacks** — methods that determine whether a specific data point was in the training set — are feasible against LoRA adapters. Since the adapter precisely encodes the fine-tuning distribution shift, it may be more vulnerable than a fully fine-tuned model where the training signal is diffused across all parameters.

**Medical/legal data risks**: If an organization uses LoRA to adapt a base LLM on proprietary medical records, legal documents, or financial data, the resulting adapter file effectively compresses and stores a representation of that confidential corpus. Distributing the adapter (even internally) may constitute unauthorized data transfer.

**Mitigation**: Apply **differential privacy (DP)** during LoRA training using libraries such as `opacus`. DP-LoRA adds calibrated Gaussian noise to gradients, providing formal guarantees (ε, δ)-DP that bound what an adversary can infer from the adapter weights.

### C.3 Societal Impact

**Who benefits**:
- **Resource-constrained researchers and institutions**: LoRA democratizes access to large model fine-tuning. A lab with a single A100 GPU can now fine-tune a 7B model where previously this required a cluster. This enables multilingual NLP in low-resource language communities, medical AI in developing healthcare systems, and academic research without large compute budgets.
- **Multi-tenant deployment systems**: Companies can serve a single base model and dynamically swap adapters per user/task, dramatically reducing infrastructure costs and carbon footprint relative to maintaining separate full model copies.

**Who may be harmed**:
- **Targets of misuse**: LoRA's low cost lowers the barrier for malicious fine-tuning. Bad actors can cheaply fine-tune a base LLM to impersonate a specific person (voice style, writing style), generate targeted disinformation, or bypass content safety filters by adapting away safety alignment layers using relatively small datasets.
- **Communities underrepresented in fine-tuning data**: When organizations deploy LoRA-adapted models without rigorous bias evaluation, communities not represented in the fine-tuning corpus may receive degraded service quality — a harm that is often invisible without deliberate measurement.

### C.4 Responsible AI Practices for LoRA

1. **Audit the fine-tuning dataset** before training: apply bias auditing tools (e.g., Aequitas, Fairlearn) to the training corpus to identify representation gaps.
2. **Test adapters on diverse holdout sets** including subgroups not well-represented in training.
3. **Document adapter provenance**: any shared adapter should include a model card specifying the training data source, intended use, and known limitations.
4. **Apply DP-LoRA** when fine-tuning on sensitive personal data.
5. **Evaluate safety alignment preservation**: test whether safety fine-tuning of the base model remains effective after LoRA adaptation.

### C.5 Concrete Ethical Scenario: Medical LLM Fine-Tuning Without Consent

**Scenario**: A private hospital fine-tunes Llama-2-7B using LoRA on 50,000 electronic health records (EHRs) containing patient diagnoses, medications, and clinical notes. The goal is to create a clinical note summarization assistant. The hospital uses a cloud compute provider, and the resulting LoRA adapter (~16MB) is stored in a shared internal repository accessible to 300 hospital staff, including administrative personnel.

**What went wrong**:
1. *Lack of consent*: Patients whose EHRs were used for model training were not informed or asked for consent. In many jurisdictions (EU under GDPR, USA under HIPAA), using identifiable health data for AI training without explicit consent or proper anonymization is a legal and ethical violation.
2. *Inadequate anonymization*: EHRs contain quasi-identifiers (age, diagnosis codes, medication combinations) that are not removed by standard de-identification. The LoRA adapter may memorize rare patient profiles, making them recoverable via membership inference attacks.
3. *Overly broad access*: Storing the adapter in a shared repository where administrative staff can access it creates unauthorized exposure of implicitly encoded patient data.
4. *No bias evaluation*: The EHR dataset likely over-represents certain demographics (the hospital's patient base). The resulting model may perform poorly — or give clinically dangerous outputs — for patient populations underrepresented in the training data.

**Prevention**:
- Obtain explicit, informed consent or use fully anonymized data under a formal data governance framework.
- Apply DP-LoRA (ε < 8) during training to provide formal privacy guarantees.
- Restrict adapter access to authorized clinical staff only; treat the adapter file with the same security classification as raw EHR data.
- Conduct bias evaluation across age, sex, ethnicity, and diagnosis category subgroups before clinical deployment.
- Publish an internal model card with known limitations and out-of-distribution risk areas before deployment.

This scenario illustrates that LoRA's efficiency is a double-edged sword: it makes powerful AI tools accessible to small institutions, but those same institutions may lack the data governance expertise to deploy them responsibly. The technical ease of LoRA must be matched with institutional maturity in AI ethics and privacy.
