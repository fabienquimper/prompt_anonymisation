from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI(title="Anonymizer Demo - Traiteur-GPT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Library availability ──────────────────────────────────────────────────────

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

try:
    import scrubadub
    SCRUBADUB_AVAILABLE = True
except ImportError:
    SCRUBADUB_AVAILABLE = False

try:
    from faker import Faker
    fake = Faker("fr_FR")
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    fake = None

# ── Presidio engine initialisation ───────────────────────────────────────────

PRESIDIO_LANG = "en"
analyzer = None
anonymizer_engine = None

if PRESIDIO_AVAILABLE:
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    for model_name in ("fr_core_news_lg", "fr_core_news_md", "fr_core_news_sm"):
        try:
            cfg = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "fr", "model_name": model_name}],
            }
            nlp_engine = NlpEngineProvider(nlp_configuration=cfg).create_engine()
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["fr"])
            PRESIDIO_LANG = "fr"
            break
        except Exception:
            continue

    if analyzer is None:
        analyzer = AnalyzerEngine()

    anonymizer_engine = AnonymizerEngine()

# ── Helpers ───────────────────────────────────────────────────────────────────

ENTITY_FR = {
    "PERSON": "PERSONNE",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "TÉLÉPHONE",
    "LOCATION": "LIEU",
    "CREDIT_CARD": "CARTE_BANCAIRE",
    "DATE_TIME": "DATE",
    "URL": "URL",
    "IP_ADDRESS": "IP",
    "IBAN_CODE": "IBAN",
    "NRP": "NATIONALITÉ",
}

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_FR = re.compile(r"\b0[1-9](?:[\s.\-]?\d{2}){4}\b")
_CARD_RE = re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b")


def _analyze(text: str):
    if not PRESIDIO_AVAILABLE:
        return []
    return analyzer.analyze(text=text, language=PRESIDIO_LANG)


# ── Anonymisation functions ───────────────────────────────────────────────────

def presidio_anonymize(text: str) -> dict:
    if not PRESIDIO_AVAILABLE:
        return {
            "available": False,
            "text": "⚠️ Presidio non installé.\n→ pip install presidio-analyzer presidio-anonymizer spacy\n→ python -m spacy download fr_core_news_lg",
            "entities": [],
        }
    try:
        results = _analyze(text)
        anonymized = anonymizer_engine.anonymize(text=text, analyzer_results=results)
        entities = [
            {
                "type": r.entity_type,
                "label": ENTITY_FR.get(r.entity_type, r.entity_type),
                "original": text[r.start : r.end],
                "score": round(r.score, 2),
            }
            for r in results
        ]
        return {"available": True, "text": anonymized.text, "entities": entities}
    except Exception as exc:
        return {"available": True, "text": f"Erreur : {exc}", "entities": []}


def scrubadub_anonymize(text: str) -> dict:
    if not SCRUBADUB_AVAILABLE:
        return {
            "available": False,
            "text": "⚠️ Scrubadub non installé.\n→ pip install scrubadub",
        }
    try:
        scrubber = scrubadub.Scrubber()
        return {"available": True, "text": scrubber.clean(text)}
    except Exception as exc:
        return {"available": True, "text": f"Erreur : {exc}"}


def faker_pseudonymize(text: str) -> dict:
    if not FAKER_AVAILABLE:
        return {
            "available": False,
            "text": "⚠️ Faker non installé.\n→ pip install faker",
            "mapping": {},
        }
    if not PRESIDIO_AVAILABLE:
        return {
            "available": False,
            "text": "⚠️ Presidio requis pour la détection.\n→ pip install presidio-analyzer",
            "mapping": {},
        }
    try:
        results = sorted(_analyze(text), key=lambda r: r.start, reverse=True)
        mapping: dict[str, str] = {}
        pseudo = text

        for r in results:
            original = text[r.start : r.end]
            if original not in mapping:
                et = r.entity_type
                if et == "PERSON":
                    mapping[original] = fake.name()
                elif et == "PHONE_NUMBER":
                    mapping[original] = fake.phone_number()
                elif et == "EMAIL_ADDRESS":
                    mapping[original] = fake.email()
                elif et == "LOCATION":
                    mapping[original] = fake.city()
                elif et == "CREDIT_CARD":
                    mapping[original] = fake.credit_card_number(card_type="visa16")
                elif et == "DATE_TIME":
                    mapping[original] = fake.date(pattern="%d/%m/%Y")
                else:
                    mapping[original] = f"[{et}_FICTIF]"
            pseudo = pseudo[: r.start] + mapping[original] + pseudo[r.end :]

        return {"available": True, "text": pseudo, "mapping": mapping}
    except Exception as exc:
        return {"available": True, "text": f"Erreur : {exc}", "mapping": {}}


def redact_text(text: str) -> dict:
    # Start with regex pass for common patterns not always caught by NLP
    redacted = _EMAIL_RE.sub("██████████", text)
    redacted = _PHONE_FR.sub("██ ██ ██ ██ ██", redacted)
    redacted = _CARD_RE.sub("████ ████ ████ ████", redacted)

    if PRESIDIO_AVAILABLE:
        try:
            results = sorted(_analyze(text), key=lambda r: r.start, reverse=True)
            for r in results:
                length = r.end - r.start
                redacted = redacted[: r.start] + "█" * length + redacted[r.end :]
        except Exception:
            pass

    return {"available": True, "text": redacted}


# ── Routes ────────────────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/anonymize")
async def anonymize(request: TextRequest):
    text = request.text.strip()
    if not text:
        return {
            "presidio": {"available": PRESIDIO_AVAILABLE, "text": "", "entities": []},
            "scrubadub": {"available": SCRUBADUB_AVAILABLE, "text": ""},
            "faker": {"available": FAKER_AVAILABLE, "text": "", "mapping": {}},
            "redaction": {"available": True, "text": ""},
        }
    return {
        "presidio": presidio_anonymize(text),
        "scrubadub": scrubadub_anonymize(text),
        "faker": faker_pseudonymize(text),
        "redaction": redact_text(text),
    }


@app.get("/status")
async def status():
    return {
        "presidio": PRESIDIO_AVAILABLE,
        "presidio_lang": PRESIDIO_LANG if PRESIDIO_AVAILABLE else None,
        "scrubadub": SCRUBADUB_AVAILABLE,
        "faker": FAKER_AVAILABLE,
    }


@app.get("/samples")
async def samples():
    return SAMPLE_TEXTS


SAMPLE_TEXTS = [
    {
        "id": 1,
        "icon": "🛒",
        "title": "Commande Particulier",
        "text": (
            "Bonjour, je suis Jean Dupont et je voudrais commander 50 repas pour mon "
            "événement du 15 mars. Mon numéro de téléphone est le 06 12 34 56 78 et mon "
            "adresse est 5 rue de la Paix, 75001 Paris. Mon email est jean.dupont@gmail.com"
        ),
    },
    {
        "id": 2,
        "icon": "🌰",
        "title": "Allergie Client",
        "text": (
            "Bonjour ! Je m'appelle Sophie Martin. J'ai une allergie sévère aux noix "
            "et aux crustacés. Pour ma commande de samedi, livrez au 12 avenue des Lilas, "
            "Lyon 69003. Budget : 2500 €. Rappel au 07 98 76 54 32."
        ),
    },
    {
        "id": 3,
        "icon": "💼",
        "title": "Commande Pro (carte bancaire)",
        "text": (
            "Commande professionnelle pour M. Pierre Leroy (Société ABC). "
            "100 couverts le 20/04/2024. Numéro de carte : 4532 1234 5678 9012. "
            "Contact : p.leroy@entreprise.fr — Tél : 01 23 45 67 89"
        ),
    },
    {
        "id": 4,
        "icon": "💬",
        "title": "Support Client",
        "text": (
            "Votre dossier a été pris en charge par Marie Leclerc "
            "(marie.leclerc@hotmail.com). Elle habite à Bordeaux. "
            "Son numéro client est le 04 56 78 90 12. "
            "Paiement effectué avec la carte 1234 5678 8765 4321."
        ),
    },
]


app.mount("/static", StaticFiles(directory="static"), name="static")
