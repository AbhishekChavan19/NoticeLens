"""
Classification Configuration and Constants for NoticeLens (Phase 4)
"""

import os

try:
    import torch
    TORCH_AVAILABLE = True
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
    HAS_CUDA = False

from pathlib import Path
from config.settings import NOTICE_CATEGORIES

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Default Model Architecture
MODEL_NAME = "xlm-roberta-base"

# Label Mappings (0-indexed for PyTorch/Transformers)
CATEGORIES = NOTICE_CATEGORIES
LABEL2ID = {cat: i for i, cat in enumerate(CATEGORIES)}
ID2LABEL = {i: cat for i, cat in enumerate(CATEGORIES)}
NUM_LABELS = len(CATEGORIES)

# Model Output Directories
MODEL_SAVE_DIR = str(ROOT_DIR / "models" / "notice_classifier")
BASELINE_SAVE_DIR = str(ROOT_DIR / "models" / "baseline_svm")
EVALUATION_RESULTS_PATH = os.path.join(MODEL_SAVE_DIR, "evaluation_results.json")

# Default Hyperparameters (Optimized for standard student laptop / CPU execution)
DEFAULT_MAX_LENGTH = 256
DEFAULT_BATCH_SIZE = 16 if HAS_CUDA else 4
DEFAULT_EPOCHS = 4
DEFAULT_LEARNING_RATE = 2e-5
DEFAULT_WEIGHT_DECAY = 0.01
DEFAULT_CONFIDENCE_THRESHOLD = 0.35

# Device Detection
DEVICE = "cuda" if HAS_CUDA else "cpu"

