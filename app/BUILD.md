# Build guide — Anonymizer Desktop (Tauri 2)

## Architecture

```
app/
├── index.html            ← Interface web (chargée par Tauri)
├── package.json          ← Tauri CLI
├── sidecar/              ← Serveur Python FastAPI
│   ├── main.py           ← Logique d'anonymisation (4 techniques)
│   ├── build_sidecar.sh  ← Compile le sidecar (macOS/Linux)
│   └── build_sidecar.bat ← Compile le sidecar (Windows)
└── src-tauri/            ← Shell natif Rust
    ├── binaries/         ← Sidecar compilé (généré par l'étape 2)
    └── src/lib.rs        ← Lance le sidecar au démarrage, le tue à la fermeture
```

Au lancement : Tauri démarre le sidecar Python sur `localhost:8765`, puis ouvre
une fenêtre native qui charge `index.html`. La fenêtre se connecte à l'API dès
que le serveur est prêt (retry automatique pendant ~30 s).

---

## WSL (Windows Subsystem for Linux)

> **Important** : si tu travailles depuis WSL sur `/mnt/c/`, la commande
> `./build_desktop.sh` produit des binaires **Linux** (AppImage / .deb).
> Pour un `.exe` Windows, utilise `build_desktop.bat` depuis **PowerShell natif**.
>
> Le script utilise `cargo install tauri-cli` (pas npm) car npm ne peut pas
> installer les native bindings sur un filesystem NTFS monté sous WSL.

---

## Prérequis

| Outil | Version | Lien |
|-------|---------|------|
| Rust + cargo | stable | https://rustup.rs |
| Python | ≥ 3.10 | https://python.org |
| Libs système (Linux) | — | `sudo apt install libwebkit2gtk-4.1-dev libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev` |
| Xcode CLI (macOS) | — | `xcode-select --install` |
| Build Tools (Windows) | — | Visual C++ Build Tools 2022 |

---

## Étape 1 — Icônes (une seule fois)

Fournissez une image source 1024×1024 PNG (logo, ou n'importe quelle image) :

```bash
cd app
npm install
npm run tauri icon path/vers/votre-logo.png
```

Cela génère automatiquement `src-tauri/icons/` (PNG, ICO, ICNS).

---

## Étape 2 — Compiler le sidecar Python

**Windows :**
```bat
cd app\sidecar
build_sidecar.bat
```

**macOS / Linux :**
```bash
cd app/sidecar
./build_sidecar.sh
```

Le script :
1. Installe les dépendances Python (presidio, spaCy, scrubadub, faker…)
2. Télécharge le modèle `fr_core_news_sm` (~15 MB)
3. Compile un bundle autonome dans `app/src-tauri/binaries/anonymizer-sidecar/`

> **Taille du bundle sidecar** : ~200–300 MB (Python + spaCy + toutes les libs).
> Pour un bundle plus petit, remplacez `fr_core_news_sm` par rien et acceptez
> le mode dégradé (Presidio en anglais uniquement).

---

## Étape 3 — Build Tauri

```bash
cd app
npm install          # installe @tauri-apps/cli (première fois seulement)
npm run tauri build
```

Les binaires finaux se trouvent dans `app/src-tauri/target/release/bundle/` :

| Plateforme | Format | Chemin |
|------------|--------|--------|
| Windows | `.exe` + `.msi` | `bundle/nsis/` et `bundle/msi/` |
| macOS | `.app` + `.dmg` | `bundle/macos/` et `bundle/dmg/` |
| Linux | `.AppImage` + `.deb` | `bundle/appimage/` et `bundle/deb/` |

---

## Développement (mode dev)

```bash
# Terminal 1 — démarrer le sidecar manuellement
cd app/sidecar
python main.py --port 8765

# Terminal 2 — lancer Tauri en mode dev (hot-reload)
cd app
npm run tauri dev
```

---

## Mobile (Android / iOS)

Le sidecar Python ne se cross-compile pas vers Android/iOS.
Pour une version mobile, il faudrait soit :
- Héberger l'API sur un serveur distant et configurer `API` dans `index.html`
- Réécrire le backend en WebAssembly (Rust + wasm-bindgen) — projet conséquent

---

## Dépannage

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| Bannière "Démarrage…" persistante | Sidecar absent ou crash | Vérifier `src-tauri/binaries/anonymizer-sidecar/` |
| Erreur CORS dans la console | CSP Tauri trop stricte | Vérifier `tauri.conf.json` → `app.security.csp` |
| `tauri build` échoue sur les icônes | Icônes non générées | Refaire l'étape 1 |
| Presidio en anglais (pas français) | `fr_core_news_sm` absent du bundle | Relancer `build_sidecar.sh` après `python -m spacy download fr_core_news_sm` |
