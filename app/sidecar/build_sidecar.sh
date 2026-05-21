#!/usr/bin/env bash
# Build the Python sidecar for macOS / Linux
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/../src-tauri/binaries"

cd "$SCRIPT_DIR"

echo "==> Installing / upgrading dependencies..."
pip install -r requirements.txt

echo "==> Downloading spaCy model (fr_core_news_sm)..."
python -m spacy download fr_core_news_sm

echo "==> Building standalone sidecar with PyInstaller..."
pyinstaller main.py \
  --onedir \
  --name anonymizer-sidecar \
  --distpath "$OUT_DIR" \
  --workpath /tmp/pyinstaller_build \
  --specpath /tmp/pyinstaller_spec \
  --collect-all spacy \
  --collect-all fr_core_news_sm \
  --collect-all presidio_analyzer \
  --collect-all presidio_anonymizer \
  --collect-all scrubadub \
  --collect-all faker \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  --clean \
  --noconfirm

echo ""
echo "✓ Sidecar built: $OUT_DIR/anonymizer-sidecar/"
echo ""
echo "Next: cd .. && npm install && npm run tauri build"
