# Theory Assessment: Parameter Efficient Fine Tuning (LoRA)
**CSE 329: Machine Learning | Student ID: 2105066**

---

## Part I: Questions

---

**Q1. [Bloom's Level 1: Remember] | Action Verb: State**

State the LoRA forward pass formula for a modified weight layer, defining all symbols used.

---

**Q2. [Bloom's Level 1: Remember] | Action Verb: Identify**

Identify the three hyperparameters introduced by LoRA that do not exist in standard full fine-tuning, and state the typical value or range for each.

---

**Q3. [Bloom's Level 2: Understand] | Action Verb: Explain**

Explain why LoRA initializes matrix B to all zeros and matrix A with random Gaussian values, rather than the reverse. What would happen if B were initialized randomly and A were initialized to zero?

---

**Q4. [Bloom's Level 2: Understand] | Action Verb: Compare**

Compare LoRA and adapter layers as PEFT methods. Your answer should address: where additional parameters are inserted relative to the existing computation graph, the effect on inference latency, and the typical performance gap relative to full fine-tuning.

---

**Q5. [Bloom's Level 3: Apply] | Action Verb: Calculate**

A transformer model has query projection matrices of shape [1024 × 1024]. A practitioner applies LoRA with rank r = 16 to all query and value projections across 24 layers.

(a) Calculate the total number of LoRA trainable parameters introduced.  
(b) Calculate the percentage reduction in trainable parameters compared to full fine-tuning of only these layers.  
(c) If full fine-tuning uses the Adam optimizer (which stores 2 extra gradient moments per parameter), calculate the GPU memory saved (in MB, assume float32) by using LoRA for these layers only.

---

**Q6. [Bloom's Level 3: Apply] | Action Verb: Predict**

A practitioner is fine-tuning a 7B language model using LoRA on a code completion dataset with 2,000 training examples. They try two configurations:
- **Config A**: r = 64, α = 128, target all projection matrices (q, k, v, o, ffn up/down)
- **Config B**: r = 4, α = 8, target only q and v projections

Predict which configuration is more likely to overfit and explain the mechanism by which LoRA's rank constraint influences regularization.

---

**Q7. [Bloom's Level 4: Analyze] | Action Verb: Diagnose**

*[Novel Scenario]* A team fine-tunes Mistral-7B using LoRA (r=8, α=16, target: q,v) on a customer support chat dataset with 50,000 examples. The model achieves 93% accuracy on the in-distribution test set. However, when deployed, users report that the model consistently produces confident but incorrect responses when questions contain technical jargon not common in the training corpus.

Diagnose **two distinct root causes** for this failure mode that are specifically attributable to properties of LoRA (not generic model problems). For each, propose a targeted mitigation strategy.

---

**Q8. [Bloom's Level 4: Analyze] | Action Verb: Differentiate**

*[Novel Scenario]* Two ML engineers are arguing about where to apply LoRA in a vision-language model (VLM) that has three components: a vision encoder (ViT), a cross-attention bridge module, and a language decoder (LLM backbone). 

Engineer A argues LoRA should only target the language decoder's attention layers. Engineer B argues it should target all three components equally.

Differentiate between the two strategies by analyzing: (a) what each approach captures and ignores during adaptation, (b) which is more appropriate when the downstream task requires understanding novel visual concepts not in the pre-training data, and (c) parameter efficiency implications of each choice.

---

**Q9. [Bloom's Level 5: Evaluate] | Action Verb: Justify**

A startup with one A100 GPU (80GB VRAM) needs to adapt Llama-2-13B for a legal document summarization task. Their dataset has 8,000 labeled legal brief/summary pairs. They are deciding between:

- **Option 1**: Full fine-tuning using gradient checkpointing and 8-bit quantization
- **Option 2**: QLoRA (quantized LoRA, 4-bit base model + LoRA adapters)
- **Option 3**: LoRA (16-bit base model) — which may not even fit in memory

Justify a recommendation for one of the three options. Your answer must consider: memory feasibility, expected performance, training time, and risks specific to the legal domain.

---

**Q10. [Bloom's Level 5: Evaluate] | Action Verb: Critique**

*[Ethical Dimension]* A research group publishes a LoRA adapter trained on a curated dataset of persuasive political essays representing one ideological perspective. They justify this by arguing that LoRA's small parameter count means the adapter cannot have meaningfully encoded harmful biases.

Critique this justification. In your answer: (a) evaluate whether parameter count is a valid proxy for bias potential, (b) identify the specific property of LoRA fine-tuning that makes even low-rank adapters capable of significant behavioral shifts, and (c) recommend a concrete evaluation protocol the researchers should have conducted before releasing the adapter.

---

**Q11. [Bloom's Level 6: Create] | Action Verb: Design**

*[Novel Scenario]* You are building a multi-tenant NLP service that must serve a single base LLM (Llama-3-8B) across 50 enterprise clients, each requiring a customized model fine-tuned on their proprietary data (average dataset size: 5,000 examples per client). Clients have different tasks: some do summarization, some do classification, some do question answering.

Design a LoRA-based serving architecture that satisfies all of the following constraints:
- Maximum GPU memory usage: 40GB (one A100)
- Adapter switch latency: < 100ms
- Client data privacy: no client's data should influence another client's adapter
- Scalable to 50 concurrent clients

Your design must specify: how adapters are structured and stored, how the serving system handles concurrent requests, any modifications to standard LoRA needed for multi-task compatibility, and at least one failure mode of your design with a mitigation.

---

**Q12. [Bloom's Level 6: Create] | Action Verb: Propose**

LoRA's low-rank constraint assumes that the useful fine-tuning signal occupies a low-dimensional subspace of the weight space. However, recent research suggests this assumption may break down for tasks that require large distributional shifts from the pre-training data (e.g., adapting an English LLM to a morphologically complex low-resource language).

Propose a modification or extension to the standard LoRA algorithm that addresses this limitation. Your proposal must: (a) identify the specific mathematical or algorithmic property of LoRA you are modifying and why it is insufficient, (b) describe your proposed change with enough mathematical detail that a peer researcher could implement it, and (c) describe an experiment to empirically validate whether your modification outperforms standard LoRA on the identified failure case.

---

## Part II: Complete Answer Key

---

**Answer Key — Q1**

**Model Answer**: The LoRA forward pass formula is:

```
h = W₀x + (α / r) · B · A · x
```

where W₀ ∈ ℝ^{d×k} is the frozen pre-trained weight matrix; x ∈ ℝ^k is the input; A ∈ ℝ^{r×k} is the down-projection adapter matrix (trainable); B ∈ ℝ^{d×r} is the up-projection adapter matrix (trainable); r is the rank (r ≪ min(d,k)); α is the scaling hyperparameter; and h ∈ ℝ^d is the output.

**Marking Scheme**:
- Correct formula structure with both W₀x and LoRA branch: 2 marks
- Correct placement of α/r scaling factor: 1 mark
- Correct matrix shapes for A and B (with r dimension): 1 mark
- Definition of all 6 symbols: 1 mark (0.5 if 4–5 symbols defined)

**Expected Response Depth**: A full-mark answer writes the formula exactly, defines every symbol with its type/shape, and correctly shows the scaling. Partial credit (3/5) if formula is correct but variable definitions are incomplete or shapes are wrong.

---

**Answer Key — Q2**

**Model Answer**: The three LoRA-specific hyperparameters are: (1) **r (rank)** — the rank of the low-rank decomposition; typical range 4–64, commonly 8 or 16; (2) **α (alpha)** — the scaling factor applied as α/r; typically set to r or 2r (e.g., α=16 for r=8); (3) **target_modules** — which weight matrices receive adapters; typically query/value projections (q_proj, v_proj), though this varies by model architecture.

**Marking Scheme**:
- r correctly named and typical range stated: 1 mark
- α correctly named and relationship to r stated: 1 mark
- target_modules correctly named with examples: 1 mark
- Partial credit: 0.5 per hyperparameter if named but no value/range given

**Expected Response Depth**: A full-mark answer names all three, gives typical values, and explains the role of each in one sentence.

---

**Answer Key — Q3**

**Model Answer**: B is initialized to zero so that ΔW = BA = 0 at the start of training. This ensures the fine-tuned model's behavior is identical to the pre-trained model at initialization — the LoRA branch contributes nothing. This preserves the pre-trained representations and gives a stable starting point. A is initialized randomly to break symmetry: if both A and B were zero, the gradients flowing through BA would be identically zero for all elements (since ∂L/∂A ∝ Bᵀ = 0), and the adapter would never learn. If the initialization were reversed (A=0, B random), the same dead-gradient problem would occur in the first step.

**Marking Scheme**:
- Explains ΔW=0 at init due to B=0, and why this is desirable: 2 marks
- Correctly identifies the dead-gradient problem for the reverse case: 2 marks
- Mentions A random initialization to break symmetry: 1 mark

**Expected Response Depth**: Full marks require both the positive justification (stable init) and the negative justification (what goes wrong in reverse). A partial answer (3/5) that only explains the positive case is insufficient.

---

**Answer Key — Q4**

**Model Answer**: **Insertion point**: LoRA adds parallel branches alongside existing weight matrices (additive, not sequential). Adapter layers are inserted *serially* between the attention sub-layer and the feed-forward sub-layer, adding two new linear projections in the main computation path. **Inference latency**: LoRA adds zero latency when weights are merged (W_merged = W₀ + α/r·BA replaces W₀). Adapters add ~15–30% latency due to the extra sequential linear operations. **Performance gap**: Both achieve within 1–3% of full fine-tuning on most benchmarks; adapters may edge out LoRA in some few-shot settings due to their non-linear activation (some adapter designs include a nonlinearity between the two projections).

**Marking Scheme**:
- Correct insertion point for each method: 2 marks (1 each)
- Correct inference latency comparison (LoRA zero when merged, adapters +latency): 2 marks
- Reasonable performance gap comparison: 1 mark

---

**Answer Key — Q5**

**Model Answer**:

**(a) LoRA parameters introduced:**
Each LoRA adapter for a [1024×1024] projection with r=16:
- A: r×k = 16×1024 = 16,384 params
- B: d×r = 1024×16 = 16,384 params
- Per projection: 32,768 params
- Per layer (q + v): 2 × 32,768 = 65,536 params
- Total (24 layers): 24 × 65,536 = **1,572,864 params ≈ 1.57M**

**(b) Full FT params for these layers:**
Per layer (q + v): 2 × 1024 × 1024 = 2,097,152
Total: 24 × 2,097,152 = 50,331,648 ≈ 50.3M
Reduction: (50.3M − 1.57M) / 50.3M = **96.9% reduction**

**(c) Adam memory saving:**
Full FT needs 3× params in memory (params + 2 moment copies) × 4 bytes:
Full FT memory: 50.3M × 3 × 4 = 603.6 MB
LoRA memory: 1.57M × 3 × 4 = 18.8 MB  
**Saving: 584.8 MB ≈ 585 MB** (note: base model weights still loaded frozen, but no gradient storage)

**Marking Scheme**:
- Part (a) correct calculation with working shown: 3 marks (1 for per-projection, 1 for per-layer, 1 for total)
- Part (b) correct reduction percentage with working: 2 marks
- Part (c) correct memory calculation with Adam multiplier: 2 marks (1 if right approach but arithmetic error)
- Partial credit: 50% for correct formula but wrong final number

---

**Answer Key — Q6**

**Model Answer**: **Config A is far more likely to overfit.** Config A has effective rank 64 across all projection types — a very high-capacity adapter relative to 2,000 examples. Even though LoRA's total parameter count is smaller than full fine-tuning, its *effective degrees of freedom* scale with r × (number of target matrices). Config A with 6 target module types and r=64 has roughly 6× the capacity of Config B.

**Mechanism**: LoRA's rank constraint acts as a regularizer by restricting the fine-tuning update to a low-dimensional subspace of the weight space. A high-rank adapter can fit a larger portion of the training data's idiosyncrasies — including noise — because it has more "directions" in which to adjust. With only 2,000 examples, there is insufficient signal to usefully populate a rank-64 subspace; the adapter will fill the unused dimensions with noise-fitting. Config B's r=4 severely constrains the adapter, forcing it to capture only the most statistically robust patterns in the data.

**Marking Scheme**:
- Correctly identifies Config A as the overfitter: 1 mark
- Explains rank as effective regularizer (subspace analogy): 2 marks
- Quantifies the difference in capacity (r × target modules): 1 mark
- Mentions the 2,000 example count as insufficient for high-rank adapters: 1 mark

---

**Answer Key — Q7**

**Model Answer**:

**Root Cause 1: LoRA adapts only a low-rank subspace, leaving out-of-distribution directions unmodified**. LoRA's rank-8 constraint means only 8 orthogonal directions in the weight space are adapted. Technical jargon in user queries likely activates representational directions not spanned by these 8 directions — the model's response to such inputs is determined entirely by the frozen W₀, which was not optimized for the target task. **Mitigation**: Increase rank (r=16 or r=32) to capture more task-relevant directions, or add target modules beyond q,v (e.g., include the feed-forward layers that process semantic content).

**Root Cause 2: LoRA does not update the base model's confidence calibration (embedding or head layers)**. The classification/generation head is typically not a target module in standard LoRA. When the model encounters OOD inputs (novel technical jargon), the attention mechanisms may still produce high-confidence representations — the LoRA adapter cannot correct overconfidence because it only modifies mid-layer projections. **Mitigation**: Add the output projection or the language model head as additional LoRA target modules, or apply temperature scaling post-hoc to calibrate output probabilities.

**Marking Scheme**:
- Two distinct, LoRA-specific root causes (not generic overfitting/data quality): 4 marks (2 each)
- Each mitigation is targeted and implementable: 2 marks (1 each)
- Partial credit (1 mark per cause): If cause is valid but not clearly tied to LoRA mechanics

---

**Answer Key — Q8**

**Model Answer**:

**(a) Engineer A** (language decoder only) assumes the vision encoder's representations are already sufficient for the task and that only the language generation/reasoning component needs adaptation. This ignores the possibility that the downstream task requires the model to perceive novel visual features. **Engineer B** (all components) adapts the full VLM to the task but uses more parameters and risks adapting well-trained visual encoders away from their general representations.

**(b) For novel visual concepts**: Engineer B's approach is more appropriate. Novel visual concepts (e.g., a medical imaging task where the VLM was pre-trained on natural images) require the vision encoder to learn new feature representations. If only the language decoder is adapted, the model cannot develop new visual representations — the encoder remains fixed on natural image features, and the language decoder cannot compensate for inadequate visual encoding.

**(c) Parameter efficiency**: Engineer A uses ~2× fewer parameters. For Engineer B, applying LoRA to the ViT (which may have fewer attention layers) adds modest cost, but the cross-attention bridge is disproportionately important and likely high-value to adapt. A principled middle ground: adapt ViT + cross-attention (not all three) for visual tasks.

**Marking Scheme**:
- Correct characterization of both strategies: 2 marks
- Correct recommendation for novel visual concepts with justification: 2 marks
- Parameter efficiency analysis: 1 mark

---

**Answer Key — Q9**

**Model Answer**: **Recommendation: QLoRA (Option 2).**

**Memory feasibility**: Llama-2-13B in float16 requires ~26GB VRAM. Adam optimizer states for full fine-tuning add 2× params × 2 bytes = ~52GB — infeasible on 80GB with gradient checkpointing overhead. QLoRA loads the base model in 4-bit NF4 (~7GB) plus adapter parameters (~50MB) plus optimizer states for adapters only (~150MB), fitting comfortably in 40GB with headroom.

**Expected performance**: QLoRA achieves within 1–2% of full fine-tuning on most NLP benchmarks (Dettmers et al., 2023). For 8,000 legal examples, the risk is that standard LoRA at 16-bit would fit (using gradient checkpointing, ~60–70GB) but is borderline. QLoRA is the safer choice.

**Legal domain risks**: Legal summarization requires precision. The 4-bit quantization of QLoRA introduces small representational errors; for critical legal terms, spot-check outputs against ground truth summaries. Fine-tuning on legal data may also introduce jurisdiction-specific biases — a validation set spanning multiple jurisdictions should be used.

**Marking Scheme**:
- Correct recommendation with memory calculation: 3 marks
- Performance expectations cited: 1 mark
- Legal domain risk mentioned: 1 mark
- Partial credit (2/5): Correct recommendation but no memory analysis

---

**Answer Key — Q10**

**Model Answer**:

**(a) Parameter count is not a valid proxy for bias potential.** Bias is a function of the *direction* of weight updates, not their magnitude or count. Even a rank-1 LoRA update (the minimum possible — 2 vectors) can, in theory, shift the model's output distribution arbitrarily along that one dimension. A model fine-tuned on entirely one-sided political essays will learn to strongly associate certain vocabulary and framing patterns with high probability regardless of the adapter's rank.

**(b) Behavioral shift mechanism**: LoRA fine-tuning concentrates its learning signal into r orthogonal directions. These directions are precisely the axes most relevant to the fine-tuning corpus. With a politically biased corpus, the adapter will align its r principal directions with features that distinguish the ideological perspective, producing *concentrated* rather than *diffuse* bias — arguably more problematic than a full fine-tuning's spread across all parameters.

**(c) Evaluation protocol**: (1) Collect a balanced political opinion probe set spanning multiple ideological perspectives; (2) measure the model's output probability distribution for equivalent prompts framed from different perspectives; (3) compare to the base model's outputs — significant divergence indicates the adapter has introduced directional bias; (4) use embedding space analysis to visualize whether the adapter's principal directions align with ideological feature directions in the representation space.

**Marking Scheme**:
- Correctly rejects parameter count as proxy with valid reasoning: 2 marks
- Correctly identifies concentration of LoRA's learning directions as the bias mechanism: 2 marks
- Concrete, implementable evaluation protocol: 1 mark

---

**Answer Key — Q11**

**Model Answer**: 

**Architecture design**:
- Load the base Llama-3-8B in 8-bit quantization (~10GB) — shared across all 50 clients
- Each client's LoRA adapter is stored on disk (~16MB per client, 50 clients = ~800MB total on disk)
- Maintain a GPU adapter cache of the N most recently used adapters (e.g., top 10 = ~160MB)

**Serving system**:
- Use a request router that identifies the client ID and loads/unloads the appropriate adapter
- Adapter switching: loading a LoRA adapter from CPU RAM to GPU takes ~20–50ms — within the 100ms budget
- Use adapter hot-caching with LRU eviction for the top-N active clients to minimize switching latency

**Multi-task compatibility**: Use task-specific LoRA with separate adapters per task type (no weight sharing between summarization/classification/QA adapters). Optionally, use MixLoRA or LoRAHub for clients that need multi-task composition.

**Privacy**: Each adapter is trained in isolation on the respective client's data only. Adapters are stored in client-specific encrypted storage with no cross-client access.

**Failure mode**: If 50 clients issue requests simultaneously, the system must context-switch between adapters frequently. Mitigation: implement request batching by client — group requests from the same client and process them together, reducing switch frequency.

**Marking Scheme**:
- Memory-feasible architecture (base model + adapters fit in 40GB): 2 marks
- Sub-100ms adapter switch mechanism with explanation: 2 marks
- Privacy isolation design: 1 mark
- Failure mode identified with mitigation: 1 mark
- Partial credit: 3/6 if design is conceptually correct but infeasible for one constraint

---

**Answer Key — Q12**

**Model Answer**:

**(a) Limitation identified**: Standard LoRA assumes the fine-tuning signal lies in a *fixed, low-rank subspace* of a specific weight matrix. For large distributional shifts (e.g., English → morphologically rich language), the relevant update may require capturing interactions across *multiple* weight matrices simultaneously, and the effective rank may be much higher than what is efficient to specify via a single (A, B) pair per layer.

**(b) Proposed modification — AdaptiveLoRA with Dynamic Rank**: Instead of a fixed rank r, start with r=1 and iteratively grow the adapter by adding new (aᵢ, bᵢ) vector pairs during training when the current adapter's training loss gradient has significant components orthogonal to the existing adapter subspace. Formally: after each epoch, compute the residual gradient G_residual = ∇L - proj_{BA}(∇L), where proj_{BA} is the projection onto the column space of BA. If ||G_residual|| / ||∇L|| > threshold τ, add a new rank-1 component: A_new = [A; aᵢ], B_new = [B, bᵢ] where aᵢ is the top left singular vector of G_residual and bᵢ = 0 (same init as standard LoRA). This grows the adapter only where the fixed-rank assumption fails.

**(c) Experiment**: Baseline: standard LoRA (r=8) fine-tuning of LLaMA-2-7B on a Finnish or Hungarian NLP benchmark (high morphological complexity). Proposed: AdaptiveLoRA initialized at r=1 with τ=0.1, growing to a maximum of r_max=32. Evaluation: test set perplexity and downstream task accuracy (e.g., POS tagging, NER). If AdaptiveLoRA achieves significantly lower perplexity with fewer or equal total parameters, the modification is validated.

**Marking Scheme**:
- Correctly identifies fixed-rank assumption as the limitation: 2 marks
- Mathematically grounded proposal (not just vague "increase r"): 3 marks
- Experimentally falsifiable validation design: 2 marks
- Partial credit: 4/7 if proposal is well-motivated but mathematical detail is insufficient
