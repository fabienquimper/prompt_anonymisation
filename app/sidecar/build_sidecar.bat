@echo off
setlocal

set SCRIPT_DIR=%~dp0
set OUT_DIR=%SCRIPT_DIR%..\src-tauri\binaries

cd /d "%SCRIPT_DIR%"

echo =^> Installing / upgrading dependencies...
pip install -r requirements.txt
if errorlevel 1 goto :error

echo =^> Downloading spaCy model (fr_core_news_sm)...
python -m spacy download fr_core_news_sm
if errorlevel 1 goto :error

echo =^> Building standalone sidecar with PyInstaller...
pyinstaller main.py ^
  --onedir ^
  --name anonymizer-sidecar ^
  --distpath "%OUT_DIR%" ^
  --workpath "%TEMP%\pyinstaller_build" ^
  --specpath "%TEMP%\pyinstaller_spec" ^
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
  --noconfirm
if errorlevel 1 goto :error

echo.
echo [OK] Sidecar built: %OUT_DIR%\anonymizer-sidecar\
echo.
echo Next: cd .. ^&^& npm install ^&^& npm run tauri build
goto :end

:error
echo [ERREUR] La compilation a echoue. Voir les messages ci-dessus.
exit /b 1

:end
endlocal
