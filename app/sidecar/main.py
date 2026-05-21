from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
import sys

# PyInstaller --onefile compatibility: spaCy can't find models via entry_points
# in a frozen bundle. Patch spacy.load to fall back to direct module import.
if getattr(sys, "frozen", False):
    import importlib
    import spacy as _spacy
    _orig_load = _spacy.load
    def _load_patched(name, *args, **kwargs):
        try:
            return _orig_load(name, *args, **kwargs)
        except OSError:
            mod = importlib.import_module(name.replace("-", "_"))
            return mod.load(*args, **kwargs)
    _spacy.load = _load_patched

app = FastAPI(title="Anonymizer Demo - Traiteur-GPT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Library availability ──────────────────────────────────────────────────────

try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer
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
raw_spacy = None

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
            raw_spacy = getattr(nlp_engine, "nlp", {}).get("fr")
            break
        except Exception:
            continue

    if analyzer is None:
        analyzer = AnalyzerEngine()

    anonymizer_engine = AnonymizerEngine()

# ── Medical terms recognizer (PatternRecognizer custom, Art. 9 RGPD) ─────────

medical_recognizer = None

if PRESIDIO_AVAILABLE:
    _MEDICAL_TERMS = [
        "diabète", "diabétique",
        "cancer", "tumeur", "leucémie", "lymphome",
        "sida", "vih",
        "asthme", "asthmatique",
        "épilepsie", "épileptique",
        "alzheimer", "parkinson",
        "autisme", "autiste",
        "sclérose",
        "schizophrénie", "schizophrène",
        "dépression", "dépressif", "dépressive",
        "bipolaire",
        "anxiété",
        "anorexie", "anorexique", "boulimie",
        "allergie", "allergique",
        "intolérance", "intolérant",
        "cœliaque", "coeliaque",
        "gluten", "sans gluten",
        "lactose", "caséine",
        "arachide", "arachides", "cacahuète", "cacahuètes",
        "noix", "noisette", "amande", "noix de cajou", "noix de pécan",
        "pistache", "macadamia",
        "crustacé", "crustacés", "crevette", "homard", "crabe",
        "mollusque", "mollusques", "huître", "moule", "calamar",
        "poisson", "cabillaud", "saumon", "thon",
        "œuf", "œufs",
        "lait", "produit laitier",
        "soja", "sésame",
        "blé", "seigle", "orge", "avoine",
        "moutarde", "céleri", "lupin",
        "sulfite", "sulfites",
        "fructose", "histamine",
        "handicap", "handicapé",
        "obésité", "obèse",
        "hypertension", "hypertendu",
        "hépatite",
        "séropositif", "séropositive",
        "enceinte", "grossesse",
        "insuffisance cardiaque", "insuffisance rénale",
    ]
    _MEDICAL_CONTEXT = [
        "souffre", "atteint", "atteinte",
        "diagnostiqué", "diagnostiquée",
        "traitement", "médicament",
        "maladie", "pathologie",
        "allergie", "allergique", "intolérant", "intolérance",
        "évite", "éviter", "interdit", "interdite", "exclure", "exclu",
        "réaction", "anaphylaxie", "anaphylactique",
        "sans", "régime", "régime sans",
    ]
    medical_recognizer = PatternRecognizer(
        supported_entity="HEALTH",
        deny_list=_MEDICAL_TERMS,
        context=_MEDICAL_CONTEXT,
        supported_language="fr",
        name="MedicalTermRecognizer",
    )

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
    "HEALTH": "SANTÉ",
}

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_FR = re.compile(r"\b0[1-9](?:[\s.\-]?\d{2}){4}\b")
_CARD_RE = re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b")


def _analyze(text: str, detect_health: bool = False):
    if not PRESIDIO_AVAILABLE:
        return []
    results = list(analyzer.analyze(text=text, language=PRESIDIO_LANG))
    if detect_health and medical_recognizer:
        health_results = medical_recognizer.analyze(text=text, entities=["HEALTH"], nlp_artifacts=None)
        results.extend(health_results)
    return results


# ── Anonymisation functions ───────────────────────────────────────────────────

def presidio_anonymize(text: str, detect_health: bool = False) -> dict:
    if not PRESIDIO_AVAILABLE:
        return {
            "available": False,
            "text": "⚠️ Presidio non installé.",
            "entities": [],
        }
    try:
        results = _analyze(text, detect_health)
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
        spacy_missed = []
        if raw_spacy:
            doc = raw_spacy(text)
            for ent in doc.ents:
                overlaps = any(
                    r.start < ent.end_char and r.end > ent.start_char
                    for r in results
                )
                if not overlaps:
                    spacy_missed.append({"text": ent.text, "label": ent.label_})
        return {"available": True, "text": anonymized.text, "entities": entities, "spacy_missed": spacy_missed}
    except Exception as exc:
        return {"available": True, "text": f"Erreur : {exc}", "entities": [], "spacy_missed": []}


def scrubadub_anonymize(text: str) -> dict:
    if not SCRUBADUB_AVAILABLE:
        return {"available": False, "text": "⚠️ Scrubadub non installé."}
    try:
        scrubber = scrubadub.Scrubber()
        return {"available": True, "text": scrubber.clean(text)}
    except Exception as exc:
        return {"available": True, "text": f"Erreur : {exc}"}


def faker_pseudonymize(text: str, detect_health: bool = False) -> dict:
    if not FAKER_AVAILABLE:
        return {"available": False, "text": "⚠️ Faker non installé.", "mapping": {}}
    if not PRESIDIO_AVAILABLE:
        return {"available": False, "text": "⚠️ Presidio requis pour la détection.", "mapping": {}}
    try:
        results = sorted(_analyze(text, detect_health), key=lambda r: r.start, reverse=True)
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
                elif et == "HEALTH":
                    mapping[original] = "[CONDITION_MÉDICALE]"
                else:
                    mapping[original] = f"[{et}_FICTIF]"
            pseudo = pseudo[: r.start] + mapping[original] + pseudo[r.end :]
        return {"available": True, "text": pseudo, "mapping": mapping}
    except Exception as exc:
        return {"available": True, "text": f"Erreur : {exc}", "mapping": {}}


def redact_text(text: str, detect_health: bool = False) -> dict:
    redacted = _EMAIL_RE.sub("██████████", text)
    redacted = _PHONE_FR.sub("██ ██ ██ ██ ██", redacted)
    redacted = _CARD_RE.sub("████ ████ ████ ████", redacted)
    if PRESIDIO_AVAILABLE:
        try:
            results = sorted(_analyze(text, detect_health), key=lambda r: r.start, reverse=True)
            for r in results:
                length = r.end - r.start
                redacted = redacted[: r.start] + "█" * length + redacted[r.end :]
        except Exception:
            pass
    return {"available": True, "text": redacted}


# ── Routes ────────────────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str
    detect_health: bool = False


@app.post("/anonymize")
async def anonymize(request: TextRequest):
    text = request.text.strip()
    dh = request.detect_health
    if not text:
        return {
            "presidio": {"available": PRESIDIO_AVAILABLE, "text": "", "entities": []},
            "scrubadub": {"available": SCRUBADUB_AVAILABLE, "text": ""},
            "faker": {"available": FAKER_AVAILABLE, "text": "", "mapping": {}},
            "redaction": {"available": True, "text": ""},
        }
    return {
        "presidio": presidio_anonymize(text, dh),
        "scrubadub": scrubadub_anonymize(text),
        "faker": faker_pseudonymize(text, dh),
        "redaction": redact_text(text, dh),
    }


class DeanonymizeRequest(BaseModel):
    text: str
    mapping: dict


@app.post("/deanonymize")
async def deanonymize(request: DeanonymizeRequest):
    text = request.text
    reverse_map = {v: k for k, v in request.mapping.items()}
    for fake in sorted(reverse_map, key=len, reverse=True):
        text = text.replace(fake, reverse_map[fake])
    return {"text": text}


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
    {
        "id": 5,
        "icon": "🛒🇬🇧",
        "title": "Individual Order",
        "text": (
            "Hello, my name is James Mitchell and I would like to order 50 meals for my "
            "event on March 15th. My phone number is +44 7700 900456 and my address is "
            "22 Baker Street, London W1U 3BX. My email is james.mitchell@gmail.com"
        ),
    },
    {
        "id": 6,
        "icon": "🌰🇬🇧",
        "title": "Client Allergy",
        "text": (
            "Hi! My name is Emily Carter. I have a severe allergy to nuts and shellfish. "
            "For my Saturday order, please deliver to 8 Elm Avenue, Manchester M1 4PW. "
            "Budget: £2,500. Call me back at +44 7911 123456."
        ),
    },
    {
        "id": 7,
        "icon": "💼🇬🇧",
        "title": "Corporate Order (credit card)",
        "text": (
            "Professional order for Mr. Robert Hughes (Hughes & Partners Ltd). "
            "100 covers on 20/04/2024. Card number: 4532 1234 5678 9012. "
            "Contact: r.hughes@company.co.uk — Tel: +44 20 7946 0321"
        ),
    },
    {
        "id": 8,
        "icon": "💬🇬🇧",
        "title": "Customer Support",
        "text": (
            "Your case has been assigned to Sarah Thompson (sarah.thompson@hotmail.com). "
            "She is based in Birmingham. Her customer reference is +44 121 496 0012. "
            "Payment made with card 1234 5678 8765 4321."
        ),
    },
    {
        "id": 9,
        "icon": "🏥",
        "title": "Données de santé (Art. 9)",
        "text": (
            "Bonjour, je suis Paul Renard. Je souffre de diabète de type 2 et d'hypertension. "
            "Je suis également cœliaque (intolérant au gluten) et allergique aux arachides et aux crustacés. "
            "Mon régime exclut aussi le lactose. "
            "Vous pouvez me joindre au 06 11 22 33 44 ou par email : paul.renard@orange.fr"
        ),
    },
]


# ── Entry point (called by PyInstaller binary) ───────────────────────────────

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Anonymizer sidecar server")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="error")
