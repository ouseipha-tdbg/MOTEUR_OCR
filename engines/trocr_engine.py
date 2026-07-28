"""Moteur TrOCR — Microsoft, transformer-based OCR."""
from .base import OCREngine

_processor = None
_model = None
_device = None

MODEL_NAME = "microsoft/trocr-base-printed"
N_BANDES = 12


def _get():
    global _processor, _model, _device
    if _model is None:
        import torch
        from transformers.models.trocr import TrOCRProcessor
        from transformers.models.vision_encoder_decoder import VisionEncoderDecoderModel

        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
        _model = VisionEncoderDecoderModel.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=False,
            use_safetensors=True,
        )
        # Bypass meta device si accelerate a été utilisé
        if any(p.is_meta for p in _model.parameters()):
            _model = _model.to_empty(device=_device)
            state = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME).state_dict()
            _model.load_state_dict(state)
        else:
            _model = _model.to(_device)
        _model = _model.eval()
    return _processor, _model, _device


def _slice_horizontal(img, n=N_BANDES):
    w, h = img.size
    band_h = h // n
    return [img.crop((0, i * band_h, w, (i + 1) * band_h)) for i in range(n)]


class TrOCREngine(OCREngine):
    name = "trocr"

    def _run(self, image_paths):
        import torch
        from PIL import Image
        processor, model, device = _get()
        lines = []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            for band in _slice_horizontal(img):
                pixel_values = processor(images=band, return_tensors="pt").pixel_values.to(device)
                with torch.no_grad():
                    generated = model.generate(pixel_values, max_length=64)
                text = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
                if text and len(text) > 2:
                    lines.append(text)
        return lines, 0.80 if lines else 0.0
