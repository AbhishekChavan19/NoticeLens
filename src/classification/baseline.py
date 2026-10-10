"""
TF-IDF + Linear SVM Baseline Model for NoticeLens (Phase 4)

Provides an academic baseline for comparison against XLM-RoBERTa.
Uses TF-IDF feature extraction + Calibrated Linear SVM classifier.
"""

import os
import joblib
import logging
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from src.classification.config import (
    BASELINE_SAVE_DIR, CATEGORIES, LABEL2ID, ID2LABEL, NUM_LABELS
)

logger = logging.getLogger(__name__)


class BaselineClassifier:
    """
    TF-IDF + Calibrated Linear SVM Baseline Notice Classifier.
    """

    def __init__(self, max_features: int = 10000, ngram_range: Tuple[int, int] = (1, 2)):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
        )
        base_svm = LinearSVC(class_weight="balanced", random_state=42, max_iter=2000)
        self.classifier = CalibratedClassifierCV(estimator=base_svm, cv=3)
        self.is_fitted = False

    def train(self, train_texts: list, train_labels: list) -> None:
        """Fit TF-IDF vectorizer and Linear SVM on training data."""
        logger.info(f"Fitting TF-IDF Vectorizer on {len(train_texts)} samples...")
        X_train = self.vectorizer.fit_transform(train_texts)

        logger.info("Training Linear SVM...")
        counts = pd.Series(train_labels).value_counts()
        min_samples = counts.min() if len(counts) > 0 else 0

        if min_samples < 2:
            # Fallback to LogisticRegression for micro datasets (< 2 samples per class)
            from sklearn.linear_model import LogisticRegression
            self.classifier = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)
        else:
            n_folds = min(3, min_samples)
            base_svm = LinearSVC(class_weight="balanced", random_state=42, max_iter=2000)
            self.classifier = CalibratedClassifierCV(estimator=base_svm, cv=n_folds)

        self.classifier.fit(X_train, train_labels)
        self.is_fitted = True

    def predict(self, text: str) -> Dict[str, Any]:
        """Predict category, confidence, and probability distribution for a single text."""
        if not self.is_fitted:
            raise RuntimeError("Baseline classifier must be trained before predicting.")

        X = self.vectorizer.transform([text])
        probs = self.classifier.predict_proba(X)[0]
        pred_id = int(np.argmax(probs))
        confidence = float(probs[pred_id])

        prob_dict = {cat: 0.0 for cat in CATEGORIES}
        for idx, cls_id in enumerate(self.classifier.classes_):
            prob_dict[ID2LABEL[cls_id]] = float(probs[idx])

        return {
            "category": ID2LABEL[pred_id],
            "confidence": confidence,
            "probabilities": prob_dict,
        }

    def evaluate(self, test_df: pd.DataFrame) -> Dict[str, Any]:
        """Evaluate baseline on held-out test set and return full metrics dictionary."""
        if not self.is_fitted:
            raise RuntimeError("Baseline classifier must be trained before evaluating.")

        test_texts = test_df["text"].tolist()
        y_true = test_df["label"].tolist()

        X_test = self.vectorizer.transform(test_texts)
        y_pred = self.classifier.predict(X_test)

        acc = float(accuracy_score(y_true, y_pred))
        macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="macro", zero_division=0
        )
        per_class_p, per_class_r, per_class_f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average=None, labels=list(range(NUM_LABELS)), zero_division=0
        )

        per_class_metrics = {}
        for idx, cat in ID2LABEL.items():
            per_class_metrics[cat] = {
                "precision": round(float(per_class_p[idx]), 4),
                "recall": round(float(per_class_r[idx]), 4),
                "f1": round(float(per_class_f1[idx]), 4),
            }

        return {
            "model": "TF-IDF + Linear SVM",
            "accuracy": round(acc, 4),
            "macro_precision": round(float(macro_p), 4),
            "macro_recall": round(float(macro_r), 4),
            "macro_f1": round(float(macro_f1), 4),
            "per_class": per_class_metrics,
        }

    def save(self, save_dir: str = BASELINE_SAVE_DIR) -> None:
        """Save model and vectorizer to disk."""
        os.makedirs(save_dir, exist_ok=True)
        joblib.dump(self.vectorizer, os.path.join(save_dir, "tfidf_vectorizer.joblib"))
        joblib.dump(self.classifier, os.path.join(save_dir, "linear_svm.joblib"))
        logger.info(f"Saved baseline model to {save_dir}")

    def load(self, save_dir: str = BASELINE_SAVE_DIR) -> None:
        """Load model and vectorizer from disk."""
        vec_path = os.path.join(save_dir, "tfidf_vectorizer.joblib")
        clf_path = os.path.join(save_dir, "linear_svm.joblib")

        if not os.path.exists(vec_path) or not os.path.exists(clf_path):
            raise FileNotFoundError(f"Baseline files missing in {save_dir}")

        self.vectorizer = joblib.load(vec_path)
        self.classifier = joblib.load(clf_path)
        self.is_fitted = True
        logger.info(f"Loaded baseline model from {save_dir}")
