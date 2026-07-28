"""Moteur Nougat — Meta AI, VLM pour documents scannés (préserve structure).

HuggingFace : facebook/nougat-small (~250 MB)
Zéro nouveau conflit. CUDA ~3s / CPU ~20s.
"""
from .base import OCREngine

_processor = None
_model = None
_device = None

MODEL_NAME = "facebook/nougat-small"


def _get():
    global _processor, _model, _device
    if _model is None:
        import torch
        # imports fully qualified pour éviter les glitchs uvicorn
        from transformers.models.nougat import NougatProcessor
        from transformers.models.vision_encoder_decoder import VisionEncoderDecoderModel
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _processor = NougatProcessor.from_pretrained(MODEL_NAME)
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME).to(_device).eval()
    return _processor, _model, _device


class NougatEngine(OCREngine):
    name = "nougat"

    def _run(self, image_paths):
        import torch
        from PIL import Image
        processor, model, device = _get()
        lines = []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            pixel_values = processor(images=img, return_tensors="pt").pixel_values.to(device)
            with torch.no_grad():
                outputs = model.generate(
                    pixel_values,
                    min_length=1,
                    max_new_tokens=1500,
                    bad_words_ids=[[processor.tokenizer.unk_token_id]],
                )
            text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
            text = processor.post_process_generation(text, fix_markdown=False)
            for l in text.split("\n"):
                l = l.strip()
                if l:
                    lines.append(l)
        return lines, 0.84 if lines else 0.0
