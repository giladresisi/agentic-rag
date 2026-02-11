@echo off
REM Script to start backend server after killing any existing processes on port 8000

echo === Starting Backend Server ===
echo.

echo Killing all Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul

echo.
echo Waiting 2 seconds for processes to terminate...
timeout /t 2 /nobreak >nul

echo.
echo [OK] Python processes cleared
echo.

echo Starting uvicorn server on port 8000...
echo Press Ctrl+C to stop
echo.

REM Activate venv and start server
call venv\Scripts\activate.bat
uvicorn main:app --reload --port 8000
