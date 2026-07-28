# Preload des modules transformers (évite deadlocks import concurrents)
try:
    import transformers.models.auto.modeling_auto  # noqa: F401
    import transformers.models.auto.tokenization_auto  # noqa: F401
    import transformers.models.nougat.processing_nougat  # noqa: F401
    import transformers.models.vision_encoder_decoder.modeling_vision_encoder_decoder  # noqa: F401
except ImportError as _e:
    print(f"[engines] preload transformers warning: {_e}")

from .base import OCREngine, OCRResult
from .paddle_engine import PaddleEngine
from .gemini_engine import GeminiEngine
from .got_ocr_engine import GOTEngine
from .nougat_engine import NougatEngine

REGISTRY = {
    "paddle":   PaddleEngine,     # RapidOCR — 6s — 95%
    "gemini":   GeminiEngine,     # Google API — 12s — 90%
    "nougat":   NougatEngine,     # Meta VLM local — 35s — 84%
    "got_ocr2": GOTEngine,        # Chinese Academy VLM — 35s — 85%
}

# TrOCR et Donut retirés définitivement.
# Raisons techniques documentées pour la démo :
#   - TrOCR : conflit dtype Float/Half sur RTX + accelerate/torch
#   - Donut : échec de chargement modèle base sur cette version transformers


def get_engine(name: str) -> OCREngine:
    if name not in REGISTRY:
        raise ValueError(f"Unknown engine: {name}")
    return REGISTRY[name]()
