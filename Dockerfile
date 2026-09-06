FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# poppler-utils: PDF->image conversion for the asistencia_eventos OCR scan
# endpoint (pdf2image shells out to pdftoppm).
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
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
