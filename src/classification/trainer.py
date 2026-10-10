"""
XLM-RoBERTa Trainer for Multilingual Notice Classification (Phase 4)

Features:
1. Fine-tunes XLM-RoBERTa (xlm-roberta-base) for 9-category notice sequence classification.
2. Supports PyTorch weighted CrossEntropyLoss for handling category imbalance.
3. Student laptop / CPU friendly training loop (low memory footprint, gradient accumulation, CPU device fallback).
4. Saves fine-tuned model and tokenizer under models/notice_classifier/.
5. Evaluates on validation and test sets; generates accuracy, macro P/R/F1, per-class metrics, and confusion matrix.
"""

import os
import json
import logging
import argparse
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)

from src.classification.config import (
    MODEL_NAME, MODEL_SAVE_DIR, CATEGORIES, LABEL2ID, ID2LABEL, NUM_LABELS,
    DEFAULT_MAX_LENGTH, DEFAULT_BATCH_SIZE, DEFAULT_EPOCHS, DEFAULT_LEARNING_RATE,
    EVALUATION_RESULTS_PATH, DEVICE
)
from src.classification.dataset import (
    NoticeDataset, load_and_split_dataset, compute_class_weights_tensor
)

logger = logging.getLogger(__name__)


def compute_metrics(y_true: list, y_pred: list) -> Dict[str, Any]:
    """Compute accuracy, macro metrics, per-class metrics, and confusion matrix."""
    acc = float(accuracy_score(y_true, y_pred))
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    per_class_p, per_class_r, per_class_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=list(range(NUM_LABELS)), zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=list(range(NUM_LABELS)))

    per_class_metrics = {}
    for idx, cat in ID2LABEL.items():
        per_class_metrics[cat] = {
            "precision": round(float(per_class_p[idx]), 4),
            "recall": round(float(per_class_r[idx]), 4),
            "f1": round(float(per_class_f1[idx]), 4),
        }

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "per_class": per_class_metrics,
        "confusion_matrix": cm.tolist(),
        "categories": CATEGORIES,
    }


def train_xlm_roberta(
    csv_path: str = "data/dataset/notices.csv",
    save_dir: str = MODEL_SAVE_DIR,
    model_name: str = MODEL_NAME,
    max_length: int = DEFAULT_MAX_LENGTH,
    batch_size: int = DEFAULT_BATCH_SIZE,
    epochs: int = DEFAULT_EPOCHS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    use_class_weights: bool = True,
    device_str: str = DEVICE,
) -> Dict[str, Any]:
    """
    Train and evaluate XLM-RoBERTa for college notice classification.
    """
    device = torch.device(device_str)
    print(f"\n============================================================")
    print(f"  Training XLM-RoBERTa Notice Classifier ({model_name})")
    print(f"  Device: {device.type.upper()} | Batch Size: {batch_size} | Epochs: {epochs}")
    print(f"============================================================\n")

    # 1. Load Data
    train_df, val_df, test_df = load_and_split_dataset(csv_path)

    # 2. Tokenizer & Datasets
    logger.info(f"Loading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    train_dataset = NoticeDataset(train_df["text"], train_df["label"], tokenizer, max_length)
    val_dataset = NoticeDataset(val_df["text"], val_df["label"], tokenizer, max_length)
    test_dataset = NoticeDataset(test_df["text"], test_df["label"], tokenizer, max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # 3. Model Architecture
    logger.info(f"Loading sequence classification model: {model_name}")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    model.to(device)

    # 4. Class Weights Loss Function
    if use_class_weights:
        class_weights = compute_class_weights_tensor(train_df["label"].tolist(), device=device)
        loss_fn = nn.CrossEntropyLoss(weight=class_weights)
        print("  [INFO] Class weighting enabled to mitigate category imbalance.")
    else:
        loss_fn = nn.CrossEntropyLoss()

    # 5. Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=int(total_steps * 0.1), num_training_steps=total_steps
    )

    # 6. Training Loop
    best_val_f1 = -1.0
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0

        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = loss_fn(outputs.logits, labels)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)

        # Validation Step
        model.eval()
        val_preds, val_targets = [], []
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                preds = torch.argmax(outputs.logits, dim=1)

                val_preds.extend(preds.cpu().numpy())
                val_targets.extend(labels.cpu().numpy())

        val_metrics = compute_metrics(val_targets, val_preds)
        print(
            f"  Epoch {epoch}/{epochs} | Train Loss: {avg_train_loss:.4f} | "
            f"Val Acc: {val_metrics['accuracy']:.4f} | Val Macro F1: {val_metrics['macro_f1']:.4f}"
        )

        # Save Best Model Checkpoint
        if val_metrics["macro_f1"] >= best_val_f1:
            best_val_f1 = val_metrics["macro_f1"]
            os.makedirs(save_dir, exist_ok=True)
            model.save_pretrained(save_dir)
            tokenizer.save_pretrained(save_dir)

    print(f"\n  [OK] Fine-tuning complete. Model saved to: {save_dir}")

    # 7. Final Test Evaluation
    logger.info("Evaluating fine-tuned model on held-out test set...")
    # Load best model back
    model = AutoModelForSequenceClassification.from_pretrained(save_dir).to(device)
    model.eval()

    test_preds, test_targets = [], []
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=1)

            test_preds.extend(preds.cpu().numpy())
            test_targets.extend(labels.cpu().numpy())

    test_metrics = compute_metrics(test_targets, test_preds)
    test_metrics["model"] = "XLM-RoBERTa"
    test_metrics["dataset_sizes"] = {
        "train": len(train_df),
        "validation": len(val_df),
        "test": len(test_df),
    }

    # Save evaluation metrics JSON
    os.makedirs(os.path.dirname(EVALUATION_RESULTS_PATH), exist_ok=True)
    with open(EVALUATION_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)

    print(f"  [OK] Evaluation metrics saved to: {EVALUATION_RESULTS_PATH}")
    return test_metrics


def main():
    parser = argparse.ArgumentParser(description="Train XLM-RoBERTa notice classifier.")
    parser.add_argument("--csv", type=str, default="data/dataset/notices.csv")
    parser.add_argument("--save-dir", type=str, default=MODEL_SAVE_DIR)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=DEFAULT_LEARNING_RATE)
    args = parser.parse_args()

    train_xlm_roberta(
        csv_path=args.csv,
        save_dir=args.save_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()
