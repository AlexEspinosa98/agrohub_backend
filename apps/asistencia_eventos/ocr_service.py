"""Best-effort OCR extraction for AgroHub's handwritten "Formato de
Asistencia" sheets (see docs/asistencia-eventos.md).

Runs fully offline/on-CPU via PaddleOCR (PP-OCRv6) — chosen over Tesseract
because this form is handwritten, not printed: Tesseract failed to read a
single attendee row on the real sample form, while PaddleOCR correctly
transcribed document numbers, dates and times. Accuracy is still inherently
limited on handwriting (names especially), which is why this only produces a
*draft*: the scan endpoint returns it (plus the raw recognized text as a
fallback) for a human to review and correct before the confirm endpoint
actually saves anything.

Column detection works by locating the table's header row(s) — PaddleOCR
sometimes splits a two-line header ("Tipo y numero de" / "documento") into
separate boxes, so header keywords are accumulated across consecutive rows
until a row with no recognizable header keyword is hit — and using each
known header word's x-position as a column boundary. There's no ML table
model involved, just position-based bucketing of recognized text into
whichever column its x-coordinate falls under. When a single detection box
spans multiple columns (PaddleOCR sometimes merges adjacent cells, e.g.
"fundacion 3051035950" for Municipio+Teléfono), its words are re-split and
each word's x-position is estimated proportionally within the box.
"""

import io
import re

from pdf2image import convert_from_bytes
from PIL import Image
from rest_framework import status as http_status
from rest_framework.exceptions import APIException

_OCR_ENGINE = None


class OcrUnavailable(APIException):
    status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "El servicio de OCR no está disponible en este servidor"


def _get_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OcrUnavailable(detail="paddleocr no está instalado en este entorno") from exc
        _OCR_ENGINE = PaddleOCR(lang="es")
    return _OCR_ENGINE


# Bounds each label's capture at the next known label — two labeled fields
# (e.g. "Responsable: ..." and "Lugar: ...") can sit side by side on the same
# visual row, and an unbounded ".+" would swallow both.
_LABELS = r"(?:tema|responsable|lugar|fecha|hora\s*inicio|hora\s*final)"

_HEADER_PATTERNS = {
    "tema": re.compile(rf"tema\s*[:\-]?\s*(.+?)(?=\s+{_LABELS}\b|$)", re.IGNORECASE),
    "responsable": re.compile(rf"responsable\s*[:\-]?\s*(.+?)(?=\s+{_LABELS}\b|$)", re.IGNORECASE),
    "lugar": re.compile(rf"lugar\s*[:\-]?\s*(.+?)(?=\s+{_LABELS}\b|$)", re.IGNORECASE),
    "fecha": re.compile(r"fecha[^:]*[:\-]?\s*([0-3]?\d[\/\-][01]?\d[\/\-]\d{2,4})", re.IGNORECASE),
    "hora_inicio": re.compile(r"hora\s*inicio\s*[:\-]?\s*([\d:.\s]{3,8}\s*[ap]\.?\s?m\.?)", re.IGNORECASE),
    "hora_final": re.compile(r"hora\s*final\s*[:\-]?\s*([\d:.\s]{3,8}\s*[ap]\.?\s?m\.?)", re.IGNORECASE),
}

# Order matters: longer/more specific keywords first so e.g. "documento"
# isn't shadowed by a coincidental shorter match.
_COLUMN_KEYWORDS = [
    ("documento", ["documento", "tipoynumero"]),
    ("nombre", ["nombre"]),
    ("municipio", ["municipio"]),
    ("telefono", ["telefono"]),
    ("edad", ["edad"]),
    ("ninguno", ["ninguno"]),
    ("ind", ["ind"]),
    ("afro", ["afro"]),
    ("rom", ["rom"]),
    ("rai", ["rai"]),
    ("f", ["f"]),
    ("m", ["m"]),
    ("o", ["o"]),
]

_ETNIA_POR_COLUMNA = {"ind": "indigena", "afro": "afro", "rom": "rom", "rai": "raizal"}
_ACENTOS = str.maketrans("áéíóúñ", "aeioun")


def _normalize_token(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower().translate(_ACENTOS))


def _column_for_header_word(raw_text: str, already_found: set):
    token = _normalize_token(raw_text)
    if not token:
        # PaddleOCR reads the "O" (Otro) gender header as a literal zero.
        if raw_text.strip() == "0" and "o" not in already_found:
            return "o"
        return None
    for col, keywords in _COLUMN_KEYWORDS:
        for kw in keywords:
            # Single-letter columns (F/M/O) need an exact match — "in" would
            # match almost any word, since f/m/o are common letters.
            if (len(kw) == 1 and token == kw) or (len(kw) > 1 and kw in token):
                return col
    return None


def _load_pages(upload_file) -> list:
    upload_file.seek(0)
    raw = upload_file.read()
    name = (upload_file.name or "").lower()
    if name.endswith(".pdf") or raw[:4] == b"%PDF":
        return convert_from_bytes(raw, dpi=300)
    return [Image.open(io.BytesIO(raw)).convert("RGB")]


def _run_ocr(image) -> list:
    """Returns a flat list of {"text","left","top","bottom","right"} boxes."""
    import numpy as np

    result = _get_engine().predict(np.array(image))
    if not result:
        return []
    page = result[0]
    words = []
    for text, box in zip(page.get("rec_texts", []), page.get("rec_boxes", [])):
        text = text.strip()
        if not text:
            continue
        x1, y1, x2, y2 = (float(v) for v in box)
        words.append({"text": text, "left": x1, "top": y1, "bottom": y2, "right": x2})
    return words


def _cluster_rows(words: list) -> list:
    if not words:
        return []
    heights = sorted(w["bottom"] - w["top"] for w in words)
    median_h = heights[len(heights) // 2] or 30
    threshold = median_h * 0.6

    ordered = sorted(words, key=lambda w: w["top"])
    rows = [[ordered[0]]]
    current_top = ordered[0]["top"]
    for word in ordered[1:]:
        if word["top"] - current_top <= threshold:
            rows[-1].append(word)
        else:
            rows.append([word])
            current_top = word["top"]
    return [sorted(row, key=lambda w: w["left"]) for row in rows]


def _expand_multiword_boxes(row: list) -> list:
    """Splits a box holding several space-separated words (PaddleOCR merged
    adjacent table cells) into one entry per word, estimating each word's
    x-position proportionally within the box."""
    expanded = []
    for word in row:
        tokens = word["text"].split()
        if len(tokens) <= 1:
            expanded.append(word)
            continue
        total_len = len(word["text"])
        width = word["right"] - word["left"]
        cursor = 0
        for token in tokens:
            idx = word["text"].index(token, cursor)
            cursor = idx + len(token)
            center_frac = (idx + len(token) / 2) / total_len if total_len else 0.5
            expanded.append(
                {
                    "text": token,
                    "left": word["left"] + center_frac * width,
                    "top": word["top"],
                    "bottom": word["bottom"],
                }
            )
    return expanded


def _parse_header(rows: list) -> dict:
    joined = "\n".join(" ".join(w["text"] for w in row) for row in rows[:14])
    header = {}
    for field, pattern in _HEADER_PATTERNS.items():
        matches = pattern.findall(joined)
        if matches:
            # The form's own "VERSIÓN/FECHA/PÁGINA" print metadata sits above
            # the real event fields and can also match "fecha" — the real
            # field is always the later occurrence in reading order.
            header[field] = matches[-1].strip(" .")
    return header


def _detect_columns(rows: list):
    anchors = {}
    header_bottom = None
    started = False
    for row in rows:
        found_any = False
        for word in row:
            col = _column_for_header_word(word["text"], set(anchors))
            if col:
                found_any = True
                if col not in anchors:
                    anchors[col] = word["left"]
        if found_any:
            started = True
            header_bottom = max(w["bottom"] for w in row)
        elif started:
            break
    if not anchors:
        return None, None

    ordered = sorted(anchors.items(), key=lambda kv: kv[1])
    boundaries = []
    for i, (col, x) in enumerate(ordered):
        left_bound = 0 if i == 0 else (ordered[i - 1][1] + x) / 2
        boundaries.append((left_bound, col))
    return boundaries, header_bottom


def _column_for_x(x: float, boundaries: list) -> str:
    col = boundaries[0][1]
    for left_bound, name in boundaries:
        if x >= left_bound:
            col = name
        else:
            break
    return col


def _best_digit_run(text: str, min_len=5, max_len=12):
    runs = [r for r in re.findall(r"\d+", text) if min_len <= len(r) <= max_len]
    return max(runs, key=len) if runs else None


def _parse_table(rows: list) -> list:
    boundaries, header_bottom = _detect_columns(rows)
    if not boundaries:
        return []

    asistentes = []
    for row in rows:
        if row[0]["top"] <= header_bottom:
            continue

        expanded = _expand_multiword_boxes(row)
        cells = {}
        for word in expanded:
            col = _column_for_x(word["left"], boundaries)
            cells.setdefault(col, []).append(word["text"])

        numero_documento = re.sub(r"[^0-9]", "", " ".join(cells.get("documento", [])))
        if len(numero_documento) < 5:
            fallback = _best_digit_run(" ".join(w["text"] for w in row))
            numero_documento = fallback or ""
        if len(numero_documento) < 5:
            continue  # not an attendee row (footer/legend text, stray marks)

        # The "No" row-number column has no header keyword to anchor a
        # boundary on, so its digit falls into the leftmost (nombre) bucket.
        nombre = " ".join(t for t in cells.get("nombre", []) if not t.isdigit()).strip()
        municipio = " ".join(cells.get("municipio", [])).strip()
        telefono = re.sub(r"[^0-9]", "", " ".join(cells.get("telefono", [])))
        if len(telefono) < 7:
            candidatos = [
                r
                for r in re.findall(r"\d+", " ".join(w["text"] for w in row))
                if 7 <= len(r) <= 10 and r != numero_documento
            ]
            telefono = max(candidatos, key=len) if candidatos else (telefono or None)
        edad_raw = re.sub(r"[^0-9]", "", " ".join(cells.get("edad", [])))
        edad = int(edad_raw) if edad_raw and len(edad_raw) <= 3 else None

        genero = None
        for letra in ("f", "m", "o"):
            if cells.get(letra):
                genero = letra.upper()
                break

        pertenencia_etnica = "ninguno"
        for columna, etiqueta in _ETNIA_POR_COLUMNA.items():
            if cells.get(columna):
                pertenencia_etnica = etiqueta
                break

        asistentes.append(
            {
                "nombre": nombre or None,
                "tipo_documento": None,
                "numero_documento": numero_documento,
                "municipio": municipio or None,
                "telefono": telefono or None,
                "edad": edad,
                "genero": genero,
                "pertenencia_etnica": pertenencia_etnica,
            }
        )
    return asistentes


def extract_asistencia(upload_file) -> dict:
    try:
        pages = _load_pages(upload_file)
    except Exception as exc:  # noqa: BLE001
        raise OcrUnavailable(detail=f"No se pudo leer el archivo: {exc}") from exc

    all_rows = []
    raw_text_parts = []
    for page in pages:
        words = _run_ocr(page)
        raw_text_parts.append(" ".join(w["text"] for w in sorted(words, key=lambda w: (w["top"], w["left"]))))
        all_rows.extend(_cluster_rows(words))

    header = _parse_header(all_rows)
    asistentes = _parse_table(all_rows)

    return {
        "tema": header.get("tema"),
        "responsable": header.get("responsable"),
        "lugar": header.get("lugar"),
        "fecha": header.get("fecha"),
        "hora_inicio": header.get("hora_inicio"),
        "hora_final": header.get("hora_final"),
        "asistentes": asistentes,
        "texto_crudo_ocr": "\n".join(raw_text_parts).strip(),
    }
