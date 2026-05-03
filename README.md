# Anonymizer Demo — Traiteur-GPT

Application web pédagogique qui compare **quatre techniques de protection des données personnelles** côte à côte, en temps réel. Conçue comme support de TP autour du RGPD et de l'anonymisation.

## Aperçu

```
┌──────────────────────────────────────────────────────────────────┐
│  Texte source (saisie libre ou exemple)                          │
└──────────────┬──────────────────────────────────────────────────┘
               │  POST /anonymize
       ┌───────▼────────────────────────────────────────────┐
       │                  FastAPI (main.py)                  │
       └──┬──────────┬───────────────┬──────────────────────┘
          │          │               │                │
    Presidio    Scrubadub          Faker          Caviardage
  (tokenisation) (masquage)  (pseudonymisation)  (suppression)
```

## Les 4 méthodes comparées

| Méthode | Technique | Réversible | Précision |
|---|---|---|---|
| **Microsoft Presidio** | NLP (spaCy) → `<PERSONNE>`, `<EMAIL>`… | Non | Très élevée |
| **Scrubadub** | Regex + patterns → `{{FILTH}}` | Non | Moyenne |
| **Faker** | Remplacement par données fictives réalistes | Oui (table de correspondance) | Dépend de Presidio |
| **Caviardage** | Remplacement par `████` | Non | Élevée (NLP + regex) |

## Prérequis

- Python 3.10+
- ~500 Mo d'espace disque (modèle spaCy `fr_core_news_lg`)

## Installation et démarrage

```bash
bash start.sh
```

Le script crée automatiquement un environnement virtuel, installe les dépendances et télécharge le modèle spaCy français.

Ouvrez ensuite : **http://localhost:8000**

### Installation manuelle

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_lg
uvicorn main:app --reload
```

## API REST

| Endpoint | Méthode | Description |
|---|---|---|
| `GET /` | GET | Interface web |
| `POST /anonymize` | POST | Anonymise un texte via les 4 méthodes |
| `GET /status` | GET | État des bibliothèques disponibles |
| `GET /samples` | GET | Textes d'exemple prédéfinis |

### Exemple d'appel

```bash
curl -X POST http://localhost:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, je suis Jean Dupont, mon email est jean@example.com"}' | jq
```

Si jq n'est pas installé `sudo apt install jq` (outil de visualisation de sortie)

### Réponse

```json
{
  "presidio":  { "available": true, "text": "Bonjour, je suis <PERSONNE>, mon email est <EMAIL>", "entities": [...] },
  "scrubadub": { "available": true, "text": "Bonjour, je suis {{NAME}}, mon email est {{EMAIL}}" },
  "faker":     { "available": true, "text": "Bonjour, je suis Marie Leroy, mon email est m.leroy@example.fr", "mapping": {...} },
  "redaction": { "available": true, "text": "Bonjour, je suis ██████████, mon email est ██████████" }
}
```

## Structure du projet

```
prompt_anonymisation/
├── main.py              # Backend FastAPI — moteurs d'anonymisation
├── requirements.txt     # Dépendances Python
├── start.sh             # Script de démarrage tout-en-un
└── static/
    └── index.html       # Interface web (vanilla JS)
```

## Entités détectées par Presidio

| Code interne | Libellé affiché |
|---|---|
| `PERSON` | PERSONNE |
| `EMAIL_ADDRESS` | EMAIL |
| `PHONE_NUMBER` | TÉLÉPHONE |
| `LOCATION` | LIEU |
| `CREDIT_CARD` | CARTE_BANCAIRE |
| `DATE_TIME` | DATE |
| `IBAN_CODE` | IBAN |
| `IP_ADDRESS` | IP |
| `NRP` | NATIONALITÉ |

## Dépendances principales

- [FastAPI](https://fastapi.tiangolo.com/) — serveur web
- [Microsoft Presidio](https://microsoft.github.io/presidio/) — détection NLP des entités
- [spaCy](https://spacy.io/) + `fr_core_news_lg` — modèle de langue français
- [Scrubadub](https://scrubadub.readthedocs.io/) — anonymisation légère par regex
- [Faker](https://faker.readthedocs.io/) — génération de données fictives réalistes

## Modèle spaCy français — `fr_core_news_lg`

spaCy est une bibliothèque de traitement du langage naturel (NLP). Elle fournit des **modèles de langue** pré-entraînés capables d'analyser un texte : découper les phrases, identifier la nature grammaticale de chaque mot, et surtout reconnaître les **entités nommées** (noms de personnes, lieux, organisations…).

`fr_core_news_lg` est le modèle français de taille "large" de spaCy. Il a été entraîné sur des corpus de presse française et couvre :

| Capacité | Description |
|---|---|
| Tokenisation | Découpage du texte en mots et ponctuations |
| POS tagging | Identification de la nature grammaticale (nom, verbe, adjectif…) |
| NER (Named Entity Recognition) | Détection des entités nommées : personnes, lieux, organisations, dates… |
| Analyse de dépendances | Relations syntaxiques entre les mots |

**Pourquoi "lg" (large) ?** spaCy propose trois tailles : `sm` (small, ~15 Mo), `md` (medium, ~45 Mo) et `lg` (large, ~560 Mo). La taille "large" embarque des **vecteurs de mots** (word vectors) — des représentations numériques apprises sur des milliards de mots — ce qui améliore significativement la précision de la reconnaissance d'entités, au prix d'un téléchargement plus lourd.

Le code tente les trois tailles dans l'ordre décroissant (`lg` → `md` → `sm`) et bascule sur le modèle anglais si aucun n'est trouvé (voir `main.py` lignes 49-63).
