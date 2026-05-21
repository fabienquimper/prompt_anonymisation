@echo off
rem ============================================================
rem  Anonymizer Desktop -- Mode developpement (hot-reload)
rem  Lance le sidecar Python + Tauri dev
rem  Usage : cd app && dev_desktop.bat
rem ============================================================
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set VENV=%ROOT_DIR%\.venv
cd /d "%SCRIPT_DIR%"

rem ── Venv ─────────────────────────────────────────────────────────────────────
if not exist "%VENV%\Scripts\activate.bat" (
    echo [ERREUR] venv introuvable : %VENV%
    echo          Lancez d'abord : build_desktop.bat
    exit /b 1
)
call "%VENV%\Scripts\activate.bat"

rem ── Sidecar Python (fenetre separee) ─────────────────────────────────────────
echo [1/2] Demarrage du sidecar Python sur le port 8765...
start "Anonymizer Sidecar" python sidecar\main.py --port 8765

rem Attendre un peu que le sidecar demarre
timeout /t 3 /nobreak >nul

rem ── Tauri dev ─────────────────────────────────────────────────────────────────
echo [2/2] Lancement de Tauri en mode dev (hot-reload)...
echo        Modifiez index.html ou frontend\* : la fenetre se recharge automatiquement.
echo.
cargo tauri dev

endlocal
