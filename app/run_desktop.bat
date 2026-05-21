@echo off
rem ============================================================
rem  Anonymizer Desktop -- Lancer l'app deja compilee (Windows)
rem  Usage : cd app && run_desktop.bat
rem ============================================================

set SCRIPT_DIR=%~dp0
set BINARY=%SCRIPT_DIR%src-tauri\target\release\anonymizer.exe

if not exist "%BINARY%" (
    echo [ERREUR] Binaire introuvable : %BINARY%
    echo          Lancez d'abord : build_desktop.bat
    exit /b 1
)

start "" "%BINARY%"
