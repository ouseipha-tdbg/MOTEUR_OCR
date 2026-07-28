from .base import OCREngine
import config

_client_ready = False


def _init():
    global _client_ready
    if not _client_ready:
        import google.generativeai as genai
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY manquant dans .env")
        genai.configure(api_key=config.GEMINI_API_KEY)
        _client_ready = True


PROMPT = (
    "Extrais TOUT le texte visible sur ce(s) document(s) (pièce d'identité, "
    "facture ONEA/SONABEL, registre RCCM...) ligne par ligne, dans l'ordre "
    "de lecture. Si le document est photographié de travers ou roté, lis-le "
    "dans le bon sens. Réponds uniquement avec le texte brut, une ligne par "
    "ligne du document, sans reformulation."
)


class GeminiEngine(OCREngine):
    name = "gemini"

    def _run(self, image_paths):
        import google.generativeai as genai
        from PIL import Image
        _init()
        imgs = [Image.open(p) for p in image_paths]

        # modèle principal puis fallbacks si quota épuisé (429)
        models = [config.GEMINI_MODEL] + [
            m for m in config.GEMINI_FALLBACK_MODELS if m != config.GEMINI_MODEL
        ]
        last_err = None
        for name in models:
            try:
                model = genai.GenerativeModel(name)
                response = model.generate_content([PROMPT, *imgs])
                text = (response.text or "").strip()
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                # Gemini ne donne pas de confidence -> proxy fixe
                return lines, 0.9 if lines else 0.0
            except Exception as e:
                msg = str(e)
                if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                    last_err = e
                    continue  # quota de CE modèle épuisé -> modèle suivant
                raise
        raise RuntimeError(f"quota épuisé sur tous les modèles ({', '.join(models)}): {last_err}")
