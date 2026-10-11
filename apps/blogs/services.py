import io
import os
import re
import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.blogs.models import Blog, Etiqueta

IMAGEN_MAX_BYTES = 5 * 1024 * 1024
IMAGEN_EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
PALABRAS_POR_MINUTO = 200


def validar_imagen(upload, campo="portada"):
    if os.path.splitext(upload.name or "")[1].lower() not in IMAGEN_EXTENSIONES:
        raise ValidationError({campo: f"Formato no permitido. Usa: {', '.join(IMAGEN_EXTENSIONES)}"})
    if upload.size > IMAGEN_MAX_BYTES:
        raise ValidationError({campo: f"La imagen supera el máximo de {IMAGEN_MAX_BYTES // (1024 * 1024)} MB."})
    from PIL import Image

    upload.seek(0)
    try:
        Image.open(io.BytesIO(upload.read())).verify()
    except Exception as exc:  # noqa: BLE001
        raise ValidationError({campo: "El archivo no es una imagen válida."}) from exc
    finally:
        upload.seek(0)


def guardar_imagen(upload, carpeta, campo="portada"):
    validar_imagen(upload, campo)
    return default_storage.save(f"blogs/{carpeta}/{uuid.uuid4()}_{os.path.basename(upload.name)}", upload)


def _slug_unico(base, excluir_id=None):
    base = slugify(base)[:260] or "entrada"
    if base.isdigit():  # un slug solo de dígitos se confundiría con un id
        base = f"b-{base}"
    slug, n = base, 2
    while Blog.objects.filter(slug=slug).exclude(id=excluir_id).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def tiempo_lectura(contenido):
    return max(1, round(len(re.findall(r"\w+", contenido or "")) / PALABRAS_POR_MINUTO))


def _asignar_etiquetas(blog, nombres):
    limpias, vistas = [], set()
    for n in nombres:
        n = " ".join(n.split())
        if n and n.lower() not in vistas:
            vistas.add(n.lower())
            limpias.append(n)
    objs = []
    for n in limpias:
        obj = Etiqueta.objects.filter(nombre__iexact=n).first() or Etiqueta.objects.create(nombre=n)
        objs.append(obj)
    blog.etiquetas.set(objs)


def _resolver_fecha(estado, fecha, actual=None):
    """publicado sin fecha -> ahora (o la que ya tenía); borrador conserva su fecha si la hay."""
    if estado == Blog.ESTADO_PUBLICADO and not fecha:
        return actual or timezone.now()
    return fecha if fecha is not None else actual


@transaction.atomic
def crear(data, creado_por=None):
    data = dict(data)
    etiquetas = data.pop("etiquetas", [])
    estado = data.pop("estado", Blog.ESTADO_BORRADOR)
    fecha = data.pop("fecha_publicacion", None)
    slug = data.pop("slug", None)
    if slug and Blog.objects.filter(slug=slug).exists():
        raise ValidationError({"slug": f"Ya existe una entrada con el slug '{slug}'."})
    blog = Blog.objects.create(
        slug=slug or _slug_unico(data["titulo"]),
        estado=estado,
        fecha_publicacion=_resolver_fecha(estado, fecha),
        autor=(data.pop("autor", None) or getattr(creado_por, "name", None) or "").strip() or None,
        creado_por=creado_por,
        **{k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()},
    )
    _asignar_etiquetas(blog, etiquetas)
    return blog


@transaction.atomic
def actualizar(blog, data, editado_por=None):
    data = dict(data)
    etiquetas = data.pop("etiquetas", None)
    if "slug" in data and data["slug"] != blog.slug and Blog.objects.filter(slug=data["slug"]).exclude(id=blog.id).exists():
        raise ValidationError({"slug": f"Ya existe una entrada con el slug '{data['slug']}'."})
    estado = data.pop("estado", blog.estado)
    fecha = data.pop("fecha_publicacion", blog.fecha_publicacion)
    blog.estado = estado
    blog.fecha_publicacion = _resolver_fecha(estado, fecha, blog.fecha_publicacion)
    for campo, valor in data.items():
        setattr(blog, campo, valor.strip() if isinstance(valor, str) else valor)
    blog.editado_por = editado_por
    blog.save()
    if etiquetas is not None:
        _asignar_etiquetas(blog, etiquetas)
    return blog


def poner_portada(blog, upload, editado_por=None):
    anterior = blog.portada
    blog.portada = guardar_imagen(upload, "portadas")
    blog.editado_por = editado_por
    blog.save()
    if anterior:
        default_storage.delete(anterior)


def quitar_portada(blog, editado_por=None):
    anterior = blog.portada
    blog.portada = None
    blog.editado_por = editado_por
    blog.save()
    if anterior:
        default_storage.delete(anterior)


def eliminar(blog):
    portada = blog.portada
    blog.delete()
    if portada:
        default_storage.delete(portada)


def listar(params, editor=False):
    """Públicas por defecto. Un editor puede pasar ?estado=borrador|publicado|todos."""
    qs = Blog.objects.all()
    estado = (params.get("estado") or "").strip().lower() if editor else ""
    if estado == "borrador":
        qs = qs.filter(estado=Blog.ESTADO_BORRADOR)
    elif estado == "todos":
        pass
    else:
        qs = qs.filter(estado=Blog.ESTADO_PUBLICADO, fecha_publicacion__lte=timezone.now())
    if params.get("etiqueta"):
        qs = qs.filter(etiquetas__nombre__iexact=params["etiqueta"].strip())
    for palabra in (params.get("q") or "").split():
        qs = qs.filter(
            Q(titulo__icontains=palabra) | Q(resumen__icontains=palabra) | Q(contenido__icontains=palabra)
            | Q(autor__icontains=palabra) | Q(etiquetas__nombre__icontains=palabra)
        )
    return qs.distinct().order_by("-fecha_publicacion", "-id")


def etiquetas_publicas():
    """Etiquetas con la cantidad de entradas publicadas que las usan."""
    ahora = timezone.now()
    filtro = Q(blogs__estado=Blog.ESTADO_PUBLICADO, blogs__fecha_publicacion__lte=ahora)
    return [
        {"nombre": e.nombre, "total": e.total}
        for e in Etiqueta.objects.annotate(total=Count("blogs", filter=filtro)).filter(total__gt=0).order_by("nombre")
    ]


def relacionados(blog, limite=3):
    ids = list(blog.etiquetas.values_list("id", flat=True))
    if not ids:
        return []
    qs = (
        Blog.objects.filter(estado=Blog.ESTADO_PUBLICADO, fecha_publicacion__lte=timezone.now(), etiquetas__in=ids)
        .exclude(id=blog.id).distinct().order_by("-fecha_publicacion")[:limite]
    )
    return list(qs)
