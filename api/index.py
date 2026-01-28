import os
import sys

# Agrega el path raíz para importar main.py
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app  # noqa: E402

# Vercel toma la variable app como ASGI entrypoint
