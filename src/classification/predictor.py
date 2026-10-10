"""
Prediction Module for NoticeLens Notice Classifier (Phase 4)

Implements the predict_notice_category(text, threshold=0.50) public API function.

Features:
1. Loads fine-tuned XLM-RoBERTa model from models/notice_classifier/.
2. Computes category softmax probabilities.
3. Enforces confidence threshold: if max probability < threshold, returns "Other/Uncertain".
4. Graceful fallback to TF-IDF + Linear SVM baseline if XLM-RoBERTa model is not found.
"""

import os
import logging
from typing import Dict, Any, Optional

try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    F = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    TORCH_AVAILABLE = False

from src.classification.config import (
    MODEL_SAVE_DIR, DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_LENGTH, ID2LABEL, DEVICE
)

logger = logging.getLogger(__name__)


class NoticePredictor:
    """
    Inference Engine for Notice Lens Notice Classifier.
    """

    def __init__(
        self,
        model_dir: str = MODEL_SAVE_DIR,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        device_str: str = DEVICE,
        use_baseline: bool = True,
    ):
        self.model_dir = model_dir
        self.threshold = threshold
        self.device = torch.device(device_str) if (TORCH_AVAILABLE and torch is not None) else "cpu"
        self.use_baseline = use_baseline
        self.model = None
        self.tokenizer = None
        self.baseline_model = None

        self._load_model()

    def _load_model(self) -> None:
        """Load primary classification model (TF-IDF + Linear SVM baseline or XLM-RoBERTa)."""
        from src.classification.baseline import BaselineClassifier

        if self.use_baseline:
            try:
                logger.info("Loading primary classifier: TF-IDF + Linear SVM Baseline...")
                self.baseline_model = BaselineClassifier()
                self.baseline_model.load()
                return
            except Exception as e:
                logger.warning(f"Failed to load baseline model ({e}). Training baseline on notices.csv...")
                try:
                    import pandas as pd
                    from src.classification.config import ROOT_DIR, LABEL2ID
                    csv_path = ROOT_DIR / "data" / "dataset" / "notices.csv"
                    df = pd.read_csv(csv_path)
                    df = df.dropna(subset=["text", "category"])
                    df["label"] = df["category"].map(LABEL2ID)
                    self.baseline_model.train(df["text"].tolist(), df["label"].tolist())
                    self.baseline_model.save()
                    return
                except Exception as train_err:
                    logger.warning(f"Failed to auto-train baseline ({train_err}). Falling back to XLM-RoBERTa.")

        # XLM-RoBERTa fallback / alternative
        if (
            TORCH_AVAILABLE
            and AutoTokenizer is not None
            and os.path.exists(self.model_dir)
            and os.path.exists(os.path.join(self.model_dir, "config.json"))
        ):
            try:
                logger.info(f"Loading XLM-RoBERTa model from: {self.model_dir}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
                if self.device is not None:
                    self.model.to(self.device)
                self.model.eval()
            except Exception as e:
                logger.error(f"Failed to load XLM-RoBERTa model from {self.model_dir}: {e}")

    def predict(self, text: str, threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Predict notice category for a given text.

        Args:
            text: Input text string of the notice.
            threshold: Confidence threshold (defaults to self.threshold).

        Returns:
            Dict containing:
                - "category": Predicted label string (or "Other/Uncertain")
                - "confidence": Float between 0.0 and 1.0
                - "probabilities": Dict mapping category names to probability floats
        """
        thresh = threshold if threshold is not None else self.threshold

        if not text or not text.strip():
            return {
                "category": "Other/Uncertain",
                "confidence": 0.0,
                "probabilities": {cat: 0.0 for cat in ID2LABEL.values()},
                "model_used": "none",
            }

        # 1. Prediction using Baseline (TF-IDF + Linear SVM)
        if self.baseline_model is not None and self.baseline_model.is_fitted:
            res = self.baseline_model.predict(text)
            top_cat = res["category"]
            conf = res["confidence"]
            final_cat = top_cat if conf >= thresh else "Other/Uncertain"

            return {
                "category": final_cat,
                "raw_category": top_cat,
                "confidence": round(conf, 4),
                "probabilities": res["probabilities"],
                "model_used": "TF-IDF + Linear SVM Baseline",
            }

        # 2. XLM-RoBERTa alternative/fallback
        if self.model is not None and self.tokenizer is not None:
            encoding = self.tokenizer(
                text,
                truncation=True,
                max_length=DEFAULT_MAX_LENGTH,
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**encoding)
                probs = F.softmax(outputs.logits, dim=1).squeeze(0).cpu().numpy()

            pred_id = int(probs.argmax())
            confidence = float(probs[pred_id])
            top_category = ID2LABEL[pred_id]

            prob_dict = {
                ID2LABEL[i]: round(float(probs[i]), 4)
                for i in range(len(probs))
            }

            # Enforce Confidence Threshold
            final_category = top_category if confidence >= thresh else "Other/Uncertain"

            return {
                "category": final_category,
                "raw_category": top_category,
                "confidence": round(confidence, 4),
                "probabilities": prob_dict,
                "model_used": "XLM-RoBERTa",
            }

        raise RuntimeError(
            "No trained model found. Please run training first using "
            "`python -m src.classification.trainer` or `python -m src.classification.baseline`."
        )


# Global singleton instance for easy function call
_PREDICTOR_INSTANCE = None


def predict_notice_category(text: str, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> Dict[str, Any]:
    """
    Public API function to classify a notice text.

    Args:
        text: Notice text string.
        threshold: Minimum confidence score required (default: 0.50).

    Returns:
        Dict with keys: "category", "confidence", "probabilities"
    """
    global _PREDICTOR_INSTANCE
    if _PREDICTOR_INSTANCE is None:
        _PREDICTOR_INSTANCE = NoticePredictor(threshold=threshold)
    return _PREDICTOR_INSTANCE.predict(text, threshold=threshold)
