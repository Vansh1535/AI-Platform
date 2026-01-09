# AI Platform - Stop All Services Script
# Stops all running platform services

Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "   AI Platform - Stopping All Services" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

# Function to stop processes by name
function Stop-ServiceByName {
    param(
        [string]$ProcessName,
        [string]$DisplayName
    )
    
    $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "Stopping $DisplayName..." -ForegroundColor Yellow
        $processes | Stop-Process -Force
        Write-Host "✅ $DisplayName stopped ($($processes.Count) process(es))" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  $DisplayName not running" -ForegroundColor Gray
    }
}

# Function to stop processes by port
function Stop-ServiceByPort {
    param(
        [int]$Port,
        [string]$DisplayName
    )
    
    Write-Host "Checking $DisplayName (Port $Port)..." -ForegroundColor Yellow
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connection) {
        $processId = $connection.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $processId -Force
            Write-Host "✅ $DisplayName stopped (PID: $processId)" -ForegroundColor Green
        }
    } else {
        Write-Host "ℹ️  $DisplayName not running on port $Port" -ForegroundColor Gray
    }
}

# Stop services
Write-Host "[1/5] Stopping Next.js Frontend..." -ForegroundColor Cyan
Stop-ServiceByName -ProcessName "node" -DisplayName "Next.js Frontend"

Write-Host ""
Write-Host "[2/5] Stopping FastAPI Backend..." -ForegroundColor Cyan
Stop-ServiceByName -ProcessName "python" -DisplayName "FastAPI Backend"
Stop-ServiceByName -ProcessName "uvicorn" -DisplayName "Uvicorn"

Write-Host ""
Write-Host "[3/5] Stopping Celery Worker..." -ForegroundColor Cyan
Stop-ServiceByName -ProcessName "celery" -DisplayName "Celery Worker"

Write-Host ""
Write-Host "[4/5] Stopping Redis Server..." -ForegroundColor Cyan
Stop-ServiceByName -ProcessName "redis-server" -DisplayName "Redis Server"

Write-Host ""
Write-Host "[5/5] Checking ports..." -ForegroundColor Cyan
Stop-ServiceByPort -Port 3001 -DisplayName "Frontend (3001)"
Stop-ServiceByPort -Port 8000 -DisplayName "Backend (8000)"
Stop-ServiceByPort -Port 6379 -DisplayName "Redis (6379)"

Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "   🛑 All Services Stopped!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Red
Write-Host ""

Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
