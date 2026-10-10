@echo off
title NoticeLens FastAPI Backend
echo Starting NoticeLens Backend on http://0.0.0.0:8000 ...
cd /d "c:\Desktop\NLP-Lab\NoticeLens"
call venv\Scripts\activate.bat
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
pause
