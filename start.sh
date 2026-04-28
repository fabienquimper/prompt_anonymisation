#!/usr/bin/env bash
set -e

echo "=== Anonymizer Demo — Traiteur-GPT ==="
echo ""

# Create & activate venv if not present
if [ ! -d ".venv" ]; then
  echo "→ Création de l'environnement virtuel..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "→ Installation des dépendances..."
pip install -q -r requirements.txt

# Download French spaCy model if missing
if ! python -c "import fr_core_news_lg" 2>/dev/null; then
  echo "→ Téléchargement du modèle spaCy français (fr_core_news_lg)..."
  python -m spacy download fr_core_news_lg
fi

echo ""
echo "✓ Tout est prêt. Démarrage du serveur..."
echo "  Ouvrez → http://localhost:8000"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
