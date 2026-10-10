"""
Dataset Splitter for NoticeLens

Splits the notice dataset into train/validation/test sets
using stratified splitting to preserve category distribution.

Default split ratios: 70% train / 15% validation / 15% test

Handles edge cases where a category has too few examples for
proper stratification by falling back gracefully.

Usage:
    from src.dataset.splitter import split_dataset

    result = split_dataset("data/dataset/notices.csv")
    result.print_summary()

CLI:
    python -m src.dataset.splitter
    python -m src.dataset.splitter --path data/dataset/notices.csv
    python -m src.dataset.splitter --train-ratio 0.8 --val-ratio 0.1 --test-ratio 0.1
"""

import os
import sys
import argparse
import logging
from dataclasses import dataclass, field

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import NOTICE_CATEGORIES
from src.dataset import DEFAULT_DATASET_PATH, DATASET_DIR

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Split Result
# -----------------------------------------------------------------------

@dataclass
class SplitResult:
    """Result of a dataset split operation."""

    train_df: pd.DataFrame = None
    val_df: pd.DataFrame = None
    test_df: pd.DataFrame = None
    warnings: list = field(default_factory=list)
    success: bool = True
    error: str = None

    def print_summary(self):
        """Print a formatted summary of the split."""
        print("\n" + "=" * 60)
        print("  DATASET SPLIT SUMMARY")
        print("=" * 60)

        if not self.success:
            print(f"  [FAIL] Error: {self.error}")
            print("=" * 60)
            return

        total = len(self.train_df) + len(self.val_df) + len(self.test_df)
        print(f"  Total records: {total}")
        print(f"  Train: {len(self.train_df):>5} ({len(self.train_df) / total * 100:.1f}%)")
        print(f"  Val:   {len(self.val_df):>5} ({len(self.val_df) / total * 100:.1f}%)")
        print(f"  Test:  {len(self.test_df):>5} ({len(self.test_df) / total * 100:.1f}%)")
        print()

        # Per-category breakdown
        print(f"  {'Category':<15} {'Train':>6} {'Val':>6} {'Test':>6} {'Total':>6}")
        print(f"  {'-' * 45}")
        for cat in NOTICE_CATEGORIES:
            t = len(self.train_df[self.train_df["category"] == cat])
            v = len(self.val_df[self.val_df["category"] == cat])
            te = len(self.test_df[self.test_df["category"] == cat])
            cat_total = t + v + te
            if cat_total > 0:
                print(f"  {cat:<15} {t:>6} {v:>6} {te:>6} {cat_total:>6}")

        if self.warnings:
            print(f"\n  [WARN] Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"    - {w}")

        print("\n" + "=" * 60)


# -----------------------------------------------------------------------
# Stratified Splitting Logic
# -----------------------------------------------------------------------

def split_dataset(
    csv_path: str = DEFAULT_DATASET_PATH,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
    save: bool = True,
    output_dir: str = None,
) -> SplitResult:
    """
    Split a NoticeLens dataset into train/val/test sets with stratification.

    Uses per-category stratification to preserve the category distribution
    across all splits. Categories with fewer than 3 examples are handled
    gracefully — their samples go to the training set with a warning.

    Args:
        csv_path:    Path to the source CSV file.
        train_ratio: Fraction for training (default: 0.70).
        val_ratio:   Fraction for validation (default: 0.15).
        test_ratio:  Fraction for testing (default: 0.15).
        random_seed: Random seed for reproducibility.
        save:        If True, save split CSVs to output_dir.
        output_dir:  Directory for output files (default: same as input CSV).

    Returns:
        SplitResult with train/val/test DataFrames and any warnings.
    """
    result = SplitResult()

    # --- Validate ratios ---
    ratio_sum = train_ratio + val_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 0.01:
        result.success = False
        result.error = (
            f"Split ratios must sum to 1.0, got {ratio_sum:.2f} "
            f"({train_ratio} + {val_ratio} + {test_ratio})"
        )
        return result

    # --- Load dataset ---
    if not os.path.exists(csv_path):
        result.success = False
        result.error = f"File not found: {csv_path}"
        return result

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        result.success = False
        result.error = f"Cannot read CSV: {e}"
        return result

    if len(df) == 0:
        result.success = False
        result.error = "Dataset is empty."
        return result

    if "category" not in df.columns:
        result.success = False
        result.error = "Dataset missing 'category' column."
        return result

    # --- Perform stratified split per category ---
    train_parts = []
    val_parts = []
    test_parts = []

    # Minimum samples needed for a proper 3-way split
    MIN_FOR_STRATIFICATION = 3

    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat].sample(
            frac=1, random_state=random_seed
        ).reset_index(drop=True)

        n = len(cat_df)

        if n < MIN_FOR_STRATIFICATION:
            # Too few examples — put all in training, warn
            train_parts.append(cat_df)
            result.warnings.append(
                f"Category '{cat}' has only {n} sample(s). "
                f"All placed in training set (need >={MIN_FOR_STRATIFICATION} "
                f"for stratification)."
            )
            logger.warning(
                f"Category '{cat}': {n} samples, all sent to training."
            )
            continue

        # Calculate split sizes
        n_test = max(1, round(n * test_ratio))
        n_val = max(1, round(n * val_ratio))
        n_train = n - n_val - n_test

        # Safety: ensure train gets at least 1
        if n_train < 1:
            n_train = 1
            leftover = n - n_train
            n_val = leftover // 2
            n_test = leftover - n_val

        # Split
        train_parts.append(cat_df.iloc[:n_train])
        val_parts.append(cat_df.iloc[n_train:n_train + n_val])
        test_parts.append(cat_df.iloc[n_train + n_val:])

        logger.info(
            f"Category '{cat}': {n} total -> "
            f"{n_train} train, {n_val} val, {n_test} test"
        )

    # Combine all parts
    result.train_df = pd.concat(train_parts, ignore_index=True) if train_parts else pd.DataFrame()
    result.val_df = pd.concat(val_parts, ignore_index=True) if val_parts else pd.DataFrame()
    result.test_df = pd.concat(test_parts, ignore_index=True) if test_parts else pd.DataFrame()

    # Shuffle within each split
    result.train_df = result.train_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    if len(result.val_df) > 0:
        result.val_df = result.val_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    if len(result.test_df) > 0:
        result.test_df = result.test_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)

    # Warn if val or test are empty
    if len(result.val_df) == 0:
        result.warnings.append("Validation set is empty — not enough data.")
    if len(result.test_df) == 0:
        result.warnings.append("Test set is empty — not enough data.")

    # --- Save split CSVs ---
    if save:
        if output_dir is None:
            output_dir = os.path.dirname(csv_path)

        os.makedirs(output_dir, exist_ok=True)

        train_path = os.path.join(output_dir, "train.csv")
        val_path = os.path.join(output_dir, "val.csv")
        test_path = os.path.join(output_dir, "test.csv")

        result.train_df.to_csv(train_path, index=False)
        result.val_df.to_csv(val_path, index=False)
        result.test_df.to_csv(test_path, index=False)

        print(f"  Saved: {train_path} ({len(result.train_df)} rows)")
        print(f"  Saved: {val_path} ({len(result.val_df)} rows)")
        print(f"  Saved: {test_path} ({len(result.test_df)} rows)")

    result.success = True
    return result


# -----------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------

def main():
    """CLI entry point for dataset splitting."""
    parser = argparse.ArgumentParser(
        description="Split the NoticeLens dataset into train/val/test sets."
    )
    parser.add_argument(
        "--path", type=str, default=DEFAULT_DATASET_PATH,
        help=f"Path to the CSV file (default: {DEFAULT_DATASET_PATH})"
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.70,
        help="Training set ratio (default: 0.70)"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.15,
        help="Validation set ratio (default: 0.15)"
    )
    parser.add_argument(
        "--test-ratio", type=float, default=0.15,
        help="Test set ratio (default: 0.15)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory for split files (default: same as input)"
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't save files, just show the summary."
    )

    args = parser.parse_args()

    result = split_dataset(
        csv_path=args.path,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        random_seed=args.seed,
        save=not args.no_save,
        output_dir=args.output_dir,
    )

    result.print_summary()

    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()
