# Anonymizer Demo — Traiteur-GPT

Application pédagogique qui compare **quatre techniques de protection des données personnelles** côte à côte, en temps réel. Conçue comme support de TP autour du RGPD et de l'anonymisation.

Disponible en deux modes :

| Mode | Lancement | Résultat |
|------|-----------|----------|
| **Web** | `./start.sh` | Serveur local → ouvrir dans un navigateur |
| **Desktop** | `cd app && ./build_desktop.sh` | `.exe` / `.dmg` / `.AppImage` standalone |

---

## Aperçu

```
┌──────────────────────────────────────────────────────────────────┐
│  Texte source (saisie libre ou exemple prédéfini)                │
└──────────────┬───────────────────────────────────────────────────┘
               │  POST /anonymize
       ┌───────▼──────────────────────────────────────┐
       │               FastAPI (Python)                │
       └──┬──────────┬──────────────┬─────────────────┘
          │          │              │              │
    Presidio    Scrubadub         Faker        Caviardage
  (tokenisation) (masquage)  (pseudonymisation) (suppression)
```

---

## Les 4 méthodes comparées

| Méthode | Technique | Réversible | Précision |
|---|---|---|---|
| **Microsoft Presidio** | NLP (spaCy) → `<PERSONNE>`, `<EMAIL>`… | Non | Très élevée |
| **Scrubadub** | Regex + patterns → `{{FILTH}}` | Non | Moyenne |
| **Faker** | Remplacement par données fictives réalistes | Oui (table de correspondance) | Dépend de Presidio |
| **Caviardage** | Remplacement par `████` | Non | Élevée (NLP + regex) |

---

## Mode Web

### Démarrage rapide

```bash
./start.sh        # macOS / Linux
start.bat         # Windows
```

Le script crée automatiquement un venv, installe les dépendances et télécharge le modèle spaCy français.

Ouvrez ensuite : **http://localhost:8000**

### Installation manuelle

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download fr_core_news_lg
uvicorn main:app --reload
```

### API REST

| Endpoint | Méthode | Description |
|---|---|---|
| `GET /` | GET | Interface web |
| `POST /anonymize` | POST | Anonymise un texte via les 4 méthodes |
| `GET /status` | GET | État des bibliothèques disponibles |
| `GET /samples` | GET | Textes d'exemple prédéfinis |

```bash
curl -X POST http://localhost:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Je suis Jean Dupont, jean@example.com"}' | jq
```

```json
{
  "presidio":  { "text": "Je suis <PERSONNE>, <EMAIL>", "entities": [...] },
  "scrubadub": { "text": "Je suis {{NAME}}, {{EMAIL}}" },
  "faker":     { "text": "Je suis Marie Leroy, m.leroy@example.fr", "mapping": {...} },
  "redaction": { "text": "Je suis ██████████, ██████████" }
}
```

---

## Mode Desktop (app native)

Génère un exécutable **autonome** (aucune installation requise pour l'utilisateur final) via [Tauri 2](https://tauri.app) + sidecar PyInstaller.

### Architecture

```
app/
├── build_desktop.sh / .bat    ← Script de build tout-en-un  ← VOUS ÊTES ICI
├── index.html                 ← Interface (identique au mode web)
├── sidecar/
│   └── main.py               ← Serveur FastAPI embarqué (port 8765)
└── src-tauri/
    └── src/lib.rs            ← Tauri lance/arrête le sidecar automatiquement
```

Au démarrage de l'app : Tauri lance le serveur Python en arrière-plan sur `localhost:8765`, ouvre la fenêtre native, puis l'arrête proprement à la fermeture.

### Prérequis

| Outil | Version | Lien |
|-------|---------|------|
| Python | ≥ 3.10 | https://python.org |
| Rust + cargo | stable | https://rustup.rs |
| Node.js + npm | ≥ 18 | https://nodejs.org |
| **Linux seulement** | — | `sudo apt install libwebkit2gtk-4.1-dev libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev` |
| **macOS seulement** | — | `xcode-select --install` |
| **Windows seulement** | — | Visual C++ Build Tools 2022 |

### Build en une commande

```bash
# macOS / Linux
cd app
./build_desktop.sh
```

```bat
rem Windows
cd app
build_desktop.bat
```

Le script fait tout automatiquement :

| Étape | Durée | Détail |
|-------|-------|--------|
| 1. Venv + dépendances Python | ~2 min | Presidio, spaCy, Faker, scrubadub, PyInstaller |
| 2. Modèle spaCy | ~30 s | `fr_core_news_sm` (~15 MB) |
| 3. Icônes Tauri | ~10 s | Générées automatiquement si absentes |
| 4. **Sidecar PyInstaller** | ~5–15 min | Embed Python + toutes les libs dans un binaire |
| 5. Build Rust (Tauri) | ~3–5 min | Compilation du shell natif |

Les installateurs finaux se trouvent dans `app/src-tauri/target/release/bundle/`.

| Plateforme | Format |
|------------|--------|
| Windows | `.exe` (NSIS) et `.msi` |
| macOS | `.app` et `.dmg` |
| Linux | `.AppImage` et `.deb` |

> **Taille du bundle** : ~250–400 MB (Python embarqué + spaCy + libs).
> C'est normal : l'interpréteur Python entier est inclus.

### Icônes personnalisées

Par défaut, le build génère une icône placeholder (fond sombre uni). Pour des icônes à votre image :

```bash
cd app
./node_modules/.bin/tauri icon votre-logo-1024x1024.png
```

### Développement / débogage desktop

```bash
# Terminal 1 — serveur Python (reload automatique)
cd app/sidecar && python main.py --port 8765

# Terminal 2 — Tauri en mode dev (hot-reload de l'UI)
cd app && npm run tauri dev
```

> Voir `app/BUILD.md` pour le dépannage détaillé et les options avancées.

---

## Structure du projet

```
anonymizer/
├── main.py              ← Backend FastAPI (mode web)
├── requirements.txt     ← Dépendances Python (mode web)
├── start.sh / .bat      ← Démarrage mode web
├── static/
│   └── index.html       ← Interface web
└── app/                 ← Version desktop (Tauri 2)
    ├── build_desktop.sh / .bat   ← Build tout-en-un
    ├── index.html                ← Interface (adaptée desktop)
    ├── BUILD.md                  ← Guide de build détaillé
    ├── sidecar/
    │   ├── main.py               ← Serveur FastAPI embarqué
    │   ├── requirements.txt      ← Dépendances sidecar
    │   ├── make_icon.py          ← Générateur d'icône placeholder
    │   ├── build_sidecar.sh      ← Build sidecar seul (macOS/Linux)
    │   └── build_sidecar.bat     ← Build sidecar seul (Windows)
    └── src-tauri/
        ├── Cargo.toml
        ├── tauri.conf.json
        └── src/lib.rs            ← Gestion cycle de vie sidecar
```

---

## Entités détectées par Presidio

| Code | Libellé affiché |
|------|----------------|
| `PERSON` | PERSONNE |
| `EMAIL_ADDRESS` | EMAIL |
| `PHONE_NUMBER` | TÉLÉPHONE |
| `LOCATION` | LIEU |
| `CREDIT_CARD` | CARTE_BANCAIRE |
| `DATE_TIME` | DATE |
| `IBAN_CODE` | IBAN |
| `IP_ADDRESS` | IP |
| `NRP` | NATIONALITÉ |
| `HEALTH` (custom) | SANTÉ — données Art. 9 RGPD |

---

## Dépendances principales

- [FastAPI](https://fastapi.tiangolo.com/) — serveur API
- [Microsoft Presidio](https://microsoft.github.io/presidio/) — détection NLP des entités PII
- [spaCy](https://spacy.io/) + `fr_core_news_lg` / `sm` — modèle de langue français
- [Scrubadub](https://scrubadub.readthedocs.io/) — anonymisation légère par regex
- [Faker](https://faker.readthedocs.io/) — génération de fausses données réalistes
- [Tauri 2](https://tauri.app) — shell natif desktop (Rust + WebView)
- [PyInstaller](https://pyinstaller.org/) — packaging Python standalone

---

## Modèle spaCy — pourquoi `fr_core_news_lg` vs `sm` ?

| Modèle | Taille | Précision NER | Vecteurs de mots |
|--------|--------|--------------|-----------------|
| `fr_core_news_sm` | ~15 MB | Bonne | Non |
| `fr_core_news_md` | ~45 MB | Meilleure | Oui (partiel) |
| `fr_core_news_lg` | ~560 MB | Excellente | Oui (complet) |

Le mode **web** charge `lg` par défaut (meilleure précision pour le TP). Le mode **desktop** embarque `sm` pour limiter la taille du bundle. Le code bascule automatiquement sur le plus grand modèle disponible.
