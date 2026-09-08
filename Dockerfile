FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# poppler-utils: PDF->image conversion for the asistencia_eventos OCR scan
# endpoint (pdf2image shells out to pdftoppm). libgl1/libglib2.0-0/libsm6/
# libxext6/libxrender1: opencv-contrib-python (pulled in by paddlex) is the
# GUI-enabled build, not -headless, so `import cv2` needs these even though
# nothing here ever opens a window — without them the first request fails
# with "ImportError: libGL.so.1", and every request after that in the same
# worker fails instead with "RuntimeError: PDX has already been initialized"
# (paddlex's internal state gets marked initialized before the import blows
# up, and that half-initialized state is never retried automatically).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        poppler-utils libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Bakes the PaddleOCR model weights into the image at build time (instead of
# on first request) so the onpremise deployment doesn't need internet access
# at runtime.
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='es')"

COPY . .
RUN mkdir -p /app/staticfiles /app/media \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
