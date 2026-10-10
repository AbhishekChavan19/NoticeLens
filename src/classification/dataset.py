"""
Dataset & Tokenization Loader for XLM-RoBERTa (Phase 4)

Implements:
1. PyTorch NoticeDataset for Transformer sequence classification.
2. Dataset loader & stratified train/val/test splitting.
3. Class weight calculation for handling category imbalance.

Requirement Checklist:
- Transformer tokenization (AutoTokenizer / XLMRobertaTokenizerFast).
- NO aggressive stemming, stopword removal, or punctuation deletion.
"""

import os
import logging
from typing import Dict, Tuple, List, Optional

import pandas as pd
import torch
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

from src.classification.config import (
    LABEL2ID, ID2LABEL, NUM_LABELS, CATEGORIES,
    DEFAULT_MAX_LENGTH
)

logger = logging.getLogger(__name__)


class NoticeDataset(Dataset):
    """
    PyTorch Dataset wrapper for notice text classification with XLM-RoBERTa.
    Applies Hugging Face tokenizer directly to raw/cleaned text without
    stemming or stopword removal.
    """

    def __init__(
        self,
        texts: List[str],
        labels: Optional[List[int]],
        tokenizer,
        max_length: int = DEFAULT_MAX_LENGTH,
    ):
        self.texts = list(texts)
        self.labels = list(labels) if labels is not None else None
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = str(self.texts[idx])

        # Tokenization without destructive preprocessing
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        item = {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
        }

        if self.labels is not None:
            item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)

        return item


def load_and_split_dataset(
    csv_path: str = "data/dataset/notices.csv",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load dataset from CSV and perform stratified train/val/test split.

    Args:
        csv_path: Path to notices.csv
        train_ratio: Fraction for training set (0.70)
        val_ratio: Fraction for validation set (0.15)
        test_ratio: Fraction for test set (0.15)
        random_state: Seed for reproducibility

    Returns:
        (train_df, val_df, test_df)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path)

    # Filter out empty or missing text/category records
    df = df.dropna(subset=["text", "category"]).copy()
    df = df[df["text"].str.strip().str.len() > 0].copy()

    # Filter records to valid categories
    df = df[df["category"].isin(CATEGORIES)].copy()

    if len(df) == 0:
        raise ValueError(f"No valid records found in {csv_path}")

    logger.info(f"Loaded {len(df)} valid records from {csv_path}")

    # Map category names to integer IDs
    df["label"] = df["category"].map(LABEL2ID)

    # Stratified Split (or fallback if rare categories have < 2 samples)
    counts = df["label"].value_counts()
    min_count = counts.min()

    if min_count < 2:
        logger.warning(
            f"Some categories have only {min_count} sample(s). "
            "Falling back to unstratified split for rare classes."
        )
        stratify_col = None
    else:
        stratify_col = df["label"]

    train_val_df, test_df = train_test_split(
        df,
        test_size=test_ratio,
        stratify=stratify_col,
        random_state=random_state,
    )

    # Re-evaluate stratification for val split
    val_relative_ratio = val_ratio / (train_ratio + val_ratio)
    train_val_counts = train_val_df["label"].value_counts()

    if train_val_counts.min() < 2:
        val_stratify = None
    else:
        val_stratify = train_val_df["label"]

    train_df, val_df = train_test_split(
        train_val_df,
        test_size=val_relative_ratio,
        stratify=val_stratify,
        random_state=random_state,
    )

    logger.info(
        f"Split dataset into Train: {len(train_df)}, "
        f"Val: {len(val_df)}, Test: {len(test_df)}"
    )

    return (
        train_df.reset_index(drop=True),
        val_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )


def compute_class_weights_tensor(
    train_labels: List[int],
    num_labels: int = NUM_LABELS,
    device: str = "cpu",
) -> torch.Tensor:
    """
    Calculate balanced class weights to mitigate severe class imbalance.

    Returns PyTorch tensor of shape (num_labels,).
    """
    import numpy as np

    present_classes = np.unique(train_labels)
    computed_weights = compute_class_weight(
        class_weight="balanced",
        classes=present_classes,
        y=train_labels,
    )

    # Initialize weights for all classes to 1.0
    weights = np.ones(num_labels, dtype=np.float32)
    for idx, cls in enumerate(present_classes):
        weights[cls] = computed_weights[idx]

    return torch.tensor(weights, dtype=torch.float, device=device)
