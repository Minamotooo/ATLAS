"""
CSE 329: Machine Learning — Coding Assessment (INSTRUCTOR SOLUTION)
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

Dataset: SST-2 (Stanford Sentiment Treebank, binary sentiment) via HuggingFace datasets
Task:    Binary sentiment classification using LoRA fine-tuned DistilBERT

Run:     python coding_solution.py

Performance Benchmarks (CPU only, no GPU required):
    Training time:  ~20–30 min on modern CPU (3 epochs, full SST-2 train split)
    Val accuracy:   ~90–92% after 3 epochs
    Val loss:       ~0.22–0.28 after 3 epochs
    Val F1 (macro): ~0.90–0.92 after 3 epochs
    Hardware:       Tested on Intel Core i7 / Apple M2, 16GB RAM, no GPU

Expected output after T2 (print_trainable_parameters):
    trainable params: 296,450 || all params: 66,955,010 || trainable%: 0.44

NOTE: This is the instructor reference solution. Do not distribute to students.
"""

# ============================================================
# IMPORTS — DO NOT MODIFY
# ============================================================
import sys
import os
import time
import random
import logging
import importlib.metadata
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

def _check_version(package: str, required: str) -> None:
    try:
        installed = importlib.metadata.version(package)
        if installed != required:
            print(f"WARNING: {package} version {installed} found, {required} expected.")
    except importlib.metadata.PackageNotFoundError:
        print(f"ERROR: {package} is not installed. Run: pip install {package}=={required}")
        sys.exit(1)

_check_version("torch",         "2.1.0")
_check_version("transformers",  "4.38.0")
_check_version("peft",          "0.9.0")
_check_version("datasets",      "2.18.0")
_check_version("scikit-learn",  "1.4.0")
_check_version("matplotlib",    "3.8.0")

import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LinearLR
from torch.utils.data import DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
)
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from datasets import load_dataset
from sklearn.metrics import accuracy_score, f1_score

# ============================================================
# CONFIG — DO NOT MODIFY
# ============================================================
MODEL_NAME              = "distilbert-base-uncased"
DATASET_NAME            = "sst2"
DATASET_CONFIG          = "sst2"
NUM_LABELS              = 2
MAX_SEQ_LEN             = 128

LORA_R                  = 8
LORA_ALPHA              = 16
LORA_DROPOUT            = 0.1
LORA_TARGET_MODULES     = ["q_lin", "v_lin"]
LORA_BIAS               = "none"
LORA_TASK_TYPE          = TaskType.SEQ_CLS

BATCH_SIZE              = 16
LEARNING_RATE           = 3e-4
NUM_EPOCHS              = 3
WEIGHT_DECAY            = 0.01
MAX_GRAD_NORM           = 1.0
WARMUP_RATIO            = 0.1
SEED                    = 42

OUTPUT_DIR              = Path("./lora_sst2_output")
ADAPTER_DIR             = OUTPUT_DIR / "adapter"
MERGED_DIR              = OUTPUT_DIR / "merged_model"
LOG_DIR                 = OUTPUT_DIR / "logs"

LOG_INTERVAL            = 50

# ============================================================
# SETUP — DO NOT MODIFY
# ============================================================
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(SEED)
for d in [OUTPUT_DIR, ADAPTER_DIR, MERGED_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "training.log"),
    ],
)
logger = logging.getLogger(__name__)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {DEVICE}")

# ============================================================
# DATA LOADING & PREPROCESSING — DO NOT MODIFY
# ============================================================
def load_and_preprocess_data(model_name, dataset_name, dataset_config,
                              max_seq_len, batch_size):
    logger.info(f"Loading dataset: {dataset_name} ({dataset_config})")
    raw_dataset = load_dataset("glue", dataset_config)
    tokenizer   = AutoTokenizer.from_pretrained(model_name)

    def tokenize_function(examples):
        return tokenizer(examples["sentence"], truncation=True, max_length=max_seq_len)

    tokenized_dataset = raw_dataset.map(tokenize_function, batched=True, desc="Tokenizing")
    tokenized_dataset = tokenized_dataset.rename_column("label", "labels")
    tokenized_dataset.set_format(type="torch",
                                  columns=["input_ids", "attention_mask", "labels"])

    collator    = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")
    train_loader = DataLoader(tokenized_dataset["train"],   batch_size=batch_size,
                               shuffle=True, collate_fn=collator)
    val_loader   = DataLoader(tokenized_dataset["validation"], batch_size=batch_size,
                               shuffle=False, collate_fn=collator)

    logger.info(f"Train: {len(tokenized_dataset['train'])} | "
                f"Val: {len(tokenized_dataset['validation'])}")
    return train_loader, val_loader, tokenizer

# ============================================================
# UTILITIES — DO NOT MODIFY
# ============================================================
def log_metrics(step, metrics, split="train"):
    metric_str = " | ".join(f"{k}: {v:.4f}" for k, v in metrics.items())
    logger.info(f"[Step {step:5d}] [{split.upper():5s}] {metric_str}")

def plot_training_curve(train_losses, val_losses, val_accuracies, save_path):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(train_losses, label="Train Loss", color="steelblue")
    axes[0].plot(
        [i * (len(train_losses) // max(len(val_losses), 1)) for i in range(len(val_losses))],
        val_losses, label="Val Loss", color="tomato", marker="o",
    )
    axes[0].set_title("Loss Curve"); axes[0].set_xlabel("Step")
    axes[0].set_ylabel("Loss"); axes[0].legend()
    axes[1].plot(val_accuracies, color="seagreen", marker="o", label="Val Accuracy")
    axes[1].set_title("Validation Accuracy"); axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy"); axes[1].legend()
    plt.tight_layout(); plt.savefig(save_path, dpi=120); plt.close()
    logger.info(f"Training curve saved to {save_path}")

# ============================================================
# VALIDATION HARNESS — DO NOT MODIFY
# ============================================================
def validate_lora_config(model):
    trainable_params = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    frozen_params    = [(n, p) for n, p in model.named_parameters() if not p.requires_grad]
    lora_names = [n for n, _ in trainable_params if "lora_" in n]
    assert len(lora_names) > 0, "VALIDATION FAILED: No LoRA parameters found."
    base_trainable = [n for n, _ in trainable_params if "lora_" not in n]
    assert len(base_trainable) == 0, f"VALIDATION FAILED: Base weights not frozen: {base_trainable[:3]}"
    total_trainable = sum(p.numel() for _, p in trainable_params)
    assert 100_000 < total_trainable < 2_000_000, \
        f"VALIDATION FAILED: Trainable count {total_trainable:,} out of range."
    logger.info("✓ validate_lora_config PASSED")
    logger.info(f"  Trainable: {total_trainable:,} | Frozen: {sum(p.numel() for _, p in frozen_params):,}")
    return True

def validate_model_output(model, tokenizer):
    model.eval()
    with torch.no_grad():
        dummy = tokenizer("This film was absolutely wonderful!", return_tensors="pt",
                           truncation=True, max_length=MAX_SEQ_LEN).to(DEVICE)
        outputs = model(**dummy)
        logits  = outputs.logits
    assert logits.shape == (1, NUM_LABELS), f"VALIDATION FAILED: Got {logits.shape}"
    probs = torch.softmax(logits, dim=-1)
    assert abs(probs.sum().item() - 1.0) < 1e-4, "VALIDATION FAILED: Probs don't sum to 1."
    logger.info(f"✓ validate_model_output PASSED | logits: {logits.cpu().numpy()}")
    return True

# ============================================================
# SOLUTION: T1 — Build LoRA Configuration
# ============================================================
def build_lora_config() -> LoraConfig:
    # APPROACH: LoraConfig is the central specification object for the PEFT library.
    # We set task_type=SEQ_CLS to tell PEFT we are doing sequence classification —
    # this determines how the model's output head is handled during training.
    # r=LORA_R controls the rank: higher rank = more expressive adapter but more params.
    # lora_alpha=LORA_ALPHA is the scaling factor; with alpha=16, r=8, the update is
    # scaled by 16/8 = 2.0, effectively doubling the magnitude of the LoRA gradient signal
    # relative to if we set alpha=r=8 (scale=1.0). This is a common setting.
    # target_modules=["q_lin", "v_lin"] targets only the query and value projections —
    # empirically, adapting Q and V captures most of the task-specific attention behavior
    # while Q and K together with V can improve further at the cost of more parameters.
    # bias="none" means bias terms are not modified — this is the standard setting.
    config = LoraConfig(
        task_type=LORA_TASK_TYPE,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=LORA_TARGET_MODULES,
        lora_dropout=LORA_DROPOUT,
        bias=LORA_BIAS,
        inference_mode=False,       # Must be False during training
    )
    logger.info(f"LoRA config built: r={LORA_R}, alpha={LORA_ALPHA}, "
                f"targets={LORA_TARGET_MODULES}")
    return config

# ============================================================
# SOLUTION: T2 — Apply LoRA to Base Model
# ============================================================
def apply_lora_to_model(base_model, lora_config: LoraConfig):
    # APPROACH: get_peft_model() does three things automatically:
    #   1. Identifies target modules by name (q_lin, v_lin in DistilBERT)
    #   2. Replaces each target nn.Linear with a LoraLayer wrapper that adds
    #      trainable A and B matrices while keeping W₀ frozen
    #   3. Freezes all non-LoRA parameters (requires_grad = False)
    # We call print_trainable_parameters() to verify the parameter count.
    # Expected: ~296,450 trainable out of ~66,955,010 total (0.44%)
    # Moving to DEVICE after wrapping ensures the LoRA matrices are also on device.
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()
    # Expected output:
    # trainable params: 296,450 || all params: 66,955,010 || trainable%: 0.44
    model = model.to(DEVICE)
    validate_lora_config(model)
    return model

# ============================================================
# SOLUTION: T3 — Single Training Step
# ============================================================
def training_step(model, batch: dict, optimizer: AdamW,
                  scheduler, loss_fn: nn.CrossEntropyLoss) -> float:
    # APPROACH: Standard supervised learning step for a HuggingFace model.
    # Key detail: HuggingFace models return a ModelOutput (not a raw tensor),
    # so we access outputs.logits explicitly.
    # Gradient clipping (MAX_GRAD_NORM=1.0) is important because LoRA updates
    # are concentrated in a small number of parameters — without clipping, a
    # single bad batch can cause a large gradient spike in the adapter parameters.
    # The scheduler step is called every training step (not every epoch) since
    # we use a LinearLR warmup scheduler with total_iters=warmup_steps.
    model.train()
    optimizer.zero_grad()

    # Move entire batch to device
    batch = {k: v.to(DEVICE) for k, v in batch.items()}
    labels = batch.pop("labels")                # Extract labels before forward pass

    # Forward pass — PEFT model applies W₀x + (α/r)·BAx transparently
    outputs = model(**batch)
    logits  = outputs.logits                    # Shape: [batch_size, num_labels]

    # Compute cross-entropy loss
    loss = loss_fn(logits, labels)

    # Backward pass
    loss.backward()

    # Gradient clipping — prevents instability in adapter params
    torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)

    # Update only trainable (LoRA) parameters
    optimizer.step()
    scheduler.step()

    return loss.item()

# ============================================================
# SOLUTION: T4 — Evaluation Loop
# ============================================================
def evaluation_loop(model, val_loader: DataLoader) -> dict:
    # APPROACH: Disable gradient computation entirely during evaluation using
    # torch.no_grad() — this saves memory and computation since we don't need
    # gradient tracking for inference.
    # We accumulate predictions and labels as lists across all batches, then
    # concatenate and compute metrics. We compute both accuracy and macro F1
    # to get a fuller picture of model performance on SST-2 (balanced classes).
    # Expected after 3 epochs: val_accuracy ≈ 0.90–0.92, val_loss ≈ 0.22–0.28
    model.eval()
    loss_fn         = nn.CrossEntropyLoss()
    all_logits      = []
    all_labels      = []
    total_loss      = 0.0
    num_batches     = 0

    with torch.no_grad():
        for batch in val_loader:
            batch  = {k: v.to(DEVICE) for k, v in batch.items()}
            labels = batch.pop("labels")

            outputs     = model(**batch)
            logits      = outputs.logits        # [batch_size, 2]
            batch_loss  = loss_fn(logits, labels)

            total_loss  += batch_loss.item()
            num_batches += 1
            all_logits.append(logits.cpu())
            all_labels.append(labels.cpu())

    # Concatenate across batches
    all_logits = torch.cat(all_logits, dim=0)   # [N, 2]
    all_labels = torch.cat(all_labels, dim=0)   # [N]

    # Convert logits to predictions
    predictions = torch.argmax(all_logits, dim=-1).numpy()
    labels_np   = all_labels.numpy()

    metrics = {
        "val_loss":     total_loss / num_batches,
        "val_accuracy": accuracy_score(labels_np, predictions),
        "val_f1":       f1_score(labels_np, predictions, average="macro"),
    }
    return metrics

# ============================================================
# SOLUTION: T5 — Parameter Efficiency Analysis
# ============================================================
def compute_parameter_efficiency(model) -> dict:
    # APPROACH: Iterate over all named parameters, separate trainable (LoRA)
    # from frozen (base model). Calculate memory for both cases assuming float32
    # (4 bytes per param). For the Adam optimizer comparison, multiply by 3 to
    # account for: (1) the parameter itself, (2) first moment (momentum), and
    # (3) second moment (RMSprop-style variance estimate). This 3× factor applies
    # to trainable parameters only — frozen params don't need gradient storage.
    # Expected: ~0.44% trainable, ~584MB saved in Adam states vs. full FT.
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params    = sum(p.numel() for p in model.parameters() if not p.requires_grad)
    total_params     = trainable_params + frozen_params
    trainable_pct    = 100.0 * trainable_params / total_params

    bytes_per_param  = 4                         # float32
    mb               = 1024 * 1024

    # LoRA memory: only adapter params need optimizer states
    lora_memory_mb   = (trainable_params * 3 * bytes_per_param) / mb

    # Full FT would need optimizer states for ALL parameters
    full_ft_memory_mb = (total_params * 3 * bytes_per_param) / mb

    memory_saving_pct = 100.0 * (full_ft_memory_mb - lora_memory_mb) / full_ft_memory_mb

    stats = {
        "total_params":       total_params,
        "trainable_params":   trainable_params,
        "frozen_params":      frozen_params,
        "trainable_pct":      trainable_pct,
        "lora_memory_mb":     lora_memory_mb,
        "full_ft_memory_mb":  full_ft_memory_mb,
        "memory_saving_pct":  memory_saving_pct,
    }

    # Print formatted summary
    print("\n" + "="*55)
    print("  Parameter Efficiency Summary")
    print("="*55)
    print(f"  {'Total parameters:':<30} {total_params:>12,}")
    print(f"  {'Trainable (LoRA):':<30} {trainable_params:>12,}")
    print(f"  {'Frozen (base model):':<30} {frozen_params:>12,}")
    print(f"  {'Trainable percentage:':<30} {trainable_pct:>11.2f}%")
    print(f"  {'LoRA Adam memory (MB):':<30} {lora_memory_mb:>11.1f}")
    print(f"  {'Full FT Adam memory (MB):':<30} {full_ft_memory_mb:>11.1f}")
    print(f"  {'Memory saving:':<30} {memory_saving_pct:>11.1f}%")
    print("="*55 + "\n")

    return stats

# ============================================================
# SOLUTION: T6 — Merge LoRA Weights and Export
# ============================================================
def merge_and_export(model, output_path: Path) -> None:
    # APPROACH: merge_and_unload() performs the mathematical merge:
    #   W_merged = W₀ + (α / r) * B @ A
    # for each LoRA-targeted layer, replacing W₀ in-place and discarding A, B.
    # The result is a standard HuggingFace model with NO PEFT wrappers — it can
    # be loaded and used without the peft library at inference time.
    # WHY MERGE: A PEFT model routes input through W₀x + (α/r)·BAx separately
    # (two matrix multiplications per layer). The merged model collapses this to
    # a single W_merged·x — identical mathematically, but ~2× fewer FLOPs per
    # target layer. For production deployments where latency matters, merging
    # eliminates the LoRA overhead entirely.
    # We save both the merged model AND the tokenizer so the output directory
    # is fully self-contained — anyone can load it with from_pretrained() alone.
    logger.info("Merging LoRA weights into base model...")

    # Merge adapter weights into base model
    merged_model = model.merge_and_unload()
    # Expected: merged_model is now a plain DistilBertForSequenceClassification
    # with adapted weights baked into q_lin and v_lin of each layer

    # Save merged model (no PEFT dependency needed to load)
    merged_model.save_pretrained(str(output_path))
    logger.info(f"Merged model saved to {output_path}")

    # Save tokenizer alongside — makes the directory a complete standalone artifact
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.save_pretrained(str(output_path))
    logger.info(f"Tokenizer saved to {output_path}")

    # Log the expected contents
    logger.info("Merged model directory contents:")
    for f in sorted(output_path.iterdir()):
        logger.info(f"  {f.name} ({f.stat().st_size / 1024:.1f} KB)")

# ============================================================
# MAIN ENTRY POINT — DO NOT MODIFY
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("CSE 329 — LoRA Fine-Tuning (INSTRUCTOR SOLUTION)")
    logger.info(f"Student ID: 2105066 | Model: {MODEL_NAME}")
    logger.info("=" * 60)

    train_loader, val_loader, tokenizer = load_and_preprocess_data(
        MODEL_NAME, DATASET_NAME, DATASET_CONFIG, MAX_SEQ_LEN, BATCH_SIZE
    )

    lora_config = build_lora_config()
    base_model  = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=NUM_LABELS
    )
    model = apply_lora_to_model(base_model, lora_config)
    validate_model_output(model, tokenizer)

    efficiency_stats = compute_parameter_efficiency(model)
    # Expected output:
    # Trainable percentage: 0.44% | Memory saving: 99.6%

    optimizer   = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY,
    )
    total_steps = len(train_loader) * NUM_EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler   = LinearLR(optimizer, start_factor=0.1, end_factor=1.0,
                            total_iters=warmup_steps)
    loss_fn     = nn.CrossEntropyLoss()

    train_losses, val_losses, val_accuracies = [], [], []
    global_step = 0
    start_time  = time.time()

    for epoch in range(1, NUM_EPOCHS + 1):
        logger.info(f"\n{'─'*40}\nEpoch {epoch}/{NUM_EPOCHS}\n{'─'*40}")

        for batch in train_loader:
            loss = training_step(model, batch, optimizer, scheduler, loss_fn)
            train_losses.append(loss)
            global_step += 1
            if global_step % LOG_INTERVAL == 0:
                log_metrics(global_step, {"loss": loss}, split="train")

        val_metrics = evaluation_loop(model, val_loader)
        val_losses.append(val_metrics["val_loss"])
        val_accuracies.append(val_metrics["val_accuracy"])
        log_metrics(global_step, val_metrics, split="val")

    elapsed = time.time() - start_time
    logger.info(f"\nTraining complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    # Expected benchmark: ~20–30 min on CPU, ~3–5 min on A100 GPU

    model.save_pretrained(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    logger.info(f"Adapter saved to {ADAPTER_DIR}")

    plot_training_curve(train_losses, val_losses, val_accuracies,
                         save_path=LOG_DIR / "training_curve.png")

    merge_and_export(model, MERGED_DIR)
    # Expected: MERGED_DIR contains config.json, pytorch_model.bin/model.safetensors,
    #           tokenizer.json, tokenizer_config.json, vocab.txt
    # File size: ~263MB (full DistilBERT weights, merged)

    logger.info("=" * 60)
    logger.info(f"Final val accuracy: {val_accuracies[-1]:.4f}")
    logger.info(f"Final val loss:     {val_losses[-1]:.4f}")
    logger.info("All deliverables saved. Instructor solution complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
