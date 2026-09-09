"""Best-effort OCR extraction for AgroHub's handwritten "Formato de
Asistencia" sheets (see docs/asistencia-eventos.md).

Two engines, picked via settings.ASISTENCIA_OCR_ENGINE ("paddleocr" | "llm"):

- "paddleocr" (default): 100% offline/on-CPU via PaddleOCR (PP-OCRv6) — chosen
  over Tesseract because this form is handwritten, not printed: Tesseract
  failed to read a single attendee row on the real sample form, while
  PaddleOCR correctly transcribed document numbers, dates and times. The
  table structure is then recovered with hand-written position-bucketing
  heuristics (see _detect_columns/_parse_table below), which is the fragile
  part — it breaks on merged cells or a column that doesn't line up.

- "llm": sends each full page image to a local vision-language model server
  (llama.cpp's llama-server running Qwen2.5-VL, see
  systemd/agrohub-ocr-llm.service) and asks it to return the same JSON shape
  directly — no hand-rolled column bucketing needed, since the model reasons
  about the whole table at once. Still 100% local/free (no external API,
  no per-request cost) — just a heavier local model instead of a lighter one.
  Grammar-constrained decoding (response_format=json_schema) guarantees the
  output actually parses as JSON in this schema; it does NOT guarantee the
  *content* is correct, so the prompt explicitly tells the model to return
  null instead of guessing on illegible handwriting.

Either way, accuracy on handwriting (names especially) is inherently
limited, which is why this only produces a *draft*: the scan endpoint
returns it (plus the raw recognized text as a fallback) for a human to
review and correct before the confirm endpoint actually saves anything —
that human step is what protects against an LLM engine confidently
hallucinating a plausible-looking but wrong ID number.
"""

import base64
import io
import json
import re

import requests
from django.conf import settings
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
        # enable_mkldnn=False: con oneDNN (el default en CPU) el detector de texto revienta
        # con "(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support
        # [pir::ArrayAttribute<pir::DoubleAttribute>]" — un bug de PaddlePaddle 3.x con su
        # nuevo executor PIR sobre oneDNN, no algo de este código. Confirmado en el servidor
        # (Ubuntu 22.04, CPU-only) que desactivar oneDNN evita el crash sin afectar la
        # precisión; solo hace la inferencia un poco más lenta.
        _OCR_ENGINE = PaddleOCR(lang="es", enable_mkldnn=False)
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


def _extract_with_paddleocr(pages: list) -> dict:
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


# JSON Schema for the LLM engine's response_format — llama-server turns this into a GBNF
# grammar and constrains sampling to it, so the output is *guaranteed* to parse as JSON in
# this exact shape. It does NOT guarantee the values themselves are correct — see the module
# docstring on why the two-step draft/confirm flow still matters with this engine.
# NOTE: a property only gets forced INTO the output if it's listed in "required" — for a
# non-required property, schema-constrained decoding lets the model omit the key entirely
# instead of writing null, which is what happened here in testing (every "nombre" and
# "tipo_documento" key vanished from a real response, not just their values). So every
# property is required here even though most may legitimately be null — "required" only
# forces the *key* to exist, the "null" in each type/enum is what allows an unsure value.
# tipo_documento is deliberately NOT asked of the model: the real form never has a separate
# "tipo de documento" column (PaddleOCR always leaves it null too — see _parse_table), and
# asking for it anyway once caused the model to shift every other value by one field trying
# to fill it in (numero_documento ended up holding the phone number, tipo_documento the real
# ID). It's filled in as null in _extract_with_llm instead, same as the PaddleOCR path.
_ASISTENTE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "nombre": {"type": ["string", "null"]},
        "numero_documento": {"type": ["string", "null"]},
        "municipio": {"type": ["string", "null"]},
        "telefono": {"type": ["string", "null"]},
        "edad": {"type": ["integer", "null"]},
        "genero": {"enum": ["F", "M", "O", None]},
        "pertenencia_etnica": {"enum": ["ninguno", "indigena", "afro", "rom", "raizal", None]},
    },
    "required": ["nombre", "numero_documento", "municipio", "telefono", "edad", "genero", "pertenencia_etnica"],
}

_PAGINA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "tema": {"type": ["string", "null"]},
        "responsable": {"type": ["string", "null"]},
        "lugar": {"type": ["string", "null"]},
        "fecha": {"type": ["string", "null"]},
        "hora_inicio": {"type": ["string", "null"]},
        "hora_final": {"type": ["string", "null"]},
        "asistentes": {"type": "array", "items": _ASISTENTE_JSON_SCHEMA},
    },
    "required": ["tema", "responsable", "lugar", "fecha", "hora_inicio", "hora_final", "asistentes"],
}

_LLM_SYSTEM_PROMPT = """Eres un asistente que transcribe planillas de asistencia a eventos de AgroHub \
(Colombia), llenadas a mano. Se te da la imagen de UNA página de la planilla.

Devuelve ÚNICAMENTE el JSON pedido, sin explicaciones ni markdown, con esta información:
- tema, responsable, lugar, fecha, hora_inicio, hora_final: los datos del encabezado del evento. \
Si esta página no trae encabezado (por ejemplo, es una página de continuación de la tabla), deja \
esos campos en null.
- asistentes: una fila por cada persona en la tabla, con nombre, numero_documento, municipio, \
telefono, edad, genero y pertenencia_etnica.

Reglas importantes:
1. Transcribe numero_documento y telefono dígito por dígito, exactamente como están escritos — \
son identificadores reales, no los redondees ni corrijas.
2. Si un campo es ilegible o no estás seguro, devuelve null — NUNCA inventes un valor solo porque \
parezca razonable. Es preferible null a un dato incorrecto.
3. genero y pertenencia_etnica normalmente se marcan con una X o un check dentro de una columna: \
usa la columna donde está la marca, no un valor por defecto.
4. Ignora firmas, huellas o marcas en columnas que no correspondan a estos campos."""


def _encode_page_png_b64(image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _run_llm_ocr(image) -> dict:
    """Sends one full page image to the local vision LLM and returns its structured
    extraction for that page (same shape as one page's worth of _extract_with_paddleocr's
    output). Raises OcrUnavailable (503) if the local llama-server isn't reachable or
    doesn't return something the schema-constrained decoding should have prevented."""
    payload = {
        "messages": [
            {"role": "system", "content": _LLM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{_encode_page_png_b64(image)}"},
                    },
                    {"type": "text", "text": "Transcribe esta página según las instrucciones."},
                ],
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "pagina_asistencia", "schema": _PAGINA_JSON_SCHEMA, "strict": True},
        },
        "temperature": 0,
    }
    try:
        response = requests.post(settings.ASISTENCIA_LLM_OCR_URL, json=payload, timeout=300)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except requests.RequestException as exc:
        raise OcrUnavailable(detail=f"El servicio de OCR (LLM local) no respondió: {exc}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise OcrUnavailable(detail="El servicio de OCR (LLM local) devolvió una respuesta inesperada") from exc


def _extract_with_llm(pages: list) -> dict:
    header = {}
    asistentes = []
    raw_parts = []
    for page in pages:
        page_data = _run_llm_ocr(page)
        raw_parts.append(json.dumps(page_data, ensure_ascii=False))
        for campo in ("tema", "responsable", "lugar", "fecha", "hora_inicio", "hora_final"):
            if not header.get(campo) and page_data.get(campo):
                header[campo] = page_data[campo]
        for asistente in page_data.get("asistentes") or []:
            asistente["tipo_documento"] = None
            asistentes.append(asistente)

    return {
        "tema": header.get("tema"),
        "responsable": header.get("responsable"),
        "lugar": header.get("lugar"),
        "fecha": header.get("fecha"),
        "hora_inicio": header.get("hora_inicio"),
        "hora_final": header.get("hora_final"),
        "asistentes": asistentes,
        "texto_crudo_ocr": "\n".join(raw_parts),
    }


def extract_asistencia(upload_file) -> dict:
    try:
        pages = _load_pages(upload_file)
    except Exception as exc:  # noqa: BLE001
        raise OcrUnavailable(detail=f"No se pudo leer el archivo: {exc}") from exc

    if settings.ASISTENCIA_OCR_ENGINE == "llm":
        return _extract_with_llm(pages)
    return _extract_with_paddleocr(pages)
