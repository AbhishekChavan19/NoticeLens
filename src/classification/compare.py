"""
Model Comparison: XLM-RoBERTa vs TF-IDF + Linear SVM (Phase 4)

Loads saved evaluation results from both models and produces a
side-by-side comparison table.

Usage:
    python -m src.classification.compare
"""

import os
import sys
import json

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classification.dataset import CLASSIFICATION_CATEGORIES

EVAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models", "notice_classifier", "evaluation",
)


def compare_models():
    """Load and compare evaluation results from both models."""

    xlmr_path = os.path.join(EVAL_DIR, "xlm_roberta_results.json")
    svm_path = os.path.join(EVAL_DIR, "baseline_svm_results.json")

    # Load results
    results = {}
    for name, path in [("XLM-RoBERTa", xlmr_path), ("TF-IDF + SVM", svm_path)]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                results[name] = json.load(f)
        else:
            print(f"  [!] {name} results not found at: {path}")
            print(f"     Run training first.")

    if len(results) < 2:
        print("\n  Cannot compare — need both models trained.")
        return

    # --- Header ---
    print("\n" + "=" * 70)
    print("  MODEL COMPARISON: XLM-RoBERTa vs TF-IDF + Linear SVM")
    print("=" * 70)

    # --- Overall Metrics ---
    print(f"\n  {'Metric':<25} {'XLM-RoBERTa':>15} {'TF-IDF + SVM':>15} {'Winner':>10}")
    print(f"  {'-'*65}")

    metrics = [
        ("Accuracy", "test_accuracy"),
        ("Macro Precision", "test_macro_precision"),
        ("Macro Recall", "test_macro_recall"),
        ("Macro F1", "test_macro_f1"),
    ]

    winners = {"XLM-RoBERTa": 0, "TF-IDF + SVM": 0}

    for label, key in metrics:
        xlmr_val = results["XLM-RoBERTa"].get(key, 0)
        svm_val = results["TF-IDF + SVM"].get(key, 0)

        if xlmr_val > svm_val:
            winner = "XLM-R"
            winners["XLM-RoBERTa"] += 1
        elif svm_val > xlmr_val:
            winner = "SVM"
            winners["TF-IDF + SVM"] += 1
        else:
            winner = "Tie"

        print(f"  {label:<25} {xlmr_val:>15.4f} {svm_val:>15.4f} {winner:>10}")

    # --- Per-Class F1 ---
    print(f"\n  Per-Class F1 Scores:")
    print(f"  {'Category':<15} {'XLM-RoBERTa':>15} {'TF-IDF + SVM':>15} {'Winner':>10}")
    print(f"  {'-'*55}")

    for cat in CLASSIFICATION_CATEGORIES:
        xlmr_f1 = results["XLM-RoBERTa"].get("per_class", {}).get(cat, {}).get("f1", 0)
        svm_f1 = results["TF-IDF + SVM"].get("per_class", {}).get(cat, {}).get("f1", 0)

        if xlmr_f1 > svm_f1:
            winner = "XLM-R"
        elif svm_f1 > xlmr_f1:
            winner = "SVM"
        else:
            winner = "Tie"

        print(f"  {cat:<15} {xlmr_f1:>15.4f} {svm_f1:>15.4f} {winner:>10}")

    # --- Training Time ---
    xlmr_time = results["XLM-RoBERTa"].get("training_time_seconds", 0)
    svm_time = results["TF-IDF + SVM"].get("training_time_seconds", 0)
    print(f"\n  Training Time:")
    print(f"    XLM-RoBERTa:  {xlmr_time:.1f}s ({xlmr_time/60:.1f} min)")
    print(f"    TF-IDF + SVM: {svm_time:.1f}s")

    # --- Verdict ---
    print(f"\n{'='*70}")
    xlmr_f1 = results["XLM-RoBERTa"]["test_macro_f1"]
    svm_f1 = results["TF-IDF + SVM"]["test_macro_f1"]

    if xlmr_f1 > svm_f1:
        print(f"  * WINNER: XLM-RoBERTa (Macro F1: {xlmr_f1:.4f} vs {svm_f1:.4f})")
        diff = xlmr_f1 - svm_f1
        print(f"    XLM-RoBERTa outperforms the baseline by {diff:.4f} F1 points.")
    elif svm_f1 > xlmr_f1:
        print(f"  * WINNER: TF-IDF + SVM (Macro F1: {svm_f1:.4f} vs {xlmr_f1:.4f})")
        diff = svm_f1 - xlmr_f1
        print(f"    Baseline outperforms XLM-RoBERTa by {diff:.4f} F1 points.")
        print(f"    This may indicate overfitting or that the dataset is too small")
        print(f"    for the transformer to learn effectively.")
    else:
        print(f"  * TIE: Both models achieve Macro F1 = {xlmr_f1:.4f}")

    print(f"\n  Note: With only {results['XLM-RoBERTa'].get('dataset_sizes', {}).get('test', '?')} test samples,")
    print(f"  results may vary significantly with different random seeds.")
    print(f"  Both models should be evaluated with caution on such a small dataset.")
    print(f"{'='*70}\n")

    # Save comparison
    comparison = {
        "xlm_roberta_macro_f1": xlmr_f1,
        "svm_baseline_macro_f1": svm_f1,
        "xlm_roberta_accuracy": results["XLM-RoBERTa"]["test_accuracy"],
        "svm_baseline_accuracy": results["TF-IDF + SVM"]["test_accuracy"],
        "winner_by_f1": "XLM-RoBERTa" if xlmr_f1 > svm_f1 else (
            "TF-IDF + SVM" if svm_f1 > xlmr_f1 else "Tie"
        ),
    }
    comp_path = os.path.join(EVAL_DIR, "model_comparison.json")
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)
    print(f"  Comparison saved to: {comp_path}")


if __name__ == "__main__":
    compare_models()
