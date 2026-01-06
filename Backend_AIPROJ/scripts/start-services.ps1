# Enterprise Project - Service Startup Script
# Starts Redis, Celery Worker, and FastAPI Server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Enterprise Project - Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get the project root directory
$ProjectRoot = $PSScriptRoot

# Function to start a service in a new window
function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$Command,
        [string]$WorkingDirectory
    )
    Write-Host "Starting $Title..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WorkingDirectory'; Write-Host '$Title' -ForegroundColor Yellow; $Command"
}

# 1. Start Redis Server
Write-Host "[1/3] Redis Server" -ForegroundColor Yellow
$RedisPath = Join-Path $ProjectRoot "Redis"
if (Test-Path $RedisPath) {
    Start-ServiceWindow -Title "Redis Server" -Command "cd '$RedisPath'; .\redis-server.exe" -WorkingDirectory $RedisPath
    Start-Sleep -Seconds 2
} else {
    Write-Host "  ⚠️  Redis folder not found at: $RedisPath" -ForegroundColor Red
}

# 2. Start Celery Worker
Write-Host "[2/3] Celery Worker" -ForegroundColor Yellow
$CeleryCommand = ".\.venv\Scripts\Activate.ps1; celery -A src.workers.celery_app worker --pool=solo --loglevel=info"
Start-ServiceWindow -Title "Celery Worker" -Command $CeleryCommand -WorkingDirectory $ProjectRoot
Start-Sleep -Seconds 2

# 3. Start FastAPI Server
Write-Host "[3/3] FastAPI Server" -ForegroundColor Yellow
$FastAPICommand = ".\.venv\Scripts\python.exe -m uvicorn src.main:app --reload"
Start-ServiceWindow -Title "FastAPI Server" -Command $FastAPICommand -WorkingDirectory $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running in separate windows:" -ForegroundColor White
Write-Host "  • Redis Server      (port 6379)" -ForegroundColor Gray
Write-Host "  • Celery Worker     (background tasks)" -ForegroundColor Gray
Write-Host "  • FastAPI Server    (http://localhost:8000)" -ForegroundColor Gray
Write-Host ""
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
