"""
NoticeLens Configuration

Central configuration constants and settings for the application.
"""

# Notice categories used across the application
NOTICE_CATEGORIES = [
    "Examination",
    "Academics",
    "Admission",
    "Scholarship",
    "Placement",
    "Internship",
    "Event",
    "General",
    "Other",
]

# Number of categories
NUM_CATEGORIES = len(NOTICE_CATEGORIES)

# Category to index mapping
CATEGORY_TO_INDEX = {cat: idx for idx, cat in enumerate(NOTICE_CATEGORIES)}

# Index to category mapping
INDEX_TO_CATEGORY = {idx: cat for idx, cat in enumerate(NOTICE_CATEGORIES)}
