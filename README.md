# Zamapay OCR Lab

Comparateur de moteurs OCR pour KYC/KYB — POC autonome avant intégration dans `yam-bot`.

## Moteurs

`paddle` (RapidOCR) · `gemini` (API) · `nougat` · `got_ocr2`

## Docs supportés

`cnib` · `passport` (MRZ) · `rccm` · `facture` (détection auto ONEA/SONABEL) · `onea` · `sonabel` · `permis`

## Setup

Le `.venv` est **à la racine de `Zamapay/`** (partagé avec yam-bot).

```powershell
# Depuis C:\Users\Adil KAFANDO\Claude\Projects\Zamapay
.\.venv\Scripts\activate
pip install -r zamapay-ocr-lab\requirements.txt

# Tesseract binaire (Windows) : UB Mannheim
# https://github.com/UB-Mannheim/tesseract/wiki
# puis renseigner TESSERACT_CMD dans .env

copy zamapay-ocr-lab\.env.example zamapay-ocr-lab\.env
# → éditer GEMINI_API_KEY
```

## Lancement

```powershell
# IMPORTANT : cd dans le sous-dossier avant de lancer
cd zamapay-ocr-lab
python app.py
# → http://127.0.0.1:8000
```

## API

```
GET  /engines            liste moteurs + doc_types
POST /ocr                doc_type, engines (csv), recto, verso?
```

Exemple :

```bash
curl -X POST http://127.0.0.1:8000/ocr \
  -F "doc_type=cnib" \
  -F "engines=paddle,gemini" \
  -F "recto=@cnib_recto.jpg" \
  -F "verso=@cnib_verso.jpg"
```

Réponse :

```json
{
  "doc_type": "cnib",
  "results": [
    {"engine": "paddle", "lines": [...], "confidence": 0.87, "elapsed_ms": 1240,
     "parsed": {"nom": "...", "yam_id": "YAM-123456", ...}},
    {"engine": "gemini", ...}
  ]
}
```

## Intégration yam-bot

Le module `engines/` + `parsers/` est autonome. Pour brancher dans `yam-bot/kyc/ocr.py` :

```python
# yam-bot/kyc/ocr.py
from engines import get_engine
from parsers import parse

def extract_doc(recto, verso=None, doc_type="cnib", engine="paddle"):
    paths = [recto] + ([verso] if verso else [])
    res = get_engine(engine).extract(paths)
    if res.error and engine != "gemini":
        # fallback automatique
        res = get_engine("gemini").extract(paths)
    return parse(doc_type, res.lines)
```

## Structure

```
zamapay-ocr-lab/
├── app.py                    FastAPI + endpoints
├── config.py                 env vars
├── engines/
│   ├── base.py              OCREngine ABC + OCRResult
│   ├── paddle_engine.py
│   ├── tesseract_engine.py
│   ├── easyocr_engine.py
│   ├── doctr_engine.py
│   └── gemini_engine.py
├── parsers/
│   ├── _utils.py            regex + yam_id
│   ├── cnib.py
│   ├── passport.py          MRZ
│   ├── rccm.py
│   ├── facture.py
│   └── permis.py
├── static/                  UI vanilla JS
└── requirements.txt
```

## Notes

- Le premier appel de chaque moteur télécharge les modèles (paddle ~50 MB, doctr ~100 MB, easyocr ~200 MB).
- Gemini nécessite une clé API (`gemini-2.0-flash` par défaut, largement suffisant).
- Pour GPU : `OCR_USE_GPU=true` dans `.env` + install PaddlePaddle GPU manuellement.
