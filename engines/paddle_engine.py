"""Moteur "paddle" — via RapidOCR (ONNX runtime, modèles PP-OCR).

Double passe : image originale + rotation 90° avec upscale/CLAHE.
Les factures BF sont souvent photographiées en paysage et imprimées en
matriciel — la 2e passe récupère les champs perdus (parcelle, contrat ONEA).
"""
from .base import OCREngine

_instance = None


def _get():
    global _instance
    if _instance is None:
        from rapidocr_onnxruntime import RapidOCR
        _instance = RapidOCR()
    return _instance


def _preprocess_rotated(img):
    """Rotation 90° anti-horaire + upscale 2x + CLAHE (contraste local)."""
    import cv2
    rot = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if max(rot.shape[:2]) < 3000:
        rot = cv2.resize(rot, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(rot, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)


class PaddleEngine(OCREngine):
    name = "paddle"

    def _run(self, image_paths):
        import cv2
        ocr = _get()
        lines, confs = [], []

        def _collect(result):
            for entry in (result or []):
                if len(entry) >= 3:
                    _, txt, score = entry
                    if txt and txt not in lines:
                        lines.append(txt)
                        confs.append(float(score))

        for p in image_paths:
            img = cv2.imread(p)
            if img is None:  # format non lu par cv2 (webp exotique...) -> passe simple
                result, _ = ocr(p)
                _collect(result)
                continue
            result, _ = ocr(img)
            _collect(result)
            # 2e passe : orientation alternative + préprocessing
            result2, _ = ocr(_preprocess_rotated(img))
            _collect(result2)

        mean = sum(confs) / len(confs) if confs else 0.0
        return lines, mean
