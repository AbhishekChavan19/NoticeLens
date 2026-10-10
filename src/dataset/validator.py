"""
Dataset Validator for NoticeLens

Validates the notices.csv dataset for common issues:
- Missing text or category
- Invalid category values
- Duplicate IDs
- Empty or extremely short documents
- Missing columns

Usage:
    from src.dataset.validator import validate_dataset

    report = validate_dataset("data/dataset/notices.csv")
    report.print_report()

CLI:
    python -m src.dataset.validator
    python -m src.dataset.validator --path data/dataset/notices.csv
"""

import os
import sys
import argparse
import logging
from dataclasses import dataclass, field

import pandas as pd

# Add project root to path for CLI usage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import NOTICE_CATEGORIES
from src.dataset import DATASET_COLUMNS, DEFAULT_DATASET_PATH, MIN_TEXT_LENGTH

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Validation Report
# -----------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """A single validation issue found in the dataset."""

    severity: str        # "error" or "warning"
    issue_type: str      # e.g., "missing_text", "invalid_category"
    row_id: str          # The ID of the affected row (or "N/A")
    message: str         # Human-readable description


@dataclass
class ValidationReport:
    """Complete validation report for a dataset."""

    total_rows: int = 0
    issues: list = field(default_factory=list)  # List[ValidationIssue]
    is_valid: bool = True

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def add_error(self, issue_type: str, row_id: str, message: str):
        """Add an error-level issue."""
        self.issues.append(ValidationIssue("error", issue_type, row_id, message))
        self.is_valid = False

    def add_warning(self, issue_type: str, row_id: str, message: str):
        """Add a warning-level issue."""
        self.issues.append(ValidationIssue("warning", issue_type, row_id, message))

    def print_report(self):
        """Print a formatted validation report to the console."""
        print("\n" + "=" * 60)
        print("  DATASET VALIDATION REPORT")
        print("=" * 60)
        print(f"  Total rows:  {self.total_rows}")
        print(f"  Errors:      {self.error_count}")
        print(f"  Warnings:    {self.warning_count}")
        print(f"  Status:      {'[PASS] VALID' if self.is_valid else '[FAIL] INVALID'}")
        print("=" * 60)

        if not self.issues:
            print("  No issues found. Dataset looks good!")
            print("=" * 60)
            return

        # Group by issue type
        issue_types = {}
        for issue in self.issues:
            key = (issue.severity, issue.issue_type)
            if key not in issue_types:
                issue_types[key] = []
            issue_types[key].append(issue)

        for (severity, issue_type), items in sorted(issue_types.items()):
            icon = "[ERROR]" if severity == "error" else "[WARN]"
            print(f"\n  {icon} {issue_type} ({len(items)} found)")
            print(f"  {'-' * 50}")
            for item in items[:10]:  # Show max 10 per type
                print(f"    [{item.row_id}] {item.message}")
            if len(items) > 10:
                print(f"    ... and {len(items) - 10} more")

        print("\n" + "=" * 60)


# -----------------------------------------------------------------------
# Validation Logic
# -----------------------------------------------------------------------

def validate_dataset(csv_path: str = DEFAULT_DATASET_PATH) -> ValidationReport:
    """
    Validate a NoticeLens CSV dataset.

    Checks for:
        1. File existence and readability
        2. Required columns present
        3. Missing text fields
        4. Missing category fields
        5. Invalid category values
        6. Duplicate IDs
        7. Empty documents (no text at all)
        8. Extremely short documents (< MIN_TEXT_LENGTH chars)

    Args:
        csv_path: Path to the CSV file to validate.

    Returns:
        ValidationReport with all found issues.
    """
    report = ValidationReport()

    # --- Check file exists ---
    if not os.path.exists(csv_path):
        report.add_error("file_not_found", "N/A", f"File not found: {csv_path}")
        return report

    # --- Load CSV ---
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        report.add_error("file_read_error", "N/A", f"Cannot read CSV: {e}")
        return report

    report.total_rows = len(df)

    if report.total_rows == 0:
        report.add_error("empty_dataset", "N/A", "Dataset has no rows.")
        return report

    # --- Check required columns ---
    missing_columns = [col for col in DATASET_COLUMNS if col not in df.columns]
    if missing_columns:
        report.add_error(
            "missing_columns", "N/A",
            f"Missing required columns: {missing_columns}"
        )
        return report

    # --- Check for duplicate IDs ---
    duplicated_ids = df[df["id"].duplicated(keep=False)]
    if len(duplicated_ids) > 0:
        seen = set()
        for _, row in duplicated_ids.iterrows():
            row_id = str(row["id"])
            if row_id not in seen:
                count = len(duplicated_ids[duplicated_ids["id"] == row["id"]])
                report.add_error(
                    "duplicate_id", row_id,
                    f"ID '{row_id}' appears {count} times."
                )
                seen.add(row_id)

    # --- Row-level checks ---
    valid_categories = set(NOTICE_CATEGORIES)

    for idx, row in df.iterrows():
        row_id = str(row.get("id", f"row_{idx}"))

        # Missing or empty text
        text = str(row.get("text", "")).strip()
        if not text or text == "nan":
            report.add_error(
                "missing_text", row_id,
                "Text field is empty or missing."
            )
            continue

        # Empty document (only whitespace)
        if len(text) == 0:
            report.add_error(
                "empty_document", row_id,
                "Document is empty after stripping whitespace."
            )
            continue

        # Extremely short document
        if len(text) < MIN_TEXT_LENGTH:
            report.add_warning(
                "short_document", row_id,
                f"Document is very short ({len(text)} chars, "
                f"minimum recommended: {MIN_TEXT_LENGTH})."
            )

        # Missing category
        category = str(row.get("category", "")).strip()
        if not category or category == "nan":
            report.add_error(
                "missing_category", row_id,
                "Category field is empty or missing."
            )
        elif category not in valid_categories:
            report.add_error(
                "invalid_category", row_id,
                f"Invalid category '{category}'. "
                f"Must be one of: {NOTICE_CATEGORIES}"
            )

        # Missing language (warning, not error)
        language = str(row.get("language", "")).strip()
        if not language or language == "nan" or language == "unknown":
            report.add_warning(
                "missing_language", row_id,
                "Language field is missing or set to 'unknown'."
            )

    logger.info(
        f"Validation complete: {report.total_rows} rows, "
        f"{report.error_count} errors, {report.warning_count} warnings"
    )

    return report


# -----------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------

def main():
    """CLI entry point for dataset validation."""
    parser = argparse.ArgumentParser(
        description="Validate a NoticeLens notice dataset CSV."
    )
    parser.add_argument(
        "--path", type=str, default=DEFAULT_DATASET_PATH,
        help=f"Path to the CSV file (default: {DEFAULT_DATASET_PATH})"
    )
    args = parser.parse_args()

    report = validate_dataset(args.path)
    report.print_report()

    # Exit with error code if validation failed
    sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
