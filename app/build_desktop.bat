@echo off
rem ============================================================
rem  Anonymizer Desktop -- Build tout-en-un (Windows)
rem  Usage : cd app && build_desktop.bat
rem ============================================================
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ============================================
echo    Anonymizer Desktop -- Build complet
echo ============================================

rem --- 1. Prerequis ----------------------------------------------------
echo.
echo [1/7] Verification des prerequis...
where /q python
if errorlevel 1 ( echo [ERREUR] Python introuvable -- https://python.org & goto :fail )
where /q node
if errorlevel 1 ( echo [ERREUR] Node.js introuvable -- https://nodejs.org & goto :fail )
where /q npm
if errorlevel 1 ( echo [ERREUR] npm introuvable -- https://nodejs.org & goto :fail )
where /q cargo
if errorlevel 1 ( echo [ERREUR] Rust/cargo introuvable -- https://rustup.rs & goto :fail )
echo [OK] Python, Node.js, npm, Rust detectes

rem --- 2. Environnement Python ------------------------------------------
echo.
echo [2/7] Environnement Python...
rem Venv dans app\.venv (isole du venv web a la racine)
set VENV=%SCRIPT_DIR%.venv
if not exist "%VENV%\Scripts\activate.bat" (
    echo     Creation du venv dans %VENV%...
    python -m venv "%VENV%"
    if errorlevel 1 goto :fail
)
call "%VENV%\Scripts\activate.bat"
echo [OK] venv active : %VENV%

echo     Installation des dependances Python...
pip install -q -r sidecar\requirements.txt
if errorlevel 1 goto :fail
echo [OK] Dependances installees

rem --- 3. Modele spaCy --------------------------------------------------
echo.
echo [3/7] Modele spaCy...
python -c "import fr_core_news_sm" >/dev/null 2>/dev/null
if errorlevel 1 (
    echo     Telechargement de fr_core_news_sm -- environ 15 MB...
    python -m spacy download fr_core_news_sm
    if errorlevel 1 goto :fail
) else (
    echo [OK] fr_core_news_sm deja present
)

rem --- 4. Tauri CLI (Node) ----------------------------------------------
echo.
echo [4/7] Tauri CLI...
call npm install --silent
if errorlevel 1 goto :fail
echo [OK] @tauri-apps/cli installe

rem --- 5. Icones --------------------------------------------------------
echo.
echo [5/7] Icones de l'application...
if not exist "src-tauri\icons\" (
    echo     Generation d'une icone placeholder...
    set ICON_TMP=%TEMP%\anon_icon_placeholder.png
    python sidecar\make_icon.py "%ICON_TMP%"
    if errorlevel 1 goto :fail
    node_modules\.bin\tauri.cmd icon "%ICON_TMP%"
    if errorlevel 1 goto :fail
    del /f /q "%ICON_TMP%" >/dev/null 2>/dev/null
    echo [OK] Icones generees dans src-tauri\icons\
    echo      Pour des icones perso : node_modules\.bin\tauri.cmd icon votre-logo-1024.png
) else (
    echo [OK] Icones deja presentes dans src-tauri\icons\
)

rem --- 6. Sidecar PyInstaller -------------------------------------------
echo.
echo [6/7] Compilation du sidecar Python ^(PyInstaller^)...
echo     Etape la plus longue : 5 a 15 minutes selon la machine.
echo.

rem Determine le triple Rust pour nommer le binaire (ex: x86_64-pc-windows-msvc)
for /f "tokens=2 delims= " %%i in ('rustc -vV ^| findstr /B "host:"') do set TARGET_TRIPLE=%%i
set SIDECAR_NAME=anonymizer-sidecar-%TARGET_TRIPLE%

rem Supprime l'ancienne version pour repartir proprement
if exist "src-tauri\binaries\anonymizer-sidecar\" rd /s /q "src-tauri\binaries\anonymizer-sidecar"
if exist "src-tauri\binaries\%SIDECAR_NAME%.exe" del /f /q "src-tauri\binaries\%SIDECAR_NAME%.exe"

pyinstaller sidecar\main.py ^
    --onefile ^
    --name anonymizer-sidecar ^
    --distpath src-tauri\binaries ^
    --workpath "%TEMP%\pyi_anon_build" ^
    --specpath "%TEMP%\pyi_anon_spec" ^
    --collect-all spacy ^
    --collect-all fr_core_news_sm ^
    --collect-all presidio_analyzer ^
    --collect-all presidio_anonymizer ^
    --collect-all scrubadub ^
    --collect-all faker ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --clean ^
    --noconfirm ^
    --log-level WARN

if errorlevel 1 goto :fail

rem Tauri externalBin exige le triple Rust dans le nom du binaire
rename "src-tauri\binaries\anonymizer-sidecar.exe" "%SIDECAR_NAME%.exe"
if errorlevel 1 goto :fail

echo [OK] Sidecar compile : src-tauri\binaries\%SIDECAR_NAME%.exe

rem --- 7. Build Tauri ---------------------------------------------------
echo.
echo [7/7] Build Tauri ^(compilation Rust^)...
echo     Premiere compilation ~5 min ^(mise en cache ensuite^).
echo.
npm run tauri build
if errorlevel 1 goto :fail

rem --- Resume ----------------------------------------------------------
echo.
echo ============================================
echo    BUILD TERMINE AVEC SUCCES
echo ============================================
echo.
echo Installateurs dans :
echo   %SCRIPT_DIR%src-tauri\target\release\bundle\
echo.
for /r "%SCRIPT_DIR%src-tauri\target\release\bundle" %%f in (*.exe *.msi) do (
    echo   %%f
)
echo.
goto :end

:fail
echo.
echo ============================================
echo    ECHEC -- Consultez les messages ci-dessus
echo    Aide : app\BUILD.md
echo ============================================
exit /b 1

:end
endlocal
