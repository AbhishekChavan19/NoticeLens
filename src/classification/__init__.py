"""
Notice Classification Package for NoticeLens (Phase 4)

Provides:
- XLM-RoBERTa multilingual notice classifier training and evaluation
- TF-IDF + Linear SVM baseline model for academic comparison
- Prediction API: predict_notice_category(text, threshold)
"""

from src.classification.predictor import predict_notice_category, NoticePredictor

__all__ = ["predict_notice_category", "NoticePredictor"]
