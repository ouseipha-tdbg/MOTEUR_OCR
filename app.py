"""Zamapay OCR Lab — comparateur de moteurs OCR pour intégration KYC/KYB.

Endpoints:
  GET  /              -> UI
  GET  /health        -> {"status": "ok"}
  GET  /engines       -> liste moteurs dispo
  POST /ocr           -> upload + comparaison multi-moteurs

Usage prod (yam-bot): importer engines.get_engine + parsers.parse directement.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from engines import REGISTRY, get_engine
from parsers import REGISTRY as PARSER_REGISTRY, parse

app = FastAPI(title="Zamapay OCR Lab", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/engines")
def list_engines():
    return {"engines": list(REGISTRY.keys()), "doc_types": list(PARSER_REGISTRY.keys())}


@app.post("/ocr")
async def ocr(
    doc_type: str = Form(...),
    engines: str = Form(...),  # csv: "paddle,tesseract,gemini"
    recto: UploadFile = File(...),
    verso: UploadFile | None = File(None),
):
    engine_names = [e.strip() for e in engines.split(",") if e.strip()]

    # save uploads
    uid = uuid.uuid4().hex[:8]
    paths = []
    for f in (recto, verso):
        if f is None: continue
        ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
        dst = os.path.join(config.UPLOAD_DIR, f"{uid}_{len(paths)}{ext}")
        with open(dst, "wb") as out: out.write(await f.read())
        paths.append(dst)

    # run engines en parallèle
    def _run(name):
        try:
            eng = get_engine(name)
        except Exception as e:
            return {
                "engine": name, "lines": [], "full_text": "",
                "confidence": 0.0, "elapsed_ms": 0,
                "error": f"engine indisponible: {e}", "parsed": {},
            }
        try:
            res = eng.extract(paths)
            parsed = parse(doc_type, res.lines) if not res.error else {}
            return {**res.to_dict(), "parsed": parsed}
        except Exception as e:
            return {
                "engine": name, "lines": [], "full_text": "",
                "confidence": 0.0, "elapsed_ms": 0,
                "error": str(e), "parsed": {},
            }

    with ThreadPoolExecutor(max_workers=len(engine_names) or 1) as pool:
        results = list(pool.map(_run, engine_names))

    return JSONResponse({
        "doc_type": doc_type,
        "uid": uid,
        "files": paths,
        "results": results,
    })


# static UI
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
