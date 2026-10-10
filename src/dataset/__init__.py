"""
Dataset Module for NoticeLens

Provides tools for dataset preparation, validation, statistics,
inspection, and train/val/test splitting of notice datasets.
"""

import os

# Default paths
DATASET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "dataset",
)
DEFAULT_DATASET_PATH = os.path.join(DATASET_DIR, "notices.csv")

# CSV column schema
DATASET_COLUMNS = ["id", "text", "category", "language", "source"]

# Minimum text length (characters) below which a notice is flagged as "short"
MIN_TEXT_LENGTH = 50
