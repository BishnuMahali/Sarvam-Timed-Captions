@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: --- TERMINAL ENFORCEMENT ---
if "%WT_SESSION%"=="" (
    where wt.exe >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo [STC] Upgrading to modern terminal...
        start wt.exe -d . cmd /c "%~f0"
        exit /b
    )
)

:: --- SHELL SELECTION ---
set "PS_EXE=powershell.exe"
where pwsh.exe >nul 2>nul
if !ERRORLEVEL! EQU 0 set "PS_EXE=pwsh.exe"

:: --- EXECUTION ---
echo [STC] Starting Sarvam Timed Captions...
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_and_run.ps1"

:: --- SAFETY PAUSE ---
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [STC] An error occurred. Please check the logs above.
)
echo.
echo [STC] Session finished. Press any key to close this window.
pause >nul
