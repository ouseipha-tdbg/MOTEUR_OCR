"""Moteur Surya — OCR open source multi-langue, très bon sur docs structurés.

Install : pip install surya-ocr
Modèles téléchargés au 1er appel (~500 MB), cachés dans ~/.cache.
"""
from .base import OCREngine

_rec = None
_det = None


def _get():
    global _rec, _det
    if _rec is None:
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        _rec = RecognitionPredictor()
        _det = DetectionPredictor()
    return _rec, _det


class SuryaEngine(OCREngine):
    name = "surya"

    def _run(self, image_paths):
        from PIL import Image
        rec, det = _get()
        lines, confs = [], []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            preds = rec([img], [["fr", "en"]], det)
            for pred in preds:
                for line in pred.text_lines:
                    if line.text:
                        lines.append(line.text)
                        confs.append(float(getattr(line, "confidence", 0.85)))
        mean = sum(confs) / len(confs) if confs else 0.0
        return lines, mean
