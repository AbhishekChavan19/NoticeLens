"""
Test Script for Notice Classification (Phase 4)

Tests the trained XLM-RoBERTa model on sample English and Marathi notices.

Usage:
    python -m src.classification.test_predictions
"""

import os
import sys
import logging

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classification.predictor import predict_notice_category
from src.classification.dataset import CLASSIFICATION_CATEGORIES

# ---------------------------------------------------------------------------
# Sample Notices for Testing
# ---------------------------------------------------------------------------

SAMPLE_NOTICES = [
    {
        "label": "Examination (English)",
        "expected": "Examination",
        "text": (
            "NOTICE - EXAMINATION DEPARTMENT\n"
            "All final year B.Tech students are hereby informed that the end semester "
            "examinations for Academic Year 2024-25 will commence from 15th May 2025. "
            "Detailed timetable and seating arrangement will be published on the college website. "
            "Hall tickets must be collected from the examination cell before 10th May 2025. "
            "Students with backlogs should contact the examination department."
        ),
    },
    {
        "label": "Academics (English)",
        "expected": "Academics",
        "text": (
            "All students of Third Year Computer Engineering are informed that the "
            "workshop on Machine Learning and AI Applications will be conducted on "
            "25th March 2025 in Seminar Hall 302. Attendance is compulsory. "
            "Students must bring their laptops. The workshop will cover supervised "
            "learning, neural networks, and practical applications in industry."
        ),
    },
    {
        "label": "Admission (English)",
        "expected": "Admission",
        "text": (
            "ADMISSION NOTICE 2024-25\n"
            "Applications are invited for admission to First Year Engineering (B.E./B.Tech) "
            "programs for the academic year 2024-25. Eligible candidates must have passed "
            "HSC examination with Physics, Chemistry, and Mathematics. Admission will be "
            "based on MHT-CET / JEE Main score. Last date for application: 30th June 2025."
        ),
    },
    {
        "label": "Scholarship (English)",
        "expected": "Scholarship",
        "text": (
            "SCHOLARSHIP NOTICE\n"
            "All eligible students belonging to SC/ST/OBC/EBC categories are hereby "
            "informed to apply for government scholarships through the MahaDBT portal. "
            "Scholarship covers tuition fees, examination fees, and maintenance allowance. "
            "Last date for online application: 31st December 2025. "
            "Contact the scholarship cell for assistance."
        ),
    },
    {
        "label": "Other (English)",
        "expected": "Other",
        "text": (
            "NOTICE\n"
            "Students are informed that the college campus will remain closed on "
            "26th January 2025 on account of Republic Day. Normal classes will resume "
            "on 27th January 2025. All students are requested to participate in the "
            "flag hoisting ceremony at 8:00 AM."
        ),
    },
    {
        "label": "Examination (Marathi)",
        "expected": "Examination",
        "text": (
            "सूचना - परीक्षा विभाग\n"
            "सर्व अंतिम वर्ष बी.टेक. विद्यार्थ्यांना कळविण्यात येते की "
            "शैक्षणिक वर्ष २०२४-२५ च्या सत्रांत परीक्षा दिनांक १५ मे २०२५ "
            "पासून सुरू होत आहेत. वेळापत्रक आणि बसण्याची व्यवस्था "
            "महाविद्यालयाच्या वेबसाइटवर प्रसिद्ध केली जाईल."
        ),
    },
    {
        "label": "Scholarship (Marathi)",
        "expected": "Scholarship",
        "text": (
            "शिष्यवृत्ती सूचना\n"
            "सर्व अनुसूचित जाती, अनुसूचित जमाती आणि इतर मागासवर्गीय विद्यार्थ्यांना "
            "कळविण्यात येते की शासकीय शिष्यवृत्तीसाठी महाडीबीटी पोर्टलवर अर्ज करावा. "
            "शिष्यवृत्तीमध्ये शिक्षण शुल्क, परीक्षा शुल्क आणि देखभाल भत्ता समाविष्ट आहे. "
            "अर्ज करण्याची अंतिम तारीख: ३१ डिसेंबर २०२५."
        ),
    },
    {
        "label": "Admission (Mixed En+Mr)",
        "expected": "Admission",
        "text": (
            "ADMISSION NOTICE / प्रवेश सूचना\n"
            "First Year Engineering (B.E.) प्रवेशासाठी अर्ज मागविण्यात येत आहेत. "
            "MHT-CET / JEE Main गुणांवर आधारित प्रवेश दिला जाईल. "
            "Eligible candidates must apply through the Centralized Admission Process. "
            "अंतिम तारीख: ३० जून २०२५."
        ),
    },
]


def run_test_predictions():
    """Run prediction on all sample notices and display results."""

    print("\n" + "=" * 70)
    print("  NOTICE CLASSIFICATION — SAMPLE PREDICTIONS")
    print("=" * 70)

    correct = 0
    total = len(SAMPLE_NOTICES)

    for i, sample in enumerate(SAMPLE_NOTICES, 1):
        print(f"\n  [{i}/{total}] {sample['label']}")
        print(f"  Text: {sample['text'][:100]}...")

        try:
            result = predict_notice_category(sample["text"])

            predicted = result["category"]
            confidence = result["confidence"]
            is_uncertain = result["is_uncertain"]

            # Check correctness (account for "Other/Uncertain" matching "Other")
            expected = sample["expected"]
            is_correct = (
                predicted == expected
                or (predicted == "Other/Uncertain" and expected == "Other")
            )
            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            uncertain_flag = " [UNCERTAIN]" if is_uncertain else ""

            print(f"  Expected:  {expected}")
            print(f"  Predicted: {predicted}{uncertain_flag} (confidence: {confidence:.4f})  {status}")

            # Show top probabilities
            probs = result["probabilities"]
            sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
            print(f"  Probabilities: ", end="")
            print(" | ".join(f"{cat}: {p:.3f}" for cat, p in sorted_probs[:3]))

        except FileNotFoundError as e:
            print(f"  ⚠  Model not found: {e}")
            print(f"     Train the model first: python -m src.classification.trainer")
            return
        except Exception as e:
            print(f"  ⚠  Error: {e}")

    print(f"\n{'='*70}")
    print(f"  RESULTS: {correct}/{total} correct ({correct/total*100:.1f}%)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_test_predictions()
