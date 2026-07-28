import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Modèles de secours si quota épuisé (429) — quotas séparés par modèle
GEMINI_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "GEMINI_FALLBACK_MODELS", "gemini-2.0-flash,gemini-2.5-flash-lite"
    ).split(",") if m.strip()
]
OCR_USE_GPU = os.getenv("OCR_USE_GPU", "false").lower() == "true"
OCR_LANG = os.getenv("OCR_LANG", "fr")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
