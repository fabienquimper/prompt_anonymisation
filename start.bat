@echo off
echo === Anonymizer Demo - Traiteur-GPT ===
echo.

REM Create venv if not present
if not exist ".venv" (
    echo ^> Creation de l'environnement virtuel...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo ^> Installation des dependances...
pip install -q -r requirements.txt

REM Download French spaCy model if missing
python -c "import fr_core_news_lg" 2>nul
if errorlevel 1 (
    echo ^> Telechargement du modele spaCy francais (fr_core_news_lg)...
    python -m spacy download fr_core_news_lg
)

echo.
echo OK Tout est pret. Demarrage du serveur...
echo   Ouvrez ^> http://localhost:8000
echo.

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
