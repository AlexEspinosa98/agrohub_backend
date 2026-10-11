import json

from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, Paginator
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cartillas import services
from apps.cartillas.models import Cartilla
from apps.cartillas.serializers import CartillaCreateSerializer, CartillaUpdateSerializer
from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.permissions import IsAuthenticatedWithRole, IsContenidoEditorRole

_AUTH = [TokenHeaderAuthentication]
# Subir/editar/borrar: admin, superadmin, investigador y comunicaciones. Leer es público.
_EDITORES = [IsAuthenticatedWithRole, IsContenidoEditorRole]


def _ok(message, data, code=status.HTTP_200_OK):
    return Response({"status": code, "message": message, "data": data}, status=code)


def _nombre(usuario):
    return (getattr(usuario, "name", None) or getattr(usuario, "email", None)) if usuario else None


def _resumen(c: Cartilla) -> dict:
    """Lo que ve el listado público (sin índice)."""
    return {
        "id": c.id,
        "tema": c.tema,
        "titulo": c.titulo,
        "resumen": c.resumen,
        "para": c.para,
        "paginas": c.paginas,
        "tamano_bytes": c.tamano_bytes,
        "fecha_publicacion": c.fecha_publicacion,
        "archivo": default_storage.url(c.archivo) if c.archivo else None,
    }


def _detalle(c: Cartilla, editor=False) -> dict:
    data = _resumen(c)
    data["indice"] = [{"titulo": i.titulo, "pagina": i.pagina} for i in c.indice.all()]
    if editor:
        data.update(
            creado_por=_nombre(c.creado_por), creado_por_id=c.creado_por_id,
            editado_por=_nombre(c.editado_por), created_at=c.created_at, updated_at=c.updated_at,
        )
    return data


def _obtener(cartilla_id: int) -> Cartilla:
    cartilla = (
        Cartilla.objects.select_related("creado_por", "editado_por").prefetch_related("indice")
        .filter(id=cartilla_id).first()
    )
    if not cartilla:
        raise NotFound("Cartilla no encontrada")
    return cartilla


def _es_editor(request) -> bool:
    return getattr(request.user, "role", None) in ("admin", "superadmin", "investigador", "comunicaciones")


class CartillasView(APIView):
    """GET (listado + búsqueda) público; POST (subir cartilla) solo editores."""

    authentication_classes = _AUTH

    def get_permissions(self):
        if self.request.method == "POST":
            return [c() for c in _EDITORES]
        return [AllowAny()]

    def get(self, request):
        qs = services.buscar(request.query_params)
        try:
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
            page = int(request.query_params.get("page", 1))
        except ValueError as exc:
            raise ParseError("page y page_size deben ser enteros") from exc
        paginador = Paginator(qs, page_size)
        try:
            pagina = paginador.page(page)
        except EmptyPage:
            pagina = paginador.page(paginador.num_pages)
        return _ok(
            "cartillas",
            {
                "total": paginador.count,
                "page": pagina.number,
                "page_size": page_size,
                "total_pages": paginador.num_pages,
                "results": [_resumen(c) for c in pagina.object_list],
            },
        )

    def post(self, request):
        """multipart/form-data: `data` (JSON como texto) + `archivo` (PDF)."""
        if "data" in request.data:
            try:
                payload = json.loads(request.data["data"])
            except (TypeError, ValueError) as exc:
                raise ParseError("El campo 'data' debe ser un JSON válido") from exc
        else:
            payload = request.data
        upload = request.FILES.get("archivo")
        if not upload:
            raise ParseError("Falta el PDF (campo 'archivo')")
        serializer = CartillaCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        cartilla = services.crear(serializer.validated_data, upload, creado_por=request.user)
        return _ok("cartilla creada", _detalle(_obtener(cartilla.id), editor=True), status.HTTP_201_CREATED)


class CartillaDetailView(APIView):
    """GET público; PUT/DELETE solo editores."""

    authentication_classes = _AUTH

    def get_permissions(self):
        if self.request.method in ("PUT", "DELETE"):
            return [c() for c in _EDITORES]
        return [AllowAny()]

    def get(self, request, cartilla_id):
        return _ok("cartilla", _detalle(_obtener(cartilla_id), editor=_es_editor(request)))

    def put(self, request, cartilla_id):
        cartilla = _obtener(cartilla_id)
        serializer = CartillaUpdateSerializer(data=request.data, context={"cartilla": cartilla})
        serializer.is_valid(raise_exception=True)
        services.actualizar(cartilla, serializer.validated_data, editado_por=request.user)
        return _ok("cartilla actualizada", _detalle(_obtener(cartilla_id), editor=True))

    def delete(self, request, cartilla_id):
        services.eliminar(_obtener(cartilla_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_EDITORES)
def cartilla_archivo(request, cartilla_id: int):
    """Reemplaza el PDF de una cartilla (recalcula páginas y tamaño y borra el anterior)."""
    cartilla = _obtener(cartilla_id)
    upload = request.FILES.get("archivo")
    if not upload:
        raise ParseError("Falta el PDF (campo 'archivo')")
    services.reemplazar_pdf(cartilla, upload, editado_por=request.user)
    return _ok("pdf reemplazado", _detalle(_obtener(cartilla_id), editor=True))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def filtros(request):
    """Temas y públicos ya usados: para los filtros del listado y el autocompletar del formulario."""
    temas = sorted({t for t in Cartilla.objects.values_list("tema", flat=True)}, key=str.lower)
    para = sorted({p for p in Cartilla.objects.exclude(para__isnull=True).exclude(para="").values_list("para", flat=True)}, key=str.lower)
    return _ok("filtros", {"temas": temas, "para": para})
