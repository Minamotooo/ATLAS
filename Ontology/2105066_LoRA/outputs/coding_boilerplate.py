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

Dataset: SST-2 (Stanford Sentiment Treebank, binary sentiment) via HuggingFace datasets
Task:    Binary sentiment classification using LoRA fine-tuned DistilBERT

Run:     python coding_boilerplate.py

NOTE TO STUDENTS:
    - DO NOT modify any code outside of the TODO sections.
    - DO NOT remove the `raise NotImplementedError(...)` lines until you have
      implemented the corresponding TODO.
    - Use the validation harness functions (validate_lora_config,
      validate_model_output) after completing each TODO to check your work.
    - ALL hyperparameters are defined in the CONFIG block below.
      DO NOT use magic numbers anywhere in your implementation.
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

# Version checks
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
# CONFIG — DO NOT MODIFY (no magic numbers beyond this block)
# ============================================================
MODEL_NAME              = "distilbert-base-uncased"
DATASET_NAME            = "sst2"                  # HuggingFace GLUE benchmark
DATASET_CONFIG          = "sst2"
NUM_LABELS              = 2                        # Positive / Negative
MAX_SEQ_LEN             = 128                      # Truncate/pad sequences to this length

# LoRA hyperparameters
LORA_R                  = 8                        # Rank of the low-rank decomposition
LORA_ALPHA              = 16                       # Scaling factor (α = 2r rule of thumb)
LORA_DROPOUT            = 0.1                      # Dropout in the LoRA branch
LORA_TARGET_MODULES     = ["q_lin", "v_lin"]       # DistilBERT query/value projections
LORA_BIAS               = "none"                   # Do not adapt bias terms
LORA_TASK_TYPE          = TaskType.SEQ_CLS

# Training hyperparameters
BATCH_SIZE              = 16
LEARNING_RATE           = 3e-4                     # LoRA tolerates higher LR than full FT
NUM_EPOCHS              = 3
WEIGHT_DECAY            = 0.01
MAX_GRAD_NORM           = 1.0                      # Gradient clipping threshold
WARMUP_RATIO            = 0.1                      # Fraction of steps for LR warmup
SEED                    = 42

# Paths
OUTPUT_DIR              = Path("./lora_sst2_output")
ADAPTER_DIR             = OUTPUT_DIR / "adapter"
MERGED_DIR              = OUTPUT_DIR / "merged_model"
LOG_DIR                 = OUTPUT_DIR / "logs"

# Logging
LOG_INTERVAL            = 50                       # Log every N training steps

# ============================================================
# SETUP — DO NOT MODIFY
# ============================================================
def set_seed(seed: int) -> None:
    """Fix all random seeds for reproducibility."""
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
def load_and_preprocess_data(model_name: str, dataset_name: str, dataset_config: str,
                              max_seq_len: int, batch_size: int):
    """
    Load SST-2 from HuggingFace, tokenize, and create DataLoaders.

    Returns:
        train_loader: DataLoader for training split
        val_loader:   DataLoader for validation split
        tokenizer:    Loaded tokenizer
    """
    logger.info(f"Loading dataset: {dataset_name} ({dataset_config})")
    raw_dataset = load_dataset("glue", dataset_config)

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize_function(examples):
        return tokenizer(
            examples["sentence"],
            truncation=True,
            max_length=max_seq_len,
        )

    tokenized_dataset = raw_dataset.map(tokenize_function, batched=True,
                                         desc="Tokenizing")
    tokenized_dataset = tokenized_dataset.rename_column("label", "labels")
    tokenized_dataset.set_format(type="torch",
                                  columns=["input_ids", "attention_mask", "labels"])

    collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")

    train_loader = DataLoader(
        tokenized_dataset["train"],
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collator,
        drop_last=False,
    )
    val_loader = DataLoader(
        tokenized_dataset["validation"],
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collator,
    )

    logger.info(f"Train size: {len(tokenized_dataset['train'])} | "
                f"Val size:   {len(tokenized_dataset['validation'])}")
    return train_loader, val_loader, tokenizer


# ============================================================
# UTILITIES — DO NOT MODIFY
# ============================================================
def log_metrics(step: int, metrics: dict, split: str = "train") -> None:
    """Log a dict of metrics at a given step."""
    metric_str = " | ".join(f"{k}: {v:.4f}" for k, v in metrics.items())
    logger.info(f"[Step {step:5d}] [{split.upper():5s}] {metric_str}")


def plot_training_curve(train_losses: list, val_losses: list,
                        val_accuracies: list, save_path: Path) -> None:
    """Save a training curve plot to disk."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(train_losses, label="Train Loss", color="steelblue")
    axes[0].plot(
        [i * (len(train_losses) // len(val_losses)) for i in range(len(val_losses))],
        val_losses, label="Val Loss", color="tomato", marker="o",
    )
    axes[0].set_title("Loss Curve")
    axes[0].set_xlabel("Step")
    axes[0].set_ylabel("Loss")
    axes[0].legend()

    axes[1].plot(val_accuracies, color="seagreen", marker="o", label="Val Accuracy")
    axes[1].set_title("Validation Accuracy")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(save_path, dpi=120)
    plt.close()
    logger.info(f"Training curve saved to {save_path}")


# ============================================================
# VALIDATION HARNESS — DO NOT MODIFY
# ============================================================
def validate_lora_config(model) -> bool:
    """
    Validation harness for T2.
    Checks that:
      1. LoRA adapter parameters exist and are trainable
      2. Base model parameters are frozen
      3. Trainable parameter count is within expected range for this config

    Returns True if all checks pass, raises AssertionError otherwise.
    """
    trainable_params = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    frozen_params    = [(n, p) for n, p in model.named_parameters() if not p.requires_grad]

    # Check 1: LoRA layers exist
    lora_names = [n for n, _ in trainable_params if "lora_" in n]
    assert len(lora_names) > 0, (
        "VALIDATION FAILED: No LoRA parameters found. "
        "Did you call get_peft_model() correctly?"
    )

    # Check 2: Base weights are frozen
    base_trainable = [n for n, _ in trainable_params if "lora_" not in n]
    assert len(base_trainable) == 0, (
        f"VALIDATION FAILED: Base model parameters are not frozen: {base_trainable[:3]}"
    )

    # Check 3: Reasonable parameter count (for r=8, q_lin + v_lin, 6 DistilBERT layers)
    total_trainable = sum(p.numel() for _, p in trainable_params)
    assert 100_000 < total_trainable < 2_000_000, (
        f"VALIDATION FAILED: Trainable param count {total_trainable:,} is outside "
        f"expected range (100K–2M) for r={LORA_R}, target={LORA_TARGET_MODULES}"
    )

    logger.info("✓ validate_lora_config PASSED")
    logger.info(f"  Trainable params:  {total_trainable:,}")
    logger.info(f"  Frozen params:     {sum(p.numel() for _, p in frozen_params):,}")
    logger.info(f"  LoRA layers found: {len(lora_names)}")
    return True


def validate_model_output(model, tokenizer) -> bool:
    """
    Validation harness for T3/T4.
    Runs a single forward pass and checks output shape and dtype.
    """
    model.eval()
    with torch.no_grad():
        dummy_input = tokenizer(
            "This film was absolutely wonderful!",
            return_tensors="pt", truncation=True, max_length=MAX_SEQ_LEN
        ).to(DEVICE)
        outputs = model(**dummy_input)
        logits = outputs.logits

    assert logits.shape == (1, NUM_LABELS), (
        f"VALIDATION FAILED: Expected logits shape (1, {NUM_LABELS}), got {logits.shape}"
    )
    probs = torch.softmax(logits, dim=-1)
    assert probs.sum().item() - 1.0 < 1e-4, "VALIDATION FAILED: Softmax does not sum to 1."
    logger.info(f"✓ validate_model_output PASSED | logits: {logits.cpu().numpy()}")
    return True


# ============================================================
# TODO SECTIONS — STUDENTS IMPLEMENT BELOW
# ============================================================

def build_lora_config() -> LoraConfig:
    """
    TODO [T1]: Build the LoRA Configuration Object
    Bloom's Level: Apply
    Difficulty: Easy | Expected lines: ~8
    Description: Create and return a LoraConfig object using the PEFT library.
                 Use the constants defined in the CONFIG block above (LORA_R,
                 LORA_ALPHA, LORA_DROPOUT, LORA_TARGET_MODULES, LORA_BIAS,
                 LORA_TASK_TYPE). This object tells PEFT which layers to adapt
                 and how to scale the LoRA update. Choosing target_modules
                 determines which weight matrices receive low-rank adapters —
                 for DistilBERT, "q_lin" and "v_lin" are the query and value
                 projection matrices in each self-attention layer.
    Hints:
      1. (Conceptual) The task_type parameter tells PEFT how to handle the
         model's output head. For classification, use TaskType.SEQ_CLS.
      2. (Implementation) All config constants are defined in the CONFIG block.
         Import LoraConfig from peft and pass the constants as keyword arguments.
    Expected behavior: Returns a LoraConfig object. Print it to verify all
                       fields are set correctly before proceeding to T2.
    """
    # >>> YOUR CODE HERE <<<
    raise NotImplementedError("TODO T1 not yet implemented")
    # >>> END YOUR CODE <<<


def apply_lora_to_model(base_model, lora_config: LoraConfig):
    """
    TODO [T2]: Apply LoRA Adapters to the Base Model
    Bloom's Level: Apply
    Difficulty: Easy | Expected lines: ~5
    Description: Use the PEFT library's get_peft_model() to wrap the base
                 model with LoRA adapters using the provided lora_config.
                 After wrapping, print the trainable parameter summary using
                 model.print_trainable_parameters(). Then call
                 validate_lora_config(model) to verify your implementation.
                 This step freezes all base model weights and injects trainable
                 A and B matrices alongside the target projection layers.
    Hints:
      1. (Conceptual) After get_peft_model(), the model's base weights are
         automatically frozen. Only A and B matrices in the LoRA branches
         will receive gradient updates during training.
      2. (Implementation) get_peft_model(model, config) returns the wrapped
         model. Don't forget to move the model to DEVICE after wrapping.
    Expected behavior: trainable params should be ~296,450 for r=8 on
                       DistilBERT with target_modules=["q_lin", "v_lin"].
                       validate_lora_config() should print ✓ PASSED.
    """
    # >>> YOUR CODE HERE <<<
    raise NotImplementedError("TODO T2 not yet implemented")
    # >>> END YOUR CODE <<<


def training_step(model, batch: dict, optimizer: AdamW,
                  scheduler, loss_fn: nn.CrossEntropyLoss) -> float:
    """
    TODO [T3]: Implement a Single Training Step
    Bloom's Level: Apply
    Difficulty: Medium | Expected lines: ~15
    Description: Implement one complete training iteration: move the batch
                 to DEVICE, perform a forward pass through the LoRA model,
                 compute cross-entropy loss, backpropagate, clip gradients,
                 update the optimizer, and step the scheduler. Return the
                 scalar loss value. This is the standard PyTorch training loop
                 for a HuggingFace model wrapped with PEFT.
    Hints:
      1. (Conceptual) HuggingFace models return a ModelOutput object. Access
         logits via outputs.logits. The loss_fn takes (logits, labels) where
         logits has shape [batch_size, num_labels].
      2. (Implementation) Use torch.nn.utils.clip_grad_norm_(model.parameters(),
         MAX_GRAD_NORM) before optimizer.step() to prevent gradient explosion.
         Remember to call optimizer.zero_grad() at the start.
    Expected behavior: Returns a float (loss value, typically 0.2–0.8 in
                       early training for SST-2 with this config).
    """
    model.train()
    # >>> YOUR CODE HERE <<<
    raise NotImplementedError("TODO T3 not yet implemented")
    # >>> END YOUR CODE <<<


def evaluation_loop(model, val_loader: DataLoader) -> dict:
    """
    TODO [T4]: Implement the Full Evaluation Loop
    Bloom's Level: Analyze
    Difficulty: Medium | Expected lines: ~20
    Description: Run the model in evaluation mode over the entire validation
                 DataLoader. Collect all predictions and ground-truth labels,
                 then compute and return a metrics dictionary containing:
                 "val_loss" (mean cross-entropy), "val_accuracy" (fraction
                 correct), and "val_f1" (macro F1 score). No gradients should
                 be computed during evaluation.
    Hints:
      1. (Conceptual) Use torch.no_grad() context manager to disable gradient
         tracking. This reduces memory usage and speeds up evaluation.
      2. (Implementation) Accumulate logits and labels across all batches as
         Python lists, then concatenate with torch.cat() after the loop.
         Use sklearn.metrics.accuracy_score and f1_score for metrics.
    Expected behavior: Returns dict with keys "val_loss", "val_accuracy",
                       "val_f1". After 3 epochs, val_accuracy should be
                       approximately 0.88–0.92 on SST-2.
    """
    model.eval()
    # >>> YOUR CODE HERE <<<
    raise NotImplementedError("TODO T4 not yet implemented")
    # >>> END YOUR CODE <<<


def compute_parameter_efficiency(model) -> dict:
    """
    TODO [T5]: Analyze Parameter Efficiency of LoRA
    Bloom's Level: Analyze
    Difficulty: Medium | Expected lines: ~10
    Description: Write a function that programmatically computes and returns
                 a dictionary with the following keys:
                   - "total_params": total number of parameters in the model
                   - "trainable_params": number of trainable (LoRA) parameters
                   - "frozen_params": number of frozen (base model) parameters
                   - "trainable_pct": percentage of trainable parameters
                   - "lora_memory_mb": memory used by LoRA params in MB (float32)
                   - "full_ft_memory_mb": memory full fine-tuning would use (MB)
                   - "memory_saving_pct": percentage memory saved vs full FT
                 Assume float32 (4 bytes per parameter) for all calculations.
                 Print a formatted summary table after computing values.
    Hints:
      1. (Conceptual) Iterate over model.named_parameters() and check
         p.requires_grad to separate trainable from frozen parameters.
      2. (Implementation) Memory in MB = num_params * 4 / (1024 * 1024).
         For Adam optimizer, full FT stores 3x the parameter count (params +
         2 gradient moment copies). LoRA only stores 3x the adapter params.
    Expected behavior: trainable_pct ≈ 0.44% for this config. The function
                       should print a readable summary table and return the dict.
    """
    # >>> YOUR CODE HERE <<<
    raise NotImplementedError("TODO T5 not yet implemented")
    # >>> END YOUR CODE <<<


def merge_and_export(model, output_path: Path) -> None:
    """
    TODO [T6]: Merge LoRA Weights and Export for Inference
    Bloom's Level: Create
    Difficulty: Hard | Expected lines: ~10
    Description: Implement adapter merging and model export. Merging combines
                 the LoRA adapter weights into the base model weights, producing
                 a standard (non-PEFT) model that runs at full inference speed
                 with zero overhead. The merged model is saved to output_path.
                 Also save the tokenizer to the same directory so the model
                 can be loaded independently of the PEFT library.
    Hints:
      1. (Conceptual) Merging computes W_merged = W₀ + (α/r) * B @ A for
         each target layer, replacing W₀. After merging, the adapter matrices
         A and B are discarded. The resulting model has the same parameter
         count as the base model but with adapted weights baked in. This is
         why merged models have ZERO inference latency overhead vs. base model.
      2. (Implementation) Call model.merge_and_unload() to get a standard
         HuggingFace model with merged weights. Then use .save_pretrained()
         to save it. Load the tokenizer from MODEL_NAME and save it too.
    Expected behavior: output_path directory contains config.json,
                       pytorch_model.bin (or model.safetensors), and
                       tokenizer files. The merged model can be loaded with
                       AutoModelForSequenceClassification.from_pretrained().
    """
    # >>> YOUR CODE HERE <<<
    raise NotImplementedError("TODO T6 not yet implemented")
    # >>> END YOUR CODE <<<


# ============================================================
# MAIN ENTRY POINT — DO NOT MODIFY
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("CSE 329 — LoRA Fine-Tuning Assignment")
    logger.info(f"Student ID: 2105066 | Model: {MODEL_NAME}")
    logger.info("=" * 60)

    # 1. Load data
    train_loader, val_loader, tokenizer = load_and_preprocess_data(
        MODEL_NAME, DATASET_NAME, DATASET_CONFIG, MAX_SEQ_LEN, BATCH_SIZE
    )

    # 2. Build LoRA config (T1)
    lora_config = build_lora_config()
    logger.info(f"LoRA Config: {lora_config}")

    # 3. Load base model and apply LoRA (T2)
    base_model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=NUM_LABELS
    )
    model = apply_lora_to_model(base_model, lora_config)
    validate_model_output(model, tokenizer)

    # 4. Parameter efficiency analysis (T5)
    efficiency_stats = compute_parameter_efficiency(model)

    # 5. Setup optimizer and scheduler
    optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )
    total_steps    = len(train_loader) * NUM_EPOCHS
    warmup_steps   = int(total_steps * WARMUP_RATIO)
    scheduler      = LinearLR(optimizer, start_factor=0.1, end_factor=1.0,
                               total_iters=warmup_steps)
    loss_fn        = nn.CrossEntropyLoss()

    # 6. Training loop
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

        # Validation
        val_metrics = evaluation_loop(model, val_loader)
        val_losses.append(val_metrics["val_loss"])
        val_accuracies.append(val_metrics["val_accuracy"])
        log_metrics(global_step, val_metrics, split="val")

    elapsed = time.time() - start_time
    logger.info(f"\nTraining complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # 7. Save adapter (not merged — preserves modularity)
    model.save_pretrained(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    logger.info(f"Adapter saved to {ADAPTER_DIR}")

    # 8. Plot training curve
    plot_training_curve(train_losses, val_losses, val_accuracies,
                         save_path=LOG_DIR / "training_curve.png")

    # 9. Merge and export (T6)
    merge_and_export(model, MERGED_DIR)
    logger.info(f"Merged model saved to {MERGED_DIR}")

    logger.info("=" * 60)
    logger.info("Assignment complete. Check outputs/ for all deliverables.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
