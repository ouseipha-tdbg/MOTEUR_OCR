"""Moteur Qwen2-VL — VLM Alibaba, alternative locale à Gemini.

Utilise le modèle 2B pour rester CPU-friendly (~4 GB téléchargement).
GPU CUDA (RTX) recommandé pour vitesse acceptable (3-8s vs 5-15min CPU).
"""
from .base import OCREngine

_model = None
_processor = None

MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
PROMPT = (
    "Extrais tout le texte visible sur ce document ligne par ligne, "
    "dans l'ordre de lecture, sans reformulation ni traduction. "
    "Une ligne par ligne du document, texte brut uniquement."
)


def _get():
    global _model, _processor
    if _model is None:
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        device_map = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        _model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_NAME, torch_dtype=dtype, device_map=device_map,
        )
        _processor = AutoProcessor.from_pretrained(MODEL_NAME)
    return _model, _processor


class QwenVLEngine(OCREngine):
    name = "qwen_vl"

    def _run(self, image_paths):
        import torch
        model, processor = _get()

        # Charge les images
        from PIL import Image
        images = [Image.open(p).convert("RGB") for p in image_paths]

        # Format messages multi-images (recto + verso)
        content = [{"type": "image", "image": img} for img in images]
        content.append({"type": "text", "text": PROMPT})
        messages = [{"role": "user", "content": content}]

        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # helper qwen-vl-utils si dispo, sinon fallback direct
        try:
            from qwen_vl_utils import process_vision_info
            image_inputs, video_inputs = process_vision_info(messages)
        except ImportError:
            image_inputs, video_inputs = images, None

        inputs = processor(
            text=[text], images=image_inputs, videos=video_inputs,
            padding=True, return_tensors="pt",
        ).to(model.device)

        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=2048)

        trimmed = output[:, inputs.input_ids.shape[1]:]
        result = processor.batch_decode(trimmed, skip_special_tokens=True)[0]
        lines = [l.strip() for l in result.splitlines() if l.strip()]
        return lines, 0.88 if lines else 0.0
