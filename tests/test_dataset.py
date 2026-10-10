"""
Tests for the Dataset Module

Run with:
    python -m pytest tests/test_dataset.py -v
"""

import os
import sys
import tempfile

import pytest
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import NOTICE_CATEGORIES
from src.dataset import DATASET_COLUMNS, MIN_TEXT_LENGTH
from src.dataset.validator import validate_dataset, ValidationReport
from src.dataset.statistics import compute_statistics, DatasetStatistics
from src.dataset.splitter import split_dataset, SplitResult


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _create_temp_csv(records: list[dict], columns=None) -> str:
    """Create a temporary CSV file from a list of dicts and return its path."""
    if columns is None:
        columns = DATASET_COLUMNS
    df = pd.DataFrame(records, columns=columns)
    path = tempfile.mktemp(suffix=".csv")
    df.to_csv(path, index=False)
    return path


def _make_sample_records(n: int = 20, category: str = "Examination") -> list[dict]:
    """Generate n sample records for testing."""
    records = []
    for i in range(n):
        records.append({
            "id": f"test_{category}_{i:03d}",
            "text": f"This is a sample {category} notice number {i}. "
                    f"It contains enough text to pass the minimum length check. "
                    f"Students should report to the examination hall by 10 AM.",
            "category": category,
            "language": "en",
            "source": "test",
        })
    return records


def _make_multi_category_records() -> list[dict]:
    """Generate records spanning multiple categories for split testing."""
    records = []
    # Give each category enough samples for stratification
    category_counts = {
        "Examination": 10,
        "Academics": 8,
        "Admission": 7,
        "Scholarship": 6,
        "Other": 4,
    }
    for cat, count in category_counts.items():
        records.extend(_make_sample_records(count, cat))
    return records


# -----------------------------------------------------------------------
# Tests for Validator
# -----------------------------------------------------------------------

class TestValidator:
    """Tests for dataset validation."""

    def test_file_not_found(self):
        report = validate_dataset("/nonexistent/path.csv")
        assert not report.is_valid
        assert report.error_count > 0

    def test_valid_dataset(self):
        records = _make_sample_records(5)
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            assert report.is_valid
            assert report.error_count == 0
            assert report.total_rows == 5
        finally:
            os.unlink(path)

    def test_empty_dataset(self):
        path = _create_temp_csv([])
        try:
            report = validate_dataset(path)
            assert not report.is_valid
        finally:
            os.unlink(path)

    def test_missing_text(self):
        records = _make_sample_records(3)
        records[1]["text"] = ""  # Empty text
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            assert not report.is_valid
            errors = [i for i in report.issues if i.issue_type == "missing_text"]
            assert len(errors) == 1
        finally:
            os.unlink(path)

    def test_missing_category(self):
        records = _make_sample_records(3)
        records[0]["category"] = ""
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            assert not report.is_valid
            errors = [i for i in report.issues if i.issue_type == "missing_category"]
            assert len(errors) == 1
        finally:
            os.unlink(path)

    def test_invalid_category(self):
        records = _make_sample_records(3)
        records[2]["category"] = "InvalidCategory"
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            assert not report.is_valid
            errors = [i for i in report.issues if i.issue_type == "invalid_category"]
            assert len(errors) == 1
        finally:
            os.unlink(path)

    def test_duplicate_ids(self):
        records = _make_sample_records(3)
        records[1]["id"] = records[0]["id"]  # Duplicate
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            assert not report.is_valid
            errors = [i for i in report.issues if i.issue_type == "duplicate_id"]
            assert len(errors) >= 1
        finally:
            os.unlink(path)

    def test_short_document_warning(self):
        records = _make_sample_records(3)
        records[0]["text"] = "Short"  # Very short text
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            warnings = [i for i in report.issues if i.issue_type == "short_document"]
            assert len(warnings) == 1
        finally:
            os.unlink(path)

    def test_all_valid_categories(self):
        """Every NOTICE_CATEGORY value should be accepted."""
        records = []
        for i, cat in enumerate(NOTICE_CATEGORIES):
            records.append({
                "id": f"cat_test_{i}",
                "text": f"This is a valid notice for the {cat} category with enough text to pass checks.",
                "category": cat,
                "language": "en",
                "source": "test",
            })
        path = _create_temp_csv(records)
        try:
            report = validate_dataset(path)
            cat_errors = [i for i in report.issues if i.issue_type == "invalid_category"]
            assert len(cat_errors) == 0
        finally:
            os.unlink(path)


# -----------------------------------------------------------------------
# Tests for Statistics
# -----------------------------------------------------------------------

class TestStatistics:
    """Tests for dataset statistics computation."""

    def test_basic_stats(self):
        records = _make_sample_records(10)
        path = _create_temp_csv(records)
        try:
            stats = compute_statistics(path)
            assert stats.total == 10
            assert stats.category_counts["Examination"] == 10
            assert stats.language_counts["English"] == 10
        finally:
            os.unlink(path)

    def test_multi_category_stats(self):
        records = _make_multi_category_records()
        path = _create_temp_csv(records)
        try:
            stats = compute_statistics(path)
            assert stats.total == 35
            assert stats.category_counts["Examination"] == 10
            assert stats.category_counts["Academics"] == 8
            assert stats.category_counts["Admission"] == 7
        finally:
            os.unlink(path)

    def test_text_length_stats(self):
        records = _make_sample_records(5)
        path = _create_temp_csv(records)
        try:
            stats = compute_statistics(path)
            assert stats.text_lengths["min"] > 0
            assert stats.text_lengths["max"] >= stats.text_lengths["min"]
            assert stats.text_lengths["mean"] > 0
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        stats = compute_statistics("/nonexistent.csv")
        assert stats.total == 0


# -----------------------------------------------------------------------
# Tests for Splitter
# -----------------------------------------------------------------------

class TestSplitter:
    """Tests for dataset splitting."""

    def test_basic_split(self):
        records = _make_multi_category_records()
        path = _create_temp_csv(records)
        try:
            result = split_dataset(path, save=False)
            assert result.success
            total = len(result.train_df) + len(result.val_df) + len(result.test_df)
            assert total == 35  # All records accounted for
        finally:
            os.unlink(path)

    def test_split_ratios(self):
        records = _make_multi_category_records()
        path = _create_temp_csv(records)
        try:
            result = split_dataset(path, save=False)
            total = len(result.train_df) + len(result.val_df) + len(result.test_df)
            train_pct = len(result.train_df) / total
            # Allow some tolerance due to rounding with small category sizes
            assert 0.55 <= train_pct <= 0.85
        finally:
            os.unlink(path)

    def test_stratification_preserves_categories(self):
        records = _make_multi_category_records()
        path = _create_temp_csv(records)
        try:
            result = split_dataset(path, save=False)
            # Each category with enough samples should appear in train
            train_cats = set(result.train_df["category"].unique())
            assert "Examination" in train_cats
            assert "Academics" in train_cats
        finally:
            os.unlink(path)

    def test_rare_category_warning(self):
        """Categories with < 3 samples should produce a warning."""
        records = _make_multi_category_records()
        # Add a category with only 2 samples
        records.append({
            "id": "rare_001",
            "text": "This is a rare placement notice with enough text for the test.",
            "category": "Placement",
            "language": "en",
            "source": "test",
        })
        records.append({
            "id": "rare_002",
            "text": "Another rare placement notice with sufficient text content.",
            "category": "Placement",
            "language": "en",
            "source": "test",
        })
        path = _create_temp_csv(records)
        try:
            result = split_dataset(path, save=False)
            assert result.success
            # Should have a warning about Placement
            placement_warnings = [
                w for w in result.warnings if "Placement" in w
            ]
            assert len(placement_warnings) > 0
        finally:
            os.unlink(path)

    def test_invalid_ratios(self):
        records = _make_sample_records(10)
        path = _create_temp_csv(records)
        try:
            result = split_dataset(
                path, train_ratio=0.5, val_ratio=0.3, test_ratio=0.3,
                save=False
            )
            assert not result.success
            assert "ratios" in result.error.lower()
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        result = split_dataset("/nonexistent.csv", save=False)
        assert not result.success

    def test_save_files(self):
        records = _make_multi_category_records()
        path = _create_temp_csv(records)
        output_dir = tempfile.mkdtemp()
        try:
            result = split_dataset(path, save=True, output_dir=output_dir)
            assert result.success
            assert os.path.exists(os.path.join(output_dir, "train.csv"))
            assert os.path.exists(os.path.join(output_dir, "val.csv"))
            assert os.path.exists(os.path.join(output_dir, "test.csv"))
        finally:
            os.unlink(path)
            for f in ["train.csv", "val.csv", "test.csv"]:
                fp = os.path.join(output_dir, f)
                if os.path.exists(fp):
                    os.unlink(fp)
            os.rmdir(output_dir)

    def test_reproducibility(self):
        """Same seed should produce the same split."""
        records = _make_multi_category_records()
        path = _create_temp_csv(records)
        try:
            r1 = split_dataset(path, random_seed=42, save=False)
            r2 = split_dataset(path, random_seed=42, save=False)
            assert list(r1.train_df["id"]) == list(r2.train_df["id"])
            assert list(r1.val_df["id"]) == list(r2.val_df["id"])
            assert list(r1.test_df["id"]) == list(r2.test_df["id"])
        finally:
            os.unlink(path)
