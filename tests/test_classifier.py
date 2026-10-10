"""
Test Suite for Notice Classification Module (Phase 4)

Run with:
    python -m pytest tests/test_classifier.py -v
"""

import os
import pytest
import pandas as pd

from src.classification.config import (
    CATEGORIES, LABEL2ID, ID2LABEL, DEFAULT_CONFIDENCE_THRESHOLD
)
from src.classification.dataset import (
    NoticeDataset, load_and_split_dataset, compute_class_weights_tensor
)
from src.classification.baseline import BaselineClassifier
from src.classification.predictor import predict_notice_category, NoticePredictor


# ---------------------------------------------------------------------------
# Sample Test Notices (English & Marathi)
# ---------------------------------------------------------------------------

SAMPLE_ENGLISH_EXAM_NOTICE = """
PIMPRI CHINCHWAD COLLEGE OF ENGINEERING
EXAMINATION DEPARTMENT NOTICE
All B.Tech students are hereby informed that the End Semester Examinations (ESE)
for Academic Year 2024-25 are scheduled to begin from 15th November 2024.
Hall tickets must be downloaded from the student portal before 10th November 2024.
"""

SAMPLE_MARATHI_ADMISSION_NOTICE = """
पिंपरी चिंचवड अभियांत्रिकी महाविद्यालय, निगडी, पुणे.
प्रवेश प्रक्रिया २०२४-२५
प्रथम वर्ष बी.टेक प्रवेशासाठी अर्ज केलेल्या सर्व विद्यार्थ्यांसाठी महत्त्वाची सूचना.
गुणवत्ता यादी आज सायंकाळी ५.०० वाजता महाविद्यालयाच्या संकेतस्थळावर प्रसिद्ध केली जाईल.
पात्र विद्यार्थ्यांनी मूळ कागदपत्रांसह प्रवेश कक्षाशी संपर्क साधावा.
"""

SAMPLE_UNCERTAIN_NOTICE = "Hello world random non-notice string xyz 12345."


# ---------------------------------------------------------------------------
# Test Functions
# ---------------------------------------------------------------------------

def test_categories_and_label_mappings():
    """Verify that all 9 categories are defined in configuration."""
    assert len(CATEGORIES) == 9
    assert "Examination" in CATEGORIES
    assert "Academics" in CATEGORIES
    assert "Admission" in CATEGORIES
    assert "Scholarship" in CATEGORIES
    assert "Placement" in CATEGORIES
    assert "Internship" in CATEGORIES
    assert "Event" in CATEGORIES
    assert "General" in CATEGORIES
    assert "Other" in CATEGORIES
    assert len(LABEL2ID) == 9
    assert len(ID2LABEL) == 9


def test_baseline_model_training_and_prediction():
    """Test TF-IDF + Linear SVM baseline classifier training and prediction."""
    train_texts = [
        SAMPLE_ENGLISH_EXAM_NOTICE,
        SAMPLE_MARATHI_ADMISSION_NOTICE,
        "Scholarship applications open for ST/SC students.",
        "Placement drive by Tata Consultancy Services TCS.",
    ]
    train_labels = [
        LABEL2ID["Examination"],
        LABEL2ID["Admission"],
        LABEL2ID["Scholarship"],
        LABEL2ID["Placement"],
    ]

    baseline = BaselineClassifier()
    baseline.train(train_texts, train_labels)

    result = baseline.predict(SAMPLE_ENGLISH_EXAM_NOTICE)
    assert isinstance(result, dict)
    assert result["category"] == "Examination"
    assert result["confidence"] > 0.0
    assert "probabilities" in result
    assert len(result["probabilities"]) == 9


def test_prediction_api_threshold_fallback():
    """Test confidence thresholding in prediction API."""
    predictor = NoticePredictor()

    # High-confidence prediction on clear notice
    res = predictor.predict(SAMPLE_ENGLISH_EXAM_NOTICE, threshold=0.10)
    assert "category" in res
    assert "confidence" in res
    assert "probabilities" in res

    # Empty text returns Other/Uncertain
    res_empty = predictor.predict("", threshold=0.50)
    assert res_empty["category"] == "Other/Uncertain"
    assert res_empty["confidence"] == 0.0


def test_class_weight_computation():
    """Test inverse class weight tensor computation."""
    labels = [0, 0, 0, 0, 1, 2]  # Imbalanced labels
    weights = compute_class_weights_tensor(labels, num_labels=9)
    assert weights.shape[0] == 9
    assert weights[1] > weights[0]  # Minority class gets higher weight
