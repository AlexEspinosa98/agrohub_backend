import io
import os
import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.cartillas.models import Cartilla, CartillaIndice

PDF_MAX_BYTES = 20 * 1024 * 1024  # = límite de cuerpo de nginx (client_max_body_size 20M)


def leer_pdf(upload):
    """Valida que sea un PDF y devuelve (bytes, nº de páginas o None)."""
    if not (upload.name or "").lower().endswith(".pdf"):
        raise ValidationError({"archivo": "El archivo debe ser un PDF (.pdf)."})
    if upload.size > PDF_MAX_BYTES:
        raise ValidationError({"archivo": f"El PDF supera el máximo de {PDF_MAX_BYTES // (1024 * 1024)} MB."})
    upload.seek(0)
    raw = upload.read()
    upload.seek(0)
    if not raw.startswith(b"%PDF"):
        raise ValidationError({"archivo": "El archivo no es un PDF válido."})
    try:
        from pdf2image import pdfinfo_from_bytes

        paginas = int(pdfinfo_from_bytes(raw)["Pages"])
    except Exception:  # noqa: BLE001 — si poppler no puede, se pide `paginas` o queda vacío
        paginas = None
    return raw, paginas


def _guardar_archivo(upload):
    nombre = f"{uuid.uuid4()}_{os.path.basename(upload.name)}"
    return default_storage.save(f"cartillas/{nombre}", upload)


def _reemplazar_indice(cartilla, indice):
    cartilla.indice.all().delete()
    CartillaIndice.objects.bulk_create(
        [
            CartillaIndice(cartilla=cartilla, titulo=i["titulo"].strip(), pagina=i["pagina"], orden=n)
            for n, i in enumerate(sorted(indice, key=lambda x: x["pagina"]))
        ]
    )


def _limpiar(data):
    for campo in ("tema", "titulo", "resumen"):
        if campo in data:
            data[campo] = data[campo].strip()
    if "para" in data:
        data["para"] = (data["para"] or "").strip() or None
    return data


@transaction.atomic
def crear(data, upload, creado_por=None):
    _, paginas_pdf = leer_pdf(upload)
    data = _limpiar(dict(data))
    indice = data.pop("indice", [])
    paginas = data.get("paginas") or paginas_pdf
    if paginas and indice and any(i["pagina"] > paginas for i in indice):
        raise ValidationError({"indice": f"Hay páginas fuera del PDF (tiene {paginas})."})
    data["paginas"] = paginas
    cartilla = Cartilla.objects.create(
        archivo=_guardar_archivo(upload), tamano_bytes=upload.size, creado_por=creado_por, **data
    )
    _reemplazar_indice(cartilla, indice)
    return cartilla


@transaction.atomic
def actualizar(cartilla, data, editado_por=None):
    data = _limpiar(dict(data))
    indice = data.pop("indice", None)
    for campo, valor in data.items():
        setattr(cartilla, campo, valor)
    cartilla.editado_por = editado_por
    cartilla.save()
    if indice is not None:
        _reemplazar_indice(cartilla, indice)
    return cartilla


def reemplazar_pdf(cartilla, upload, editado_por=None):
    _, paginas = leer_pdf(upload)
    anterior = cartilla.archivo
    cartilla.archivo = _guardar_archivo(upload)
    cartilla.tamano_bytes = upload.size
    if paginas:
        cartilla.paginas = paginas
    cartilla.editado_por = editado_por
    cartilla.save()
    if anterior:
        default_storage.delete(anterior)
    return cartilla


def eliminar(cartilla):
    archivo = cartilla.archivo
    cartilla.delete()
    if archivo:
        default_storage.delete(archivo)


def buscar(params):
    """Listado por fecha de publicación (más reciente primero). `q` NO es exacta: se parte en
    palabras y cada una debe aparecer (sin importar mayúsculas) en el tema, el título, el resumen,
    el público o algún título del índice. Filtros opcionales: `tema` y `para`."""
    qs = Cartilla.objects.all()
    if params.get("tema"):
        qs = qs.filter(tema__iexact=params["tema"].strip())
    if params.get("para"):
        qs = qs.filter(para__iexact=params["para"].strip())
    for palabra in (params.get("q") or "").split():
        qs = qs.filter(
            Q(tema__icontains=palabra) | Q(titulo__icontains=palabra) | Q(resumen__icontains=palabra)
            | Q(para__icontains=palabra) | Q(indice__titulo__icontains=palabra)
        )
    return qs.distinct().order_by("-fecha_publicacion", "-id")
