# NoticeLens 🔍

**Multilingual College Notice Understanding System for PCCOE**

NoticeLens is an NLP-powered system that processes college notices (PDF uploads),
extracts structured information, classifies them into categories, and presents
student-friendly summaries in English and simple Marathi.

## Pipeline

```
PDF Upload
  → PDF Text Extraction (PyMuPDF)
  → OCR Fallback (Tesseract)
  → Language Detection (fastText)
  → Notice Classification (XLM-RoBERTa)
  → Information Extraction (OpenAI LLM)
  → Student-Friendly Simplification
  → English / Simple Marathi Output
```

## Notice Categories

| # | Category     |
|---|-------------|
| 1 | Examination  |
| 2 | Academics    |
| 3 | Admission    |
| 4 | Scholarship  |
| 5 | Placement    |
| 6 | Internship   |
| 7 | Event        |
| 8 | General      |
| 9 | Other        |

## Project Structure

```
noticelens/
├── app.py                  # Streamlit application entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md               # Project documentation
│
├── data/
│   ├── raw/                # Uploaded raw PDFs
│   ├── processed/          # Extracted and processed text
│   └── dataset/            # Training/evaluation datasets
│
├── models/                 # Saved model files
│
├── src/
│   ├── pdf/                # PDF text extraction module
│   ├── language/           # Language detection module
│   ├── classification/     # Notice classification module
│   ├── extraction/         # LLM information extraction module
│   ├── simplification/     # Text simplification module
│   ├── database/           # SQLite database module
│   └── utils/              # Shared utilities
│
├── tests/                  # Unit and integration tests
│
└── config/                 # Configuration files
```

## Setup

### Prerequisites

- Python 3.9+
- Tesseract OCR installed on your system
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd NoticeLens
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   copy .env.example .env       # Windows
   # cp .env.example .env       # Linux/Mac
   ```
   Edit `.env` and add your OpenAI API key.

5. **Install Tesseract OCR**
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt install tesseract-ocr`
   - Mac: `brew install tesseract`

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

## Tech Stack

| Component             | Technology                |
|-----------------------|---------------------------|
| Frontend              | Streamlit                 |
| PDF Extraction        | PyMuPDF                   |
| OCR                   | Tesseract (pytesseract)   |
| Language Detection    | fastText                  |
| Classification        | XLM-RoBERTa (HuggingFace) |
| Information Extraction| OpenAI API                |
| Evaluation            | scikit-learn              |
| Database              | SQLite                    |
| Web Scraping (future) | Requests + BeautifulSoup  |

## Development Rules

- Build phase-by-phase; no premature implementation
- No fake/mock AI results in the final application
- No hardcoded classifications
- Never invent information from a notice
- Keep classification and LLM processing as separate modules
- Use environment variables for API keys
- Keep code modular and beginner-readable

## License

This project is developed as an academic mini-project for PCCOE.
