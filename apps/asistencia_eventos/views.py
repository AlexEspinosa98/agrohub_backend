import io
import json
import uuid

import pandas as pd
from dateutil import parser as dateutil_parser
from django.core.files.storage import default_storage
from django.http import HttpResponse
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.response import Response

from apps.asistencia_eventos import services
from apps.asistencia_eventos.models import Evento, PersonaAsistente, RegistroAsistencia
from apps.asistencia_eventos.ocr_service import extract_asistencia
from apps.asistencia_eventos.serializers import (
    EventoConfirmSerializer,
    EventoHeaderUpdateSerializer,
    PersonaUpdateSerializer,
    RegistroAsistenciaUpdateSerializer,
)
from apps.user_activity.authentication import TokenHeaderAuthentication
from apps.user_activity.permissions import IsAdminRole, IsAuthenticatedWithRole

_AUTH = [TokenHeaderAuthentication]
_ADMIN_ONLY = [IsAuthenticatedWithRole, IsAdminRole]
# Cualquier usuario con rol asignado (no solo admin/superadmin) puede escanear, guardar, ver,
# editar y borrar SUS PROPIOS eventos, y consultar su propio dashboard/estadisticas/excel — todo
# acotado por dueño (ver _eventos_visibles y _usuario_scope: superadmin ve el sistema completo,
# cualquier otro rol solo lo que él mismo registró). Abrir el permiso no cambia el alcance de
# los datos, solo quita la restricción de que además haya que ser admin. Se mantiene _ADMIN_ONLY
# únicamente en persona_detail — es la ficha maestra compartida entre usuarios (una persona
# puede aparecer en eventos de cualquiera), así que editarla/borrarla no tiene un "dueño" al que
# acotar de la misma forma.
_CUALQUIER_ROL = [IsAuthenticatedWithRole]


def _save_scan(upload_file) -> str:
    filename = f"{uuid.uuid4()}_{upload_file.name}"
    return default_storage.save(f"asistencia_eventos/{filename}", upload_file)


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def scan_evento(request):
    """Paso 1: sube el PDF/imagen escaneado, corre OCR y devuelve TODO lo
    extraído (encabezado del evento + asistentes + texto crudo del OCR) para
    que se revise/corrija en el flujo web antes de guardar nada."""
    upload = request.FILES.get("archivo")
    if not upload:
        raise ParseError("Falta el archivo escaneado (campo 'archivo')")

    extracted = extract_asistencia(upload)

    documentos = [a["numero_documento"] for a in extracted["asistentes"] if a.get("numero_documento")]
    existentes = set(
        PersonaAsistente.objects.filter(numero_documento__in=documentos).values_list(
            "numero_documento", flat=True
        )
    )
    for asistente in extracted["asistentes"]:
        asistente["persona_ya_registrada"] = asistente.get("numero_documento") in existentes

    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": "Documento escaneado — revisa y corrige antes de guardar",
            "data": extracted,
        }
    )


def _parse_fecha_ocr(texto):
    """El OCR devuelve la fecha/hora tal como aparecen escritas en la hoja (ej. "28/08/2026",
    "8:30 am") — el flujo normal (/scan → revisión humana → /eventos) confía en que el frontend
    las convierta a los formatos que esperan DateField/TimeField (ISO) al armar el payload de
    confirmación. /scan-bulk no tiene ese paso humano, así que hace esa conversión aquí mismo;
    si el texto no es un formato de fecha/hora reconocible, devuelve None en vez de fallar —
    EventoConfirmSerializer ya acepta fecha/hora_inicio/hora_final en null."""
    if not texto:
        return None
    try:
        return dateutil_parser.parse(texto, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _parse_hora_ocr(texto):
    if not texto:
        return None
    try:
        return dateutil_parser.parse(texto).time()
    except (ValueError, OverflowError):
        return None


@api_view(["POST"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def scan_bulk(request):
    """Sube y GUARDA DIRECTAMENTE varios documentos a la vez — sin el paso de revisión
    humana de /scan + /eventos. Usa tal cual lo que el motor de OCR configurado
    (settings.ASISTENCIA_OCR_ENGINE) haya extraído de cada archivo.

    ADVERTENCIA: sin revisión, cualquier error del OCR queda guardado tal cual — nombres mal
    transcritos, y en particular, si ASISTENCIA_OCR_ENGINE=llm, el campo pertenencia_etnica es
    conocido por no ser confiable (ver docs/asistencia-eventos.md). Usar solo cuando la
    velocidad importa más que la exactitud, aceptando que haya que corregir datos después.

    Cada archivo se procesa y GUARDA de forma independiente, uno a la vez, en el mismo orden
    en que llegó — si el archivo 3 de 10 falla (OCR ilegible, datos inválidos, etc.), los
    archivos 1 y 2 ya quedaron guardados y el 4 en adelante se sigue procesando; el resultado
    por archivo indica cuál se guardó y cuál no. Importante: con el motor LLM cada página tarda
    ~90-180s en el hardware de producción — el timeout de nginx/gunicorn (300s) limita cuántos
    archivos caben con seguridad en un solo request antes de que la conexión se corte. Si eso
    pasa, los archivos ya procesados hasta ese punto quedan guardados igual (se guardan uno a
    uno, no todos al final) — solo que el cliente no ve la respuesta; conviene revisar
    GET /eventos después si un request de este endpoint se corta."""
    archivos = request.FILES.getlist("archivos")
    if not archivos:
        raise ParseError("Falta al menos un archivo (campo 'archivos')")

    resultados = []
    for upload in archivos:
        try:
            extracted = extract_asistencia(upload)
            payload = {
                "tema": extracted.get("tema") or "(sin tema — completar manualmente)",
                "responsable": extracted.get("responsable"),
                "lugar": extracted.get("lugar"),
                "fecha": _parse_fecha_ocr(extracted.get("fecha")),
                "hora_inicio": _parse_hora_ocr(extracted.get("hora_inicio")),
                "hora_final": _parse_hora_ocr(extracted.get("hora_final")),
                "asistentes": extracted.get("asistentes") or [],
            }
            serializer = EventoConfirmSerializer(data=payload)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            documento_path = _save_scan(upload)
            evento = services.guardar_evento(
                data, documento_path, extracted.get("texto_crudo_ocr"), registrado_por=request.user
            )
            resultados.append(
                {
                    "archivo": upload.name,
                    "status": "guardado",
                    "evento_id": evento.id,
                    "total_asistentes": evento.asistentes.count(),
                }
            )
        except Exception as exc:  # noqa: BLE001 — un archivo fallando no debe tumbar el resto del lote
            resultados.append({"archivo": upload.name, "status": "error", "detalle": str(exc)})

    guardados = sum(1 for r in resultados if r["status"] == "guardado")
    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": f"{guardados} de {len(archivos)} documento(s) guardados",
            "data": resultados,
        }
    )


def _crear_evento(request):
    """Paso 2: recibe la información ya depurada (misma forma que el draft
    del scan) junto con el archivo original, y ahí sí guarda todo — sube el
    documento escaneado, hace upsert de cada persona por número de
    documento (garantizando unicidad) y crea el evento + sus registros de
    asistencia.

    Multipart no anida JSON dentro de campos de formulario, así que cuando
    va acompañado del archivo, el payload depurado viaja como un campo
    'data' con el JSON como texto; si se manda sin archivo (application/json
    puro) se acepta el body tal cual."""
    if "data" in request.data:
        try:
            payload = json.loads(request.data["data"])
        except (TypeError, ValueError) as exc:
            raise ParseError("El campo 'data' debe ser un JSON válido") from exc
    else:
        payload = request.data

    serializer = EventoConfirmSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    upload = request.FILES.get("archivo")
    documento_path = _save_scan(upload) if upload else None
    texto_crudo_ocr = payload.get("texto_crudo_ocr") or None

    evento = services.guardar_evento(data, documento_path, texto_crudo_ocr, registrado_por=request.user)
    return Response(
        {
            "status": status.HTTP_201_CREATED,
            "message": "evento guardado",
            "data": {"id": evento.id, "total_asistentes": evento.asistentes.count()},
        },
        status=status.HTTP_201_CREATED,
    )


def _eventos_visibles(request):
    """superadmin ve todos los eventos; cualquier otro rol (admin o user) solo ve los que él
    mismo registró — este filtro es lo que hace seguro abrir scan/eventos a cualquier usuario
    con rol asignado (ver _CUALQUIER_ROL) en vez de restringirlo a admin/superadmin."""
    eventos = Evento.objects.select_related("registrado_por", "editado_por").order_by("-fecha", "-id")
    if request.user.role != "superadmin":
        eventos = eventos.filter(registrado_por=request.user)
    return eventos


def _listar_eventos(request):
    eventos = _eventos_visibles(request)
    data = [
        {
            "id": e.id,
            "tema": e.tema,
            "responsable": e.responsable,
            "lugar": e.lugar,
            "fecha": e.fecha,
            "total_asistentes": e.asistentes.count(),
            "registrado_por": e.registrado_por.name if e.registrado_por else None,
            "editado_por": e.editado_por.name if e.editado_por else None,
        }
        for e in eventos
    ]
    return Response({"status": status.HTTP_200_OK, "message": "eventos", "data": data})


@api_view(["GET", "POST"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def eventos_list_create(request):
    if request.method == "POST":
        return _crear_evento(request)
    return _listar_eventos(request)


def _actualizar_evento(request, evento_id: int):
    """Edición parcial del encabezado del evento — solo se aplican los campos
    que vienen en el body; no toca la lista de asistentes (eso se maneja
    persona por persona en evento_asistente_detail)."""
    evento = _eventos_visibles(request).filter(id=evento_id).first()
    if not evento:
        raise NotFound("Evento no encontrado")

    serializer = EventoHeaderUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    evento = services.actualizar_evento_header(evento, serializer.validated_data, editado_por=request.user)
    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": "evento actualizado",
            "data": {
                "id": evento.id,
                "tema": evento.tema,
                "responsable": evento.responsable,
                "lugar": evento.lugar,
                "fecha": evento.fecha,
                "hora_inicio": evento.hora_inicio,
                "hora_final": evento.hora_final,
            },
        }
    )


def _eliminar_evento(request, evento_id: int):
    evento = _eventos_visibles(request).filter(id=evento_id).first()
    if not evento:
        raise NotFound("Evento no encontrado")
    services.eliminar_evento(evento)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "PUT", "DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_ADMIN_ONLY)
def persona_detail(request, numero_documento: str):
    """Ficha maestra de una persona — GET trae sus datos + eventos donde
    participó, PUT corrige nombre/tipo_documento/genero/pertenencia_etnica
    (edición parcial), DELETE la elimina en cascada con toda su participación
    en eventos. No está acotado por `registrado_por`: una persona puede
    aparecer en eventos de distintos admins, así que su ficha es compartida."""
    persona = PersonaAsistente.objects.filter(numero_documento=numero_documento).first()
    if not persona:
        raise NotFound("Persona no encontrada")

    if request.method == "DELETE":
        services.eliminar_persona(persona)
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "PUT":
        serializer = PersonaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        persona = services.actualizar_persona(persona, serializer.validated_data)

    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": "persona",
            "data": {
                "tipo_documento": persona.tipo_documento,
                "numero_documento": persona.numero_documento,
                "nombre": persona.nombre,
                "genero": persona.genero,
                "pertenencia_etnica": persona.pertenencia_etnica,
                "eventos": services.eventos_de_persona(persona),
            },
        }
    )


@api_view(["PUT", "DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def evento_asistente_detail(request, evento_id: int, numero_documento: str):
    """Corrige o retira la participación de UNA persona en UN evento puntual
    (municipio/telefono/edad de esa asistencia), sin tocar su ficha maestra ni
    el resto del evento. Acotado igual que evento_detail: cualquier rol no-superadmin
    solo sobre eventos que él mismo registró, superadmin sobre cualquiera."""
    evento = _eventos_visibles(request).filter(id=evento_id).first()
    if not evento:
        raise NotFound("Evento no encontrado")

    registro = (
        RegistroAsistencia.objects.select_related("persona")
        .filter(evento=evento, persona__numero_documento=numero_documento)
        .first()
    )
    if not registro:
        raise NotFound("Esa persona no está registrada en este evento")

    if request.method == "DELETE":
        services.eliminar_registro_asistencia(registro)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = RegistroAsistenciaUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    registro = services.actualizar_registro_asistencia(registro, serializer.validated_data)
    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": "asistencia actualizada",
            "data": {
                "evento_id": evento.id,
                "numero_documento": registro.persona.numero_documento,
                "municipio": registro.municipio,
                "telefono": registro.telefono,
                "edad": registro.edad,
            },
        }
    )


def _obtener_evento_detail(request, evento_id: int):
    evento = _eventos_visibles(request).filter(id=evento_id).first()
    if not evento:
        raise NotFound("Evento no encontrado")

    asistentes = [
        {
            "nombre": r.persona.nombre,
            "tipo_documento": r.persona.tipo_documento,
            "numero_documento": r.persona.numero_documento,
            "genero": r.persona.genero,
            "pertenencia_etnica": r.persona.pertenencia_etnica,
            "municipio": r.municipio,
            "telefono": r.telefono,
            "edad": r.edad,
        }
        for r in evento.asistentes.select_related("persona").all()
    ]
    return Response(
        {
            "status": status.HTTP_200_OK,
            "message": "evento",
            "data": {
                "id": evento.id,
                "tema": evento.tema,
                "responsable": evento.responsable,
                "lugar": evento.lugar,
                "fecha": evento.fecha,
                "hora_inicio": evento.hora_inicio,
                "hora_final": evento.hora_final,
                "documento_escaneado": (
                    default_storage.url(evento.documento_escaneado) if evento.documento_escaneado else None
                ),
                "registrado_por": evento.registrado_por.name if evento.registrado_por else None,
                "editado_por": evento.editado_por.name if evento.editado_por else None,
                "actualizado_en": evento.updated_at,
                "asistentes": asistentes,
            },
        }
    )


@api_view(["GET", "PUT", "DELETE"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def evento_detail(request, evento_id: int):
    if request.method == "PUT":
        return _actualizar_evento(request, evento_id)
    if request.method == "DELETE":
        return _eliminar_evento(request, evento_id)
    return _obtener_evento_detail(request, evento_id)


def _usuario_scope(request):
    """None para superadmin (ve todo el sistema); el propio usuario para cualquier otro rol
    (acota a lo que él mismo registró) — mismo criterio que _eventos_visibles."""
    return None if request.user.role == "superadmin" else request.user


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def dashboard_resumen(request):
    data = services.resumen_general(usuario=_usuario_scope(request))
    return Response({"status": status.HTTP_200_OK, "message": "resumen", "data": data})


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def dashboard_estadisticas(request):
    evento_id = request.query_params.get("evento_id")
    data = services.estadisticas_por_municipio(
        evento_id=int(evento_id) if evento_id else None, usuario=_usuario_scope(request)
    )
    return Response({"status": status.HTTP_200_OK, "message": "estadisticas", "data": data})


_HEADER_FILL = PatternFill(start_color="1F6F43", end_color="1F6F43", fill_type="solid")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_BOLD_FONT = Font(bold=True)


def _autosize_columns(worksheet):
    for col_cells in worksheet.columns:
        length = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
        worksheet.column_dimensions[get_column_letter(col_cells[0].column)].width = min(max(length + 2, 10), 45)


def _formatear_libro(workbook):
    for worksheet in workbook.worksheets:
        if worksheet.max_row == 0:
            continue
        for cell in worksheet[1]:
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
        worksheet.freeze_panes = "A2"
        _autosize_columns(worksheet)
        if worksheet.title == "Estadisticas" and worksheet.max_row > 1:
            for cell in worksheet[worksheet.max_row]:
                cell.font = _BOLD_FONT


@api_view(["GET"])
@authentication_classes(_AUTH)
@permission_classes(_CUALQUIER_ROL)
def dashboard_excel(request):
    """Excel completo del dashboard (opcionalmente filtrado por un solo
    evento con ?evento_id=) — 4 hojas: Resumen, Estadisticas (la misma
    tabla Municipio x Género x edad del dashboard), Eventos y el detalle
    completo de Asistentes."""
    evento_id_param = request.query_params.get("evento_id")
    evento_id = int(evento_id_param) if evento_id_param else None
    usuario = _usuario_scope(request)

    resumen = services.resumen_general(usuario=usuario)
    estadisticas = services.estadisticas_por_municipio(evento_id=evento_id, usuario=usuario)
    eventos = services.eventos_para_export(evento_id=evento_id, usuario=usuario)
    asistentes = services.asistentes_para_export(evento_id=evento_id, usuario=usuario)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {"Indicador": "Total personas", "Valor": resumen["total_personas"]},
                {"Indicador": "Total eventos", "Valor": resumen["total_eventos"]},
                {"Indicador": "Total asistencias", "Valor": resumen["total_asistencias"]},
            ]
        ).to_excel(writer, index=False, sheet_name="Resumen")

        columnas_stats = ["municipio", "genero", "0-14", "15-19", "20-59", "mayor de 60", "total"]
        etiquetas_stats = ["Municipio", "Género", "0-14", "15-19", "20-59", "Mayor de 60", "Total"]
        df_stats = pd.DataFrame(estadisticas, columns=columnas_stats)
        df_stats.columns = etiquetas_stats
        df_stats.to_excel(writer, index=False, sheet_name="Estadisticas")

        columnas_eventos = [
            "id",
            "tema",
            "responsable",
            "lugar",
            "fecha",
            "hora_inicio",
            "hora_final",
            "total_asistentes",
            "registrado_por",
            "editado_por",
        ]
        pd.DataFrame(eventos, columns=columnas_eventos).to_excel(writer, index=False, sheet_name="Eventos")

        columnas_asistentes = [
            "evento_id",
            "evento_tema",
            "evento_fecha",
            "nombre",
            "tipo_documento",
            "numero_documento",
            "genero",
            "pertenencia_etnica",
            "municipio",
            "telefono",
            "edad",
        ]
        pd.DataFrame(asistentes, columns=columnas_asistentes).to_excel(
            writer, index=False, sheet_name="Asistentes"
        )

        _formatear_libro(writer.book)

    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = "attachment; filename=dashboard_asistencia_eventos.xlsx"
    return response
