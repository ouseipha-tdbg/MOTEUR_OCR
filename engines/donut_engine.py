"""Moteur Donut — NAVER Clova, VLM léger pour documents structurés.

HuggingFace : naver-clova-ix/donut-base (~200 MB)
"""
from .base import OCREngine

_processor = None
_model = None
_device = None

MODEL_NAME = "naver-clova-ix/donut-base"
TASK_PROMPT = "<s_synthdog>"


def _get():
    global _processor, _model, _device
    if _model is None:
        import torch
        from transformers.models.donut import DonutProcessor
        from transformers.models.vision_encoder_decoder import VisionEncoderDecoderModel

        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _processor = DonutProcessor.from_pretrained(MODEL_NAME)

        # Chargement direct sans accelerate/meta device
        _model = VisionEncoderDecoderModel.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=False,
            use_safetensors=True,
        )
        # Force materialisation des poids (bypass meta si présent)
        if any(p.is_meta for p in _model.parameters()):
            _model = _model.to_empty(device=_device)
            state = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME).state_dict()
            _model.load_state_dict(state)
        else:
            _model = _model.to(_device)
        _model = _model.eval()
    return _processor, _model, _device


class DonutEngine(OCREngine):
    name = "donut"

    def _run(self, image_paths):
        import torch
        from PIL import Image
        processor, model, device = _get()
        lines = []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            pixel_values = processor(img, return_tensors="pt").pixel_values.to(device)
            decoder_input_ids = processor.tokenizer(
                TASK_PROMPT, add_special_tokens=False, return_tensors="pt"
            ).input_ids.to(device)
            with torch.no_grad():
                outputs = model.generate(
                    pixel_values,
                    decoder_input_ids=decoder_input_ids,
                    max_length=1024,
                    pad_token_id=processor.tokenizer.pad_token_id,
                    eos_token_id=processor.tokenizer.eos_token_id,
                )
            seq = processor.batch_decode(outputs, skip_special_tokens=True)[0]
            for l in seq.replace(TASK_PROMPT, "").split("\n"):
                l = l.strip()
                if l:
                    lines.append(l)
        return lines, 0.83 if lines else 0.0
