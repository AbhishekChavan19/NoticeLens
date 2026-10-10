"""
Dataset Statistics for NoticeLens

Generates and displays statistics about the notice dataset:
- Total notice count
- Notices per category
- Language distribution (English, Marathi, mixed, unknown)
- Text length statistics

Also provides a simple inspection utility to browse records.

Usage:
    from src.dataset.statistics import compute_statistics, inspect_record

    stats = compute_statistics("data/dataset/notices.csv")
    stats.print_stats()

CLI:
    python -m src.dataset.statistics
    python -m src.dataset.statistics --inspect Acad001
    python -m src.dataset.statistics --category Examination --limit 5
"""

import os
import sys
import argparse
import logging

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import NOTICE_CATEGORIES
from src.dataset import DEFAULT_DATASET_PATH

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Statistics
# -----------------------------------------------------------------------

class DatasetStatistics:
    """Holds computed statistics about a dataset."""

    def __init__(self, df: pd.DataFrame):
        self.total = len(df)
        self.df = df

        # --- Category distribution ---
        self.category_counts = {}
        if "category" in df.columns:
            counts = df["category"].value_counts()
            for cat in NOTICE_CATEGORIES:
                self.category_counts[cat] = int(counts.get(cat, 0))

        # --- Language distribution ---
        self.language_counts = {"English": 0, "Marathi": 0, "Mixed": 0, "Unknown": 0}
        LANG_MAP = {
            "en": "English", "english": "English",
            "mr": "Marathi", "marathi": "Marathi",
            "mixed": "Mixed",
            "unknown": "Unknown",
        }
        if "language" in df.columns:
            for lang in df["language"].fillna("Unknown"):
                lang_clean = str(lang).strip().lower()
                label = LANG_MAP.get(lang_clean, str(lang).strip().title())
                if label in self.language_counts:
                    self.language_counts[label] += 1
                else:
                    self.language_counts[label] = 1

        # --- Text length stats ---
        self.text_lengths = {"min": 0, "max": 0, "mean": 0, "median": 0}
        if "text" in df.columns:
            lengths = df["text"].fillna("").apply(len)
            if len(lengths) > 0:
                self.text_lengths["min"] = int(lengths.min())
                self.text_lengths["max"] = int(lengths.max())
                self.text_lengths["mean"] = int(lengths.mean())
                self.text_lengths["median"] = int(lengths.median())

    def print_stats(self):
        """Print formatted statistics to the console."""
        print("\n" + "=" * 60)
        print("  DATASET STATISTICS")
        print("=" * 60)
        print(f"  Total notices: {self.total}")
        print()

        # Category distribution
        print("  Category Distribution:")
        print(f"  {'Category':<15} {'Count':>6} {'Percent':>8}")
        print(f"  {'-' * 32}")
        for cat, count in self.category_counts.items():
            pct = (count / self.total * 100) if self.total > 0 else 0
            bar = "#" * int(pct / 5)  # Simple bar chart
            print(f"  {cat:<15} {count:>6} {pct:>7.1f}% {bar}")
        print()

        # Language distribution
        print("  Language Distribution:")
        print(f"  {'Language':<15} {'Count':>6} {'Percent':>8}")
        print(f"  {'-' * 32}")
        for lang, count in self.language_counts.items():
            pct = (count / self.total * 100) if self.total > 0 else 0
            print(f"  {lang:<15} {count:>6} {pct:>7.1f}%")
        print()

        # Text length stats
        print("  Text Length Statistics (characters):")
        print(f"    Min:    {self.text_lengths['min']:,}")
        print(f"    Max:    {self.text_lengths['max']:,}")
        print(f"    Mean:   {self.text_lengths['mean']:,}")
        print(f"    Median: {self.text_lengths['median']:,}")

        print("\n" + "=" * 60)


def compute_statistics(csv_path: str = DEFAULT_DATASET_PATH) -> DatasetStatistics:
    """
    Compute statistics for a NoticeLens CSV dataset.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DatasetStatistics object with all computed metrics.
    """
    if not os.path.exists(csv_path):
        logger.error(f"Dataset not found: {csv_path}")
        return DatasetStatistics(pd.DataFrame())

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} records from {csv_path}")

    return DatasetStatistics(df)


# -----------------------------------------------------------------------
# Inspection Utility
# -----------------------------------------------------------------------

def inspect_record(csv_path: str, record_id: str) -> None:
    """
    Display a single record from the dataset by ID.

    Args:
        csv_path: Path to the CSV file.
        record_id: The ID of the record to display.
    """
    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    record = df[df["id"] == record_id]

    if len(record) == 0:
        print(f"No record found with ID: {record_id}")
        return

    row = record.iloc[0]
    print("\n" + "=" * 60)
    print(f"  RECORD: {row['id']}")
    print("=" * 60)
    print(f"  Category: {row.get('category', 'N/A')}")
    print(f"  Language: {row.get('language', 'N/A')}")
    print(f"  Source:   {row.get('source', 'N/A')}")
    print(f"  Length:   {len(str(row.get('text', '')))}")
    print("-" * 60)
    print("  Text:")
    print("-" * 60)
    text = str(row.get("text", ""))
    # Print with indentation
    for line in text.split("\n"):
        print(f"  {line}")
    print("=" * 60)


def list_records(
    csv_path: str,
    category: str = None,
    limit: int = 10,
) -> None:
    """
    List records from the dataset with optional category filter.

    Args:
        csv_path: Path to the CSV file.
        category: Filter by category (optional).
        limit: Maximum number of records to show.
    """
    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)

    if category:
        df = df[df["category"] == category]
        if len(df) == 0:
            print(f"No records found for category: {category}")
            return

    print(f"\n  Showing {min(limit, len(df))} of {len(df)} records")
    print(f"  {'ID':<15} {'Category':<15} {'Lang':<8} {'Length':>6}  {'Text Preview'}")
    print(f"  {'-' * 75}")

    for _, row in df.head(limit).iterrows():
        text = str(row.get("text", ""))
        preview = text[:50].replace("\n", " ") + ("..." if len(text) > 50 else "")
        print(
            f"  {str(row['id']):<15} "
            f"{str(row.get('category', 'N/A')):<15} "
            f"{str(row.get('language', '?')):<8} "
            f"{len(text):>6}  "
            f"{preview}"
        )

    print()


# -----------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------

def main():
    """CLI entry point for dataset statistics and inspection."""
    parser = argparse.ArgumentParser(
        description="Generate statistics or inspect the NoticeLens dataset."
    )
    parser.add_argument(
        "--path", type=str, default=DEFAULT_DATASET_PATH,
        help=f"Path to the CSV file (default: {DEFAULT_DATASET_PATH})"
    )
    parser.add_argument(
        "--inspect", type=str, default=None,
        help="Inspect a specific record by ID."
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Filter records by category when listing."
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Maximum records to show when listing (default: 10)."
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List records instead of showing statistics."
    )

    args = parser.parse_args()

    if args.inspect:
        inspect_record(args.path, args.inspect)
    elif args.list:
        list_records(args.path, category=args.category, limit=args.limit)
    else:
        stats = compute_statistics(args.path)
        stats.print_stats()


if __name__ == "__main__":
    main()
