#!/usr/bin/env bash
# ============================================================
#  Anonymizer Desktop — Lancer l'app déjà compilée
#  Usage : cd app && ./run_desktop.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="$SCRIPT_DIR/src-tauri/target/release/anonymizer"

if [ ! -f "$BINARY" ]; then
    echo "[ERREUR] Binaire introuvable : $BINARY"
    echo "         Lancez d'abord : ./build_desktop.sh"
    exit 1
fi

# WSL : avertir si pas de serveur d'affichage détecté
if grep -qi microsoft /proc/version 2>/dev/null; then
    if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
        echo "[INFO] WSL sans DISPLAY détecté. Si la fenêtre ne s'ouvre pas :"
        echo "       Windows 11 + WSLg  → devrait fonctionner automatiquement"
        echo "       Windows 10 (VcXsrv) → export DISPLAY=:0"
        echo ""
    fi
fi

exec "$BINARY"
