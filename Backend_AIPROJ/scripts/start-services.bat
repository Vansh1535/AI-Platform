@echo off
REM Enterprise Project - Service Startup Script (Batch Version)
REM Starts Redis, Celery Worker, and FastAPI Server

echo ========================================
echo   Enterprise Project - Starting Services
echo ========================================
echo.

REM Get the project root directory
cd /d "%~dp0"

REM 1. Start Redis Server
echo [1/3] Starting Redis Server...
if exist "Redis\redis-server.exe" (
    start "Redis Server" cmd /k "cd Redis && redis-server.exe"
    timeout /t 2 /nobreak >nul
) else (
    echo   Warning: Redis folder not found
)

REM 2. Start Celery Worker
echo [2/3] Starting Celery Worker...
start "Celery Worker" cmd /k ".venv\Scripts\activate.bat && celery -A src.workers.celery_app worker --pool=solo --loglevel=info"
timeout /t 2 /nobreak >nul

REM 3. Start FastAPI Server
echo [3/3] Starting FastAPI Server...
start "FastAPI Server" cmd /k ".venv\Scripts\activate.bat && python -m uvicorn src.main:app --reload"

echo.
echo ========================================
echo   All services started!
echo ========================================
echo.
echo Services running in separate windows:
echo   - Redis Server      (port 6379)
echo   - Celery Worker     (background tasks)
echo   - FastAPI Server    (http://localhost:8000)
echo.
echo API Documentation: http://localhost:8000/docs
echo.
pause

.\start-services.bat
