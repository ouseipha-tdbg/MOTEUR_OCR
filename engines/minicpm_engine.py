"""Moteur MiniCPM-V 2.6 — VLM OpenBMB (chinois), 8B params.

Sur CUDA (RTX) : ~5-10s. Sur CPU : 30-60s.
HuggingFace : openbmb/MiniCPM-V-2_6 (~16 GB)
"""
from .base import OCREngine

_model = None
_tokenizer = None
_device = None

MODEL_NAME = "openbmb/MiniCPM-V-2_6"
PROMPT = (
    "Extrais tout le texte visible sur ce document ligne par ligne, "
    "dans l'ordre de lecture, sans reformulation."
)


def _get():
    global _model, _tokenizer, _device
    if _model is None:
        import torch
        from transformers import AutoModel, AutoTokenizer
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if _device == "cuda" else torch.float32
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        _model = AutoModel.from_pretrained(
            MODEL_NAME, trust_remote_code=True,
            attn_implementation="sdpa", torch_dtype=dtype,
        ).eval().to(_device)
    return _model, _tokenizer, _device


class MiniCPMEngine(OCREngine):
    name = "minicpm_v"

    def _run(self, image_paths):
        from PIL import Image
        model, tokenizer, device = _get()
        lines = []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            msgs = [{"role": "user", "content": [img, PROMPT]}]
            result = model.chat(image=None, msgs=msgs, tokenizer=tokenizer)
            lines.extend([l.strip() for l in result.splitlines() if l.strip()])
        return lines, 0.87 if lines else 0.0
