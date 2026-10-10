"""
Dataset Preparation Script for NoticeLens

Extracts text from raw PDF notices in data/raw/ using the Phase 1
PDF extractor and creates the notices.csv dataset file.

Categories are inferred from filename prefixes (your own naming):
    Acad*  → Academics
    Ad*    → Admission
    E*     → Examination
    Sch*   → Scholarship
    Other* → Other

These are based on YOUR file naming convention — not an LLM.
You should still review the generated CSV and correct any mistakes.

Usage:
    python -m src.dataset.prepare
    python -m src.dataset.prepare --raw-dir data/raw --output data/dataset/notices.csv
    python -m src.dataset.prepare --ocr        # Enable OCR for scanned PDFs
"""

import os
import re
import sys
import argparse
import logging

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pdf.extractor import extract_from_pdf
from src.language.detector import detect_language
from src.dataset import DATASET_COLUMNS, DEFAULT_DATASET_PATH

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Filename → Category Mapping
# -----------------------------------------------------------------------
# Based on the user's own file naming convention in data/raw/
# Order matters: longer prefixes checked first to avoid "E" matching "Event"

PREFIX_TO_CATEGORY = [
    ("Acad", "Academics"),
    ("Ad", "Admission"),
    ("Sch", "Scholarship"),
    ("Other", "Other"),
    ("Exam", "Examination"),
    ("Ev", "Event"),
    ("Place", "Placement"),
    ("Intern", "Internship"),
    ("Gen", "General"),
    ("E", "Examination"),   # Fallback: E001, E002, etc.
]


def _infer_category(filename: str) -> str:
    """
    Infer a notice category from the filename prefix.

    This uses YOUR file naming convention, not an LLM.
    Returns "Other" if no known prefix matches.
    """
    stem = os.path.splitext(filename)[0]  # Remove .pdf

    for prefix, category in PREFIX_TO_CATEGORY:
        if stem.startswith(prefix):
            return category

    return "Other"


def _make_id(filename: str) -> str:
    """Create a clean ID from a filename."""
    return os.path.splitext(filename)[0]  # e.g., "Acad001"


# -----------------------------------------------------------------------
# Main Preparation Logic
# -----------------------------------------------------------------------

def prepare_dataset(
    raw_dir: str,
    output_path: str = DEFAULT_DATASET_PATH,
    ocr_enabled: bool = False,
    tesseract_path: str = None,
) -> pd.DataFrame:
    """
    Prepare the notices.csv dataset from raw PDF files.

    Scans the raw_dir for PDF files, extracts text from each using the
    Phase 1 PDF extractor, infers category from filename prefix, and
    writes the result to a CSV.

    Args:
        raw_dir:        Path to directory containing raw PDF files.
        output_path:    Path for the output CSV file.
        ocr_enabled:    Whether to use OCR for scanned PDFs.
        tesseract_path: Path to Tesseract executable (if not on PATH).

    Returns:
        DataFrame of the prepared dataset.
    """
    if not os.path.isdir(raw_dir):
        print(f"Error: Directory not found: {raw_dir}")
        return pd.DataFrame()

    # Find all PDF files
    pdf_files = sorted([
        f for f in os.listdir(raw_dir)
        if f.lower().endswith(".pdf")
    ])

    if not pdf_files:
        print(f"No PDF files found in: {raw_dir}")
        return pd.DataFrame()

    print(f"\nFound {len(pdf_files)} PDF files in {raw_dir}")
    print(f"OCR: {'Enabled' if ocr_enabled else 'Disabled'}")
    print("-" * 60)

    records = []
    failed = []

    for i, filename in enumerate(pdf_files, 1):
        filepath = os.path.join(raw_dir, filename)
        record_id = _make_id(filename)
        category = _infer_category(filename)

        print(f"  [{i:>3}/{len(pdf_files)}] {filename:<25} -> {category:<15}", end="")

        # Extract text
        try:
            with open(filepath, "rb") as f:
                file_bytes = f.read()

            result = extract_from_pdf(
                file_bytes=file_bytes,
                ocr_enabled=ocr_enabled,
                tesseract_path=tesseract_path,
            )

            if result.success and result.extracted_text.strip():
                lang_result = detect_language(result.extracted_text)
                records.append({
                    "id": record_id,
                    "text": result.extracted_text,
                    "category": category,
                    "language": lang_result.language,
                    "source": f"pccoe_raw/{filename}",
                })
                char_count = len(result.extracted_text)
                method = result.extraction_method
                print(f" [OK] {char_count:>6} chars ({method}, lang={lang_result.language})")
            else:
                failed.append((filename, result.error or "No text extracted"))
                print(f" [FAIL] {result.error or 'No text'}")

        except Exception as e:
            failed.append((filename, str(e)))
            print(f" [FAIL] Error: {e}")

    print("-" * 60)
    print(f"  Extracted: {len(records)}/{len(pdf_files)} files")

    if failed:
        print(f"\n  [WARN] Failed files ({len(failed)}):")
        for fname, reason in failed:
            print(f"    - {fname}: {reason}")
        if not ocr_enabled:
            print(
                "\n  Tip: Some PDFs may be scanned images. Try running with --ocr"
                "\n     to enable Tesseract OCR fallback."
            )

    # Create DataFrame
    if not records:
        print("\nNo records extracted. CSV not created.")
        return pd.DataFrame()

    df = pd.DataFrame(records, columns=DATASET_COLUMNS)

    # Save CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n  [OK] Dataset saved to: {output_path}")
    print(f"     {len(df)} records, {len(df['category'].unique())} categories")

    return df


# -----------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------

def main():
    """CLI entry point for dataset preparation."""
    parser = argparse.ArgumentParser(
        description="Prepare NoticeLens dataset from raw PDF notices."
    )
    parser.add_argument(
        "--raw-dir", type=str, default="data/raw",
        help="Directory containing raw PDF files (default: data/raw)"
    )
    parser.add_argument(
        "--output", type=str, default=DEFAULT_DATASET_PATH,
        help=f"Output CSV path (default: {DEFAULT_DATASET_PATH})"
    )
    parser.add_argument(
        "--ocr", action="store_true",
        help="Enable Tesseract OCR for scanned PDFs."
    )
    parser.add_argument(
        "--tesseract-path", type=str, default=None,
        help="Path to Tesseract executable (if not on PATH)."
    )

    args = parser.parse_args()

    prepare_dataset(
        raw_dir=args.raw_dir,
        output_path=args.output,
        ocr_enabled=args.ocr,
        tesseract_path=args.tesseract_path,
    )


if __name__ == "__main__":
    main()
