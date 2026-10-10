"""
Classification Configuration and Constants for NoticeLens (Phase 4)
"""

import os
import torch
from config.settings import NOTICE_CATEGORIES

# Default Model Architecture
MODEL_NAME = "xlm-roberta-base"

# Label Mappings (0-indexed for PyTorch/Transformers)
CATEGORIES = NOTICE_CATEGORIES
LABEL2ID = {cat: i for i, cat in enumerate(CATEGORIES)}
ID2LABEL = {i: cat for i, cat in enumerate(CATEGORIES)}
NUM_LABELS = len(CATEGORIES)

# Model Output Directories
MODEL_SAVE_DIR = "models/notice_classifier"
BASELINE_SAVE_DIR = "models/baseline_svm"
EVALUATION_RESULTS_PATH = os.path.join(MODEL_SAVE_DIR, "evaluation_results.json")

# Default Hyperparameters (Optimized for standard student laptop / CPU execution)
DEFAULT_MAX_LENGTH = 256
DEFAULT_BATCH_SIZE = 4 if not torch.cuda.is_available() else 16
DEFAULT_EPOCHS = 4
DEFAULT_LEARNING_RATE = 2e-5
DEFAULT_WEIGHT_DECAY = 0.01
DEFAULT_CONFIDENCE_THRESHOLD = 0.50

# Device Detection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
