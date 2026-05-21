#!/usr/bin/env bash
# ============================================================
#  Anonymizer Desktop — Build tout-en-un (macOS / Linux)
#  Usage : cd app && ./build_desktop.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

step() { echo ""; echo "──────────────────────────────────────"; echo "▶  $1"; echo "──────────────────────────────────────"; }
ok()   { echo "   ✓ $1"; }
err()  { echo ""; echo "[ERREUR] $1" >&2; echo "         Voir app/BUILD.md → Prérequis" >&2; exit 1; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Anonymizer Desktop — Build complet    ║"
echo "╚══════════════════════════════════════════╝"

# ── 1. Prérequis ─────────────────────────────────────────────────────────────
step "Vérification des prérequis"
command -v python3 &>/dev/null || err "Python 3 introuvable — https://python.org"

# Bibliothèques système Linux (GTK/WebKit/GLib) requises par Tauri
if [[ "$(uname)" == "Linux" ]] && command -v apt-get &>/dev/null; then
    MISSING_LIBS=()
    pkg-config --exists glib-2.0        2>/dev/null || MISSING_LIBS+=(libwebkit2gtk-4.1-dev)
    pkg-config --exists webkit2gtk-4.1  2>/dev/null || MISSING_LIBS+=(libwebkit2gtk-4.1-dev)
    pkg-config --exists openssl         2>/dev/null || MISSING_LIBS+=(libssl-dev)
    pkg-config --exists gtk+-3.0        2>/dev/null || MISSING_LIBS+=(libgtk-3-dev)
    pkg-config --exists librsvg-2.0     2>/dev/null || MISSING_LIBS+=(librsvg2-dev)
    if [ ${#MISSING_LIBS[@]} -gt 0 ]; then
        # Déduplique
        MISSING_LIBS=($(printf '%s\n' "${MISSING_LIBS[@]}" | sort -u))
        echo "   Bibliothèques système manquantes — installation via apt..."
        sudo apt-get install -y pkg-config "${MISSING_LIBS[@]}" \
            libayatana-appindicator3-dev 2>/dev/null || true
        ok "Bibliothèques système installées"
    else
        ok "Bibliothèques système Linux OK"
    fi
fi

command -v node &>/dev/null || err "Node.js introuvable — https://nodejs.org"
command -v npm  &>/dev/null || err "npm introuvable — https://nodejs.org"

# Rust : cargo peut exister sans toolchain par défaut (rustup sans 'stable')
if ! cargo --version &>/dev/null; then
    if command -v rustup &>/dev/null; then
        echo "   Rustup trouvé mais pas de toolchain, installation de stable..."
        rustup default stable
    else
        err "Rust/cargo introuvable — https://rustup.rs"
    fi
fi
PYTHON=python3
ok "Python 3 : $(python3 --version)"
ok "Node.js  : $(node --version)"
ok "npm      : $(npm --version)"
ok "Rust     : $(cargo --version)"

# ── 2. Environnement Python ───────────────────────────────────────────────────
step "Environnement Python"
VENV="$ROOT_DIR/.venv"
if [ ! -f "$VENV/bin/activate" ]; then
    echo "   Création du venv..."
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
PYTHON=python
ok "venv activé : $VENV"

echo "   Installation des dépendances Python..."
pip install -q -r sidecar/requirements.txt
ok "Dépendances OK"

# ── 3. Modèle spaCy ──────────────────────────────────────────────────────────
step "Modèle spaCy"
if ! python -c "import fr_core_news_sm" 2>/dev/null; then
    echo "   Téléchargement de fr_core_news_sm (~15 MB)..."
    python -m spacy download fr_core_news_sm
else
    ok "fr_core_news_sm déjà présent"
fi

# ── 4. Tauri CLI via cargo ────────────────────────────────────────────────────
# On utilise cargo install tauri-cli plutôt que npm :
# npm ne peut pas installer les native bindings sur un filesystem NTFS (WSL /mnt/c/)
step "Tauri CLI"
if cargo tauri --version &>/dev/null 2>&1; then
    ok "Tauri CLI déjà installé : $(cargo tauri --version)"
else
    echo "   Installation via cargo (5-10 min, une seule fois)..."
    cargo install tauri-cli --version "^2" --locked
    ok "Tauri CLI installé : $(cargo tauri --version)"
fi

# ── 5. Icônes ─────────────────────────────────────────────────────────────────
step "Icônes de l'application"
ICONS_DIR="src-tauri/icons"
if [ ! -d "$ICONS_DIR" ] || [ -z "$(ls -A "$ICONS_DIR" 2>/dev/null)" ]; then
    echo "   Génération d'une icône placeholder..."
    ICON_TMP="$(mktemp /tmp/anon_icon_XXXX.png)"
    python sidecar/make_icon.py "$ICON_TMP"
    cargo tauri icon "$ICON_TMP"
    rm -f "$ICON_TMP"
    ok "Icônes générées dans $ICONS_DIR/"
    echo "   💡 Pour des icônes personnalisées : cargo tauri icon votre-logo-1024.png"
else
    ok "Icônes déjà présentes dans $ICONS_DIR/"
fi

# ── 6. Sidecar Python (PyInstaller) ──────────────────────────────────────────
step "Compilation du sidecar Python (PyInstaller — 5 à 15 min)"
echo "   Patience, c'est la plus longue étape..."

# Détermine le triple Rust de la cible courante (ex: x86_64-unknown-linux-gnu)
TARGET_TRIPLE=$(rustc -vV | grep '^host:' | cut -d' ' -f2)
SIDECAR_NAME="anonymizer-sidecar-$TARGET_TRIPLE"

# Supprime l'ancienne version pour repartir proprement
rm -rf "src-tauri/binaries/anonymizer-sidecar"
rm -f  "src-tauri/binaries/$SIDECAR_NAME"

pyinstaller sidecar/main.py \
    --onefile \
    --name anonymizer-sidecar \
    --distpath /tmp/pyi_dist \
    --workpath /tmp/pyi_anon_build \
    --specpath /tmp/pyi_anon_spec \
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
    --noconfirm \
    --log-level WARN

# Copie depuis /tmp (Linux natif) vers NTFS — évite les écritures lentes sur /mnt/c/
cp /tmp/pyi_dist/anonymizer-sidecar "src-tauri/binaries/$SIDECAR_NAME"
ok "Sidecar compile -> src-tauri/binaries/$SIDECAR_NAME"

# ── 7. Build Tauri ────────────────────────────────────────────────────────────
step "Build Tauri (compilation Rust)"
cargo tauri build

# ── Résumé ────────────────────────────────────────────────────────────────────
BUNDLE="$SCRIPT_DIR/src-tauri/target/release/bundle"
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          ✓  BUILD TERMINÉ                ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Installateurs :"
find "$BUNDLE" -maxdepth 2 \( \
    -name "*.dmg" -o -name "*.app" \
    -o -name "*.AppImage" -o -name "*.deb" \
    -o -name "*.exe" -o -name "*.msi" \
    \) 2>/dev/null | sort | while read -r f; do
    SIZE=$(du -sh "$f" 2>/dev/null | cut -f1)
    echo "  [$SIZE]  $f"
done
echo ""
