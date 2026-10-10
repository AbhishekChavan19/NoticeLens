FROM python:3.11-slim

# Prevent python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies including Tesseract with Marathi & English OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-mar \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application code and model artifacts
COPY src/ ./src/
COPY api/ ./api/
COPY config/ ./config/
COPY models/ ./models/
COPY data/dataset/notices.csv ./data/dataset/notices.csv

# Train baseline model inside container for 100% environment compatibility
RUN python -c "from src.classification.baseline import BaselineClassifier; import pandas as pd; from src.classification.config import LABEL2ID; df = pd.read_csv('data/dataset/notices.csv').dropna(subset=['text', 'category']); df['label'] = df['category'].map(LABEL2ID); b = BaselineClassifier(); b.train(df['text'].tolist(), df['label'].tolist()); b.save()"

EXPOSE 8000

# Start Uvicorn with dynamic PORT support
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
