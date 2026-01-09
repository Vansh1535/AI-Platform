# AI Platform - Full Stack Startup Script
# Starts Backend (FastAPI + Redis + Celery) and Frontend (Next.js) simultaneously

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   AI Platform - Starting Full Stack" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get paths
$RootPath = $PSScriptRoot
$BackendPath = Join-Path $RootPath "Backend_AIPROJ"
$FrontendPath = Join-Path $RootPath "Frontend_AIPROJ"
$RedisPath = Join-Path $BackendPath "Redis"

# Function to start a service in a new window
function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$Command,
        [string]$WorkingDirectory,
        [string]$Color = "Yellow"
    )
    Write-Host "Starting $Title..." -ForegroundColor Green
    $TitleCommand = "Write-Host '=====================================' -ForegroundColor $Color; Write-Host '  $Title' -ForegroundColor $Color; Write-Host '=====================================' -ForegroundColor $Color; Write-Host ''"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WorkingDirectory'; $TitleCommand; $Command"
}

# Check if directories exist
if (-not (Test-Path $BackendPath)) {
    Write-Host "❌ Backend directory not found: $BackendPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $FrontendPath)) {
    Write-Host "❌ Frontend directory not found: $FrontendPath" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Backend:  $BackendPath" -ForegroundColor Gray
Write-Host "📁 Frontend: $FrontendPath" -ForegroundColor Gray
Write-Host ""

# 1. Start Redis Server
Write-Host "[1/5] Starting Redis Server..." -ForegroundColor Yellow
if (Test-Path $RedisPath) {
    Start-ServiceWindow -Title "Redis Server (Port 6379)" -Command ".\redis-server.exe" -WorkingDirectory $RedisPath -Color "Magenta"
    Start-Sleep -Seconds 2
    Write-Host "✅ Redis Server started" -ForegroundColor Green
} else {
    Write-Host "⚠️  Redis folder not found at: $RedisPath" -ForegroundColor Yellow
    Write-Host "   Backend caching will be disabled" -ForegroundColor Gray
}

# 2. Start Celery Worker
Write-Host "[2/5] Starting Celery Worker..." -ForegroundColor Yellow
$CeleryCommand = "if (Test-Path '.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1; celery -A app.workers.celery_app worker --pool=solo --loglevel=info } else { Write-Host 'Virtual environment not found!' -ForegroundColor Red; Read-Host 'Press Enter to exit' }"
Start-ServiceWindow -Title "Celery Worker" -Command $CeleryCommand -WorkingDirectory $BackendPath -Color "Cyan"
Start-Sleep -Seconds 3
Write-Host "✅ Celery Worker started" -ForegroundColor Green

# 3. Start FastAPI Backend
Write-Host "[3/5] Starting FastAPI Backend..." -ForegroundColor Yellow
$BackendCommand = "if (Test-Path '.venv\Scripts\python.exe') { .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 } else { Write-Host 'Virtual environment not found! Run: python -m venv .venv' -ForegroundColor Red; Read-Host 'Press Enter to exit' }"
Start-ServiceWindow -Title "FastAPI Backend (Port 8000)" -Command $BackendCommand -WorkingDirectory $BackendPath -Color "Green"
Start-Sleep -Seconds 5
Write-Host "✅ FastAPI Backend started" -ForegroundColor Green

# 4. Start Next.js Frontend
Write-Host "[4/5] Starting Next.js Frontend..." -ForegroundColor Yellow
$FrontendCommand = "if (Test-Path 'node_modules') { npm run dev } else { Write-Host 'Dependencies not installed! Run: npm install' -ForegroundColor Red; Read-Host 'Press Enter to exit' }"
Start-ServiceWindow -Title "Next.js Frontend (Port 3001)" -Command $FrontendCommand -WorkingDirectory $FrontendPath -Color "Blue"
Start-Sleep -Seconds 5
Write-Host "✅ Next.js Frontend started" -ForegroundColor Green

# 5. Wait for backend to be ready
Write-Host "[5/5] Waiting for services to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$backendReady = $false

while (-not $backendReady -and $attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "Backend is ready!" -ForegroundColor Green
        }
    } catch {
        $attempt++
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
}

if (-not $backendReady) {
    Write-Host ""
    Write-Host "Warning: Backend may not be fully ready yet. Check the FastAPI window." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   🚀 All Services Started!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running in separate windows:" -ForegroundColor White
Write-Host "  • Redis Server      → Port 6379" -ForegroundColor Magenta
Write-Host "  • Celery Worker     → Background tasks" -ForegroundColor Cyan
Write-Host "  • FastAPI Backend   → http://localhost:8000" -ForegroundColor Green
Write-Host "  • Next.js Frontend  → http://localhost:3000" -ForegroundColor Blue
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor White
Write-Host "  • Swagger UI → http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  • ReDoc      → http://localhost:8000/redoc" -ForegroundColor Gray
Write-Host ""
Write-Host "Admin Login:" -ForegroundColor White
Write-Host "  • Username: admin" -ForegroundColor Gray
Write-Host "  • Password: SecureAdmin123!" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "   Close all PowerShell windows or press Ctrl+C in each" -ForegroundColor Gray
Write-Host ""

# Open browser
Write-Host "Opening frontend in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3001"

Write-Host ""
Write-Host "Platform is ready for testing!" -ForegroundColor Green
Write-Host ""
Write-Host "Press Enter to close this window..." -ForegroundColor Yellow
Read-Host
