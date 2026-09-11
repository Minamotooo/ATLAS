# Module 1 Prompt — Lecture Note Generator

## Technique: Few-Shot + Chain-of-Thought + Output Structuring + Constraint Setting

---

## Instruction

You are PedagogyGPT (see system prompt). Generate a **detailed, pedagogically sound lecture note** on the topic below for upper-undergraduate ML students. The note must contain exactly three components as specified. Before writing each component, briefly reason (internally) about what students most need to understand, what common misconceptions exist, and what real-world context will make the content click.

**Topic**: `{{TOPIC}}` = Parameter Efficient Fine Tuning (LoRA)

---

## Few-Shot Example of Expected Depth and Style

**Example (for a different topic — Batch Normalization):**

> **A) Knowledge Component — Excerpt**
> Batch Normalization (Ioffe & Szegedy, 2015) addresses internal covariate shift by normalizing layer inputs across a mini-batch. For a mini-batch B = {x₁, ..., xₘ}, the normalized output is:
> ŷᵢ = γ · (xᵢ − μ_B) / √(σ²_B + ε) + β
> where μ_B and σ²_B are the batch mean and variance, γ and β are learned scale and shift parameters, and ε is a small constant for numerical stability. The key insight is that normalizing inputs to each layer stabilizes the distribution of activations, allowing higher learning rates and reducing sensitivity to weight initialization.

This example shows: (1) precise mathematical notation, (2) attribution, (3) clear explanation of *why* the technique works, (4) explicit variable definitions. Match this level of rigor.

---

## Required Output Structure

### Learning Objectives
List 4–6 measurable learning objectives using Bloom's action verbs. These will drive alignment across all three modules.

---

### A) Knowledge Component

Cover all of the following for `{{TOPIC}}`:

1. **Motivation & Problem Statement**: Why does fine-tuning large models pose a challenge? What problem does LoRA solve?
2. **Core Mathematical Foundations**: 
   - The low-rank decomposition: ΔW = BA where B ∈ ℝ^{d×r}, A ∈ ℝ^{r×k}, rank r ≪ min(d,k)
   - Initialization strategy and the role of α scaling
   - Forward pass formulation: h = W₀x + (α/r)·BAx
   - Parameter count comparison: full fine-tuning vs. LoRA
3. **Algorithmic Description**: Step-by-step pseudocode for applying LoRA to a transformer model
4. **Comparison with Related Methods**: LoRA vs. full fine-tuning vs. adapter layers vs. prefix tuning vs. prompt tuning — include a comparison table with strengths, weaknesses, and when to use each
5. **Real-World Applications**: At least 3 concrete use cases with specific examples (e.g., domain adaptation of LLMs, image generation fine-tuning)

**Depth**: Each sub-section should be 150–300 words with equations where applicable.

---

### B) Skill Component

Cover all of the following:

1. **Step-by-Step Implementation Guide**: How to apply LoRA to a HuggingFace transformer model using the PEFT library
2. **Complete Code Example**: End-to-end workflow in Python — model loading → LoRA config → training → evaluation. Use `transformers` and `peft` libraries. Include version numbers.
3. **End-to-End Workflow**: Data preprocessing → LoRA fine-tuning → evaluation → saving/loading adapters
4. **Common Pitfalls & Debugging Tips**: At least 5 specific pitfalls with diagnosis and fix
5. **Hyperparameter Tuning**: Guidance on r (rank), α (scaling), target modules, dropout — with recommended ranges and search strategies

**Depth**: Code examples must be complete enough to run. Include comments explaining *why*, not just *what*.

---

### C) Ethical Implications & Values Component

Address all of the following **specifically for LoRA**, not generic AI ethics:

1. **Bias Amplification**: How LoRA fine-tuning on domain-specific data can amplify dataset biases; detection methods
2. **Privacy Concerns**: Risks of fine-tuning on sensitive/proprietary data; adapter leakage risks; membership inference attacks on LoRA adapters
3. **Societal Impact**: Who benefits (resource-constrained labs, multilingual NLP) and who may be harmed (e.g., enabling low-cost generation of harmful content, misuse for impersonation)
4. **Responsible AI Practices**: Specific recommendations for auditing LoRA-fine-tuned models
5. **Concrete Ethical Scenario**: A detailed case study — e.g., a company fine-tunes a medical LLM using LoRA on patient data without proper consent; analyze what went wrong and how to prevent it

**Constraint**: This section must be at least 400 words and must not use generic phrases like "AI can be biased" without tying them specifically to LoRA's mechanics.

---

## Quality Checklist (self-verify before output)
- [ ] All three components present and non-trivial
- [ ] Mathematical notation is consistent and correct
- [ ] Code is syntactically correct and uses real library APIs
- [ ] Ethics section is LoRA-specific, not generic
- [ ] Learning objectives use Bloom's action verbs
- [ ] Constructive alignment: objectives match content
