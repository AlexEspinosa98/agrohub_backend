import os
import sys
from fastapi import FastAPI

# Asegura que el path raíz quede accesible
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from main import app  # noqa: E402

# Punto de chequeo para Vercel logs
@app.get("/__health")
async def health():
    return {"status": "ok"}
