import json

from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, Paginator
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.blogs import services
from apps.blogs.models import Blog
from apps.blogs.serializers import BlogCreateSerializer, BlogUpdateSerializer
from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.permissions import IsAuthenticatedWithRole, IsContenidoEditorRole

_AUTH = [TokenHeaderAuthentication]
# Escribir: admin, superadmin, investigador y comunicaciones. Leer lo publicado es público.
_EDITORES = [IsAuthenticatedWithRole, IsContenidoEditorRole]


def _ok(message, data, code=status.HTTP_200_OK):
    return Response({"status": code, "message": message, "data": data}, status=code)


def _es_editor(request) -> bool:
    return getattr(request.user, "role", None) in ("admin", "superadmin", "investigador", "comunicaciones")


def _nombre(usuario):
    return (getattr(usuario, "name", None) or getattr(usuario, "email", None)) if usuario else None


def _url(ruta):
    return default_storage.url(ruta) if ruta else None


def _resumen(b: Blog, editor=False) -> dict:
    data = {
        "id": b.id,
        "slug": b.slug,
        "titulo": b.titulo,
        "resumen": b.resumen,
        "portada": _url(b.portada),
        "etiquetas": [e.nombre for e in b.etiquetas.all()],
        "autor": b.autor,
        "fecha_publicacion": b.fecha_publicacion,
        "tiempo_lectura_min": services.tiempo_lectura(b.contenido),
    }
    if editor:
        data["estado"] = b.estado
        data["publicado"] = b.publicado
    return data


def _detalle(b: Blog, editor=False) -> dict:
    data = _resumen(b, editor)
    data["contenido"] = b.contenido
    data["relacionados"] = [_resumen(r) for r in services.relacionados(b)] if b.publicado else []
    if editor:
        data.update(
            creado_por=_nombre(b.creado_por), creado_por_id=b.creado_por_id,
            editado_por=_nombre(b.editado_por), created_at=b.created_at, updated_at=b.updated_at,
        )
    return data


def _por_ref(ref: str) -> Blog:
    qs = Blog.objects.select_related("creado_por", "editado_por").prefetch_related("etiquetas")
    blog = qs.filter(id=int(ref)).first() if ref.isdigit() else qs.filter(slug=ref).first()
    if not blog:
        raise NotFound("Entrada no encontrada")
    return blog


def _por_id(blog_id: int) -> Blog:
    return _por_ref(str(blog_id))


class BlogsView(APIView):
    """GET (listado + búsqueda) público; POST (crear entrada) solo editores."""

    authentication_classes = _AUTH

    def get_permissions(self):
        return [c() for c in _EDITORES] if self.request.method == "POST" else [AllowAny()]

    def get(self, request):
        editor = _es_editor(request)
        qs = services.listar(request.query_params, editor=editor).prefetch_related("etiquetas")
        try:
            page_size = min(max(int(request.query_params.get("page_size", 12)), 1), 100)
            page = int(request.query_params.get("page", 1))
        except ValueError as exc:
            raise ParseError("page y page_size deben ser enteros") from exc
        paginador = Paginator(qs, page_size)
        try:
            pagina = paginador.page(page)
        except EmptyPage:
            pagina = paginador.page(paginador.num_pages)
        return _ok(
            "blogs",
            {
                "total": paginador.count, "page": pagina.number, "page_size": page_size,
                "total_pages": paginador.num_pages,
                "results": [_resumen(b, editor) for b in pagina.object_list],
            },
        )

    def post(self, request):
        """JSON, o multipart/form-data con `data` (JSON como texto) y `portada` (imagen, opcional)."""
        if "data" in request.data:
            try:
                payload = json.loads(request.data["data"])
            except (TypeError, ValueError) as exc:
                raise ParseError("El campo 'data' debe ser un JSON válido") from exc
        else:
            payload = request.data
        serializer = BlogCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        portada = request.FILES.get("portada")
        if portada:
            services.validar_imagen(portada)
        blog = services.crear(serializer.validated_data, creado_por=request.user)
        if portada:
            services.poner_portada(blog, portada, editado_por=None)
        return _ok("entrada creada", _detalle(_por_id(blog.id), editor=True), status.HTTP_201_CREATED)


class BlogDetailView(APIView):
    """GET público (por id o por slug) — borradores y programadas solo para el equipo editor;
    PUT/DELETE solo editores."""

    authentication_classes = _AUTH

    def get_permissions(self):
        return [c() for c in _EDITORES] if self.request.method in ("PUT", "DELETE") else [AllowAny()]

    def get(self, request, ref):
        blog = _por_ref(ref)
        editor = _es_editor(request)
        if not blog.publicado and not editor:
            raise NotFound("Entrada no encontrada")
        return _ok("entrada", _detalle(blog, editor))

    def put(self, request, ref):
        blog = _por_ref(ref)
        serializer = BlogUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.actualizar(blog, serializer.validated_data, editado_por=request.user)
        return _ok("entrada actualizada", _detalle(_por_id(blog.id), editor=True))

    def delete(self, request, ref):
        services.eliminar(_por_ref(ref))
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST", "DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_EDITORES)
def blog_portada(request, blog_id: int):
    """POST (campo `portada`) pone o reemplaza la imagen de portada; DELETE la quita."""
    blog = _por_id(blog_id)
    if request.method == "DELETE":
        services.quitar_portada(blog, editado_por=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
    upload = request.FILES.get("portada")
    if not upload:
        raise ParseError("Falta la imagen (campo 'portada')")
    services.poner_portada(blog, upload, editado_por=request.user)
    return _ok("portada guardada", _detalle(_por_id(blog_id), editor=True))


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_EDITORES)
def subir_imagen(request):
    """Sube una imagen para insertarla dentro del contenido (Markdown): devuelve su URL."""
    upload = request.FILES.get("imagen")
    if not upload:
        raise ParseError("Falta la imagen (campo 'imagen')")
    ruta = services.guardar_imagen(upload, "contenido", campo="imagen")
    return _ok("imagen subida", {"url": default_storage.url(ruta)}, status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def etiquetas(request):
    """Etiquetas con la cantidad de entradas publicadas: para el filtro y la nube de etiquetas."""
    return _ok("etiquetas", services.etiquetas_publicas())
