"""Moteur GOT-OCR2 — Chinese Academy of Sciences, end-to-end OCR.

HuggingFace : stepfun-ai/GOT-OCR2_0 (~1.5 GB)
GPU CUDA recommandé (~2-4s), CPU acceptable (~30-40s).
"""
from .base import OCREngine

_model = None
_tokenizer = None
_device = None


def _get():
    global _model, _tokenizer, _device
    if _model is None:
        import torch
        # imports fully qualified pour éviter les glitchs uvicorn
        from transformers.models.auto.modeling_auto import AutoModel
        from transformers.models.auto.tokenization_auto import AutoTokenizer
        name = "stepfun-ai/GOT-OCR2_0"
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
        dtype = torch.float16 if _device == "cuda" else torch.float32
        _model = AutoModel.from_pretrained(
            name, trust_remote_code=True,
            low_cpu_mem_usage=True, use_safetensors=True,
            pad_token_id=_tokenizer.eos_token_id,
            torch_dtype=dtype,
        ).eval().to(_device)
    return _model, _tokenizer, _device


class GOTEngine(OCREngine):
    name = "got_ocr2"

    def _run(self, image_paths):
        model, tokenizer, device = _get()
        lines = []
        for p in image_paths:
            result = model.chat(tokenizer, p, ocr_type="ocr")
            lines.extend([l.strip() for l in result.splitlines() if l.strip()])
        return lines, 0.85 if lines else 0.0
