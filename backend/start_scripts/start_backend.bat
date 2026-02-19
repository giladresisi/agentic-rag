@echo off
REM Script to start backend server after killing any existing processes on port 8000
REM Can be run from start_scripts directory

REM Navigate to backend root directory (parent of start_scripts)
cd /d "%~dp0.."

echo === Starting Backend Server ===
echo Working directory: %CD%
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
