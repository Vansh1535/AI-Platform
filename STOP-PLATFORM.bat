@echo off
REM AI Platform - Stop All Services (Batch Version)
REM Double-click this file to stop all platform services

echo ============================================
echo    AI Platform - Stopping All Services
echo ============================================
echo.

REM Run the PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "%~dp0stop-platform.ps1"

pause
