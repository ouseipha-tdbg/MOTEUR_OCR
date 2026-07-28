"""Moteur CnOCR — breezedeus, OCR chinois via ONNX runtime.

Utilise onnxruntime déjà installé via rapidocr. Modèles ONNX ~50 MB.
Rapide sur CPU (~2s). Supporte FR/EN aussi.

Install : pip install cnocr
"""
from .base import OCREngine

_ocr = None


def _get():
    global _ocr
    if _ocr is None:
        from cnocr import CnOcr
        # rec_model_name : modèle multilingue (chinois + latin)
        _ocr = CnOcr(rec_model_name="densenet_lite_136-fc")
    return _ocr


class CnOCREngine(OCREngine):
    name = "cnocr"

    def _run(self, image_paths):
        ocr = _get()
        lines, confs = [], []
        for p in image_paths:
            result = ocr.ocr(p) or []
            for entry in result:
                txt = entry.get("text", "").strip()
                score = float(entry.get("score", 0.0))
                if txt:
                    lines.append(txt)
                    confs.append(score)
        mean = sum(confs) / len(confs) if confs else 0.0
        return lines, mean
