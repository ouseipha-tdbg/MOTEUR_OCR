# =============================================================
# Reset complet du venv zamapay-ocr-lab
# Install ordonné, versions figées, freeze final.
# =============================================================
# Usage : .\setup-venv.ps1
# Après ce script, ne JAMAIS refaire pip install sans passer par
# requirements-lock.txt sinon on casse tout.

$ErrorActionPreference = "Stop"

Write-Host "==> 1. Suppression de l'ancien venv..." -ForegroundColor Cyan
if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }

Write-Host "==> 2. Création du nouveau venv..." -ForegroundColor Cyan
python -m venv .venv

Write-Host "==> 3. Activation du venv..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

Write-Host "==> 4. Upgrade pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

Write-Host "==> 5. Numpy stack (fondations)..." -ForegroundColor Cyan
pip install "numpy==1.26.4" "Pillow==10.4.0" "scipy==1.11.4"

Write-Host "==> 6. OpenCV..." -ForegroundColor Cyan
pip install "opencv-python-headless==4.10.0.84"

Write-Host "==> 7. Torch CUDA 12.1 (pour la RTX)..." -ForegroundColor Cyan
pip install "torch==2.5.1" "torchvision==0.20.1" --index-url https://download.pytorch.org/whl/cu121

Write-Host "==> 8. Transformers stack..." -ForegroundColor Cyan
pip install "huggingface-hub==0.26.2" "tokenizers==0.20.3" "transformers==4.45.2" "accelerate==0.34.2" "safetensors==0.4.5"

Write-Host "==> 9. Deps VLM (GOT-OCR2, tokenizers avancés)..." -ForegroundColor Cyan
pip install "sentencepiece==0.2.0" "tiktoken==0.7.0" verovio

Write-Host "==> 10. RapidOCR (moteur 'paddle')..." -ForegroundColor Cyan
pip install "rapidocr-onnxruntime==1.3.24"

Write-Host "==> 11. FastAPI stack..." -ForegroundColor Cyan
pip install "fastapi==0.115.0" "uvicorn[standard]==0.30.6" "python-multipart==0.0.9" "python-dotenv==1.0.1"

Write-Host "==> 12. Gemini..." -ForegroundColor Cyan
pip install "google-generativeai==0.8.3"

Write-Host "==> 13. Réparation numpy si des installs précédents l'ont bougé..." -ForegroundColor Cyan
pip install "numpy==1.26.4" --force-reinstall --no-deps

Write-Host ""
Write-Host "==> 14. Vérifications..." -ForegroundColor Cyan
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
python -c "from transformers import AutoModel, DonutProcessor, NougatProcessor, TrOCRProcessor, VisionEncoderDecoderModel; print('Transformers OK')"
python -c "import rapidocr_onnxruntime; print('RapidOCR OK')"
python -c "import google.generativeai as genai; print('Gemini OK')"

Write-Host ""
Write-Host "==> 15. FREEZE des versions..." -ForegroundColor Cyan
pip freeze > requirements-lock.txt

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host " Setup terminé. Versions figées dans requirements-lock.txt" -ForegroundColor Green
Write-Host " Lance maintenant : python app.py" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
