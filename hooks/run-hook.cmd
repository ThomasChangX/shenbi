@echo off
REM Windows polyglot wrapper for shenbi hooks
REM Auto-detects bash (Git for Windows / WSL) and delegates
where bash >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    bash "%~dp0session-start" %*
) else (
    echo Shenbi hooks require bash (install Git for Windows or WSL)
    exit /b 1
)
