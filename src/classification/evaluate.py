"""
Evaluation & Comparison Module for NoticeLens (Phase 4)

Compares:
    1. TF-IDF + Linear SVM Baseline
    2. XLM-RoBERTa Multilingual Transformer Model

Using the exact same held-out test split.
"""

import os
import json
import logging
import argparse
from typing import Dict, Any

import pandas as pd

from src.classification.config import (
    EVALUATION_RESULTS_PATH, MODEL_SAVE_DIR, BASELINE_SAVE_DIR, CATEGORIES
)
from src.classification.dataset import load_and_split_dataset
from src.classification.baseline import BaselineClassifier
from src.classification.trainer import train_xlm_roberta, compute_metrics

logger = logging.getLogger(__name__)


def run_full_evaluation(
    csv_path: str = "data/dataset/notices.csv",
    epochs: int = 4,
    batch_size: int = 4,
) -> Dict[str, Any]:
    """
    Train and evaluate both Baseline (TF-IDF + SVM) and XLM-RoBERTa models
    on the exact same held-out test split and return side-by-side metrics.
    """
    print("\n============================================================")
    print("  PHASE 4: Model Training & Academic Comparison")
    print("============================================================\n")

    # 1. Load data split
    train_df, val_df, test_df = load_and_split_dataset(csv_path)

    # 2. Train & Evaluate Baseline Classifier (TF-IDF + Linear SVM)
    print("\n------------------------------------------------------------")
    print("  [1/2] Training Baseline Model: TF-IDF + Linear SVM")
    print("------------------------------------------------------------")
    baseline = BaselineClassifier()
    baseline.train(train_df["text"].tolist(), train_df["label"].tolist())
    baseline.save(BASELINE_SAVE_DIR)
    baseline_metrics = baseline.evaluate(test_df)
    print(f"  Baseline Accuracy: {baseline_metrics['accuracy']:.4f} | Macro F1: {baseline_metrics['macro_f1']:.4f}")

    # 3. Train & Evaluate XLM-RoBERTa
    print("\n------------------------------------------------------------")
    print("  [2/2] Training Base Model: XLM-RoBERTa")
    print("------------------------------------------------------------")
    xlm_metrics = train_xlm_roberta(
        csv_path=csv_path,
        save_dir=MODEL_SAVE_DIR,
        epochs=epochs,
        batch_size=batch_size,
    )

    # 4. Consolidate Results
    comparison_report = {
        "dataset_summary": {
            "total_notices": len(train_df) + len(val_df) + len(test_df),
            "train_size": len(train_df),
            "val_size": len(val_df),
            "test_size": len(test_df),
            "num_categories": len(CATEGORIES),
        },
        "baseline_tfidf_svm": baseline_metrics,
        "xlm_roberta": xlm_metrics,
    }

    # Save to JSON
    os.makedirs(os.path.dirname(EVALUATION_RESULTS_PATH), exist_ok=True)
    with open(EVALUATION_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(comparison_report, f, indent=2)

    # 5. Print Comparison Summary Table
    print("\n============================================================")
    print("  MODEL COMPARISON ON HELD-OUT TEST SET")
    print("============================================================")
    print(f"  {'Metric':<20} {'TF-IDF + Linear SVM':<22} {'XLM-RoBERTa':<20}")
    print(f"  {'-' * 62}")
    print(f"  {'Accuracy':<20} {baseline_metrics['accuracy']:<22.4f} {xlm_metrics['accuracy']:<20.4f}")
    print(f"  {'Macro Precision':<20} {baseline_metrics['macro_precision']:<22.4f} {xlm_metrics['macro_precision']:<20.4f}")
    print(f"  {'Macro Recall':<20} {baseline_metrics['macro_recall']:<22.4f} {xlm_metrics['macro_recall']:<20.4f}")
    print(f"  {'Macro F1':<20} {baseline_metrics['macro_f1']:<22.4f} {xlm_metrics['macro_f1']:<20.4f}")
    print("============================================================\n")

    return comparison_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full evaluation and comparison.")
    parser.add_argument("--csv", type=str, default="data/dataset/notices.csv")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    run_full_evaluation(csv_path=args.csv, epochs=args.epochs, batch_size=args.batch_size)
