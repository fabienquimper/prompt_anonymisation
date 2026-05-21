#!/usr/bin/env bash
# ============================================================
#  Anonymizer Desktop — Mode développement (hot-reload)
#  Lance le sidecar Python + Tauri dev en un seul terminal
#  Usage : cd app && ./dev_desktop.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$ROOT_DIR/.venv"
cd "$SCRIPT_DIR"

# ── Venv ──────────────────────────────────────────────────────────────────────
if [ ! -f "$VENV/bin/activate" ]; then
    echo "[ERREUR] venv introuvable ($VENV)"
    echo "         Lancez d'abord : ./build_desktop.sh"
    exit 1
fi
source "$VENV/bin/activate"

# ── Sidecar Python ────────────────────────────────────────────────────────────
echo "▶ Démarrage du sidecar Python sur le port 8765..."
python sidecar/main.py --port 8765 &
SIDECAR_PID=$!

# Arrêter le sidecar proprement à la sortie (Ctrl+C ou fin de tauri dev)
cleanup() {
    echo ""
    echo "▶ Arrêt du sidecar (PID $SIDECAR_PID)..."
    kill "$SIDECAR_PID" 2>/dev/null || true
    wait "$SIDECAR_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Attendre que le port 8765 réponde (max 30 s)
echo "   En attente du sidecar..."
for i in $(seq 1 60); do
    if (echo > /dev/tcp/localhost/8765) 2>/dev/null; then
        echo "   ✓ Sidecar prêt"
        break
    fi
    if ! kill -0 "$SIDECAR_PID" 2>/dev/null; then
        echo "[ERREUR] Le sidecar s'est arrêté prématurément."
        echo "         Relancez avec : python sidecar/main.py --port 8765"
        exit 1
    fi
    sleep 0.5
done

# ── Tauri dev ─────────────────────────────────────────────────────────────────
echo "▶ Lancement de Tauri en mode dev (hot-reload)..."
echo "   Modifiez index.html ou frontend/* : la fenêtre se recharge automatiquement."
echo ""
cargo tauri dev
