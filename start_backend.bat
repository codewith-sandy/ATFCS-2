@echo off
echo Starting Adaptive Traffic Management Backend...
cd /d "%~dp0"
call traffic_ai_env\Scripts\activate.bat
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
