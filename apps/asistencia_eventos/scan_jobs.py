"""Escaneo en segundo plano (ScanJob). El hilo vive dentro del proceso de gunicorn que recibió la
petición, igual que los informes de transcripción/análisis de kunsamu: si el servicio se
reinicia a mitad de camino el job queda "procesando" para siempre, por eso `sanear_huerfano` lo
marca como error cuando pasa mucho tiempo sin avanzar."""
import threading
import uuid
from datetime import timedelta

from django.core.files.storage import default_storage
from django.db import close_old_connections
from django.utils import timezone

from apps.asistencia_eventos import parseo, services
from apps.asistencia_eventos.models import ScanJob
from apps.asistencia_eventos.ocr_service import OcrUnavailable, contar_paginas, extract_asistencia

# Cada página tarda ~2-3 min y actualiza `updated_at` al terminar: 15 min sin ningún avance es
# casi seguro un reinicio del servicio, no una página lenta.
UMBRAL_HUERFANO = timedelta(minutes=15)


def crear_job(upload, user, guardar_directo=False) -> ScanJob:
    paginas = contar_paginas(upload)
    ruta = default_storage.save(f"asistencia_eventos/scans/{uuid.uuid4()}_{upload.name}", upload)
    return ScanJob.objects.create(
        archivo=ruta,
        nombre_archivo=upload.name or "",
        paginas_total=paginas,
        registrado_por=user,
        guardar_directo=guardar_directo,
    )


def lanzar(job_id) -> None:
    threading.Thread(target=_procesar, args=(job_id,), daemon=True).start()


def _procesar(job_id) -> None:
    close_old_connections()
    try:
        job = ScanJob.objects.get(pk=job_id)
        job.estado = ScanJob.ESTADO_PROCESANDO
        job.save(update_fields=["estado", "updated_at"])

        def avance(total, hechas, parcial):
            ScanJob.objects.filter(pk=job_id).update(
                paginas_total=total,
                paginas_procesadas=hechas,
                resultado=parcial,
                updated_at=timezone.now(),
            )

        with default_storage.open(job.archivo, "rb") as archivo:
            extracted = extract_asistencia(archivo, on_progress=avance)
        extracted = services.enriquecer_borrador(extracted)

        evento_id = _guardar_directo(job, extracted) if job.guardar_directo else None

        ScanJob.objects.filter(pk=job_id).update(
            evento_id=evento_id,
            estado=ScanJob.ESTADO_COMPLETO,
            paginas_procesadas=job.paginas_total or 0,
            resultado=extracted,
            error_mensaje="",
            completado_en=timezone.now(),
            updated_at=timezone.now(),
        )
    except OcrUnavailable as exc:
        _marcar_error(job_id, str(exc.detail))
    except Exception as exc:  # noqa: BLE001 — cualquier falla queda legible en el job, nunca se pierde en el hilo
        _marcar_error(job_id, f"Error inesperado: {exc}")
    finally:
        close_old_connections()


def _guardar_directo(job: ScanJob, extracted: dict) -> int:
    """/scan-bulk: arma el evento con lo que leyó el OCR (sin revisión humana) y lo guarda,
    enlazando el archivo que ya quedó en disco al subirlo."""
    from apps.asistencia_eventos.serializers import EventoConfirmSerializer

    payload = {
        "tema": extracted.get("tema") or "(sin tema — completar manualmente)",
        "responsable": extracted.get("responsable"),
        "lugar": extracted.get("lugar"),
        "fecha": parseo.parse_fecha_ocr(extracted.get("fecha")),
        "hora_inicio": parseo.parse_hora_ocr(extracted.get("hora_inicio")),
        "hora_final": parseo.parse_hora_ocr(extracted.get("hora_final")),
        "asistentes": extracted.get("asistentes") or [],
    }
    serializer = EventoConfirmSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    evento = services.guardar_evento(
        serializer.validated_data, job.archivo, extracted.get("texto_crudo_ocr"),
        registrado_por=job.registrado_por,
    )
    return evento.id


def _marcar_error(job_id, mensaje) -> None:
    ScanJob.objects.filter(pk=job_id).update(
        estado=ScanJob.ESTADO_ERROR,
        error_mensaje=mensaje,
        completado_en=timezone.now(),
        updated_at=timezone.now(),
    )


def sanear_huerfano(job: ScanJob) -> ScanJob:
    en_curso = job.estado in (ScanJob.ESTADO_PENDIENTE, ScanJob.ESTADO_PROCESANDO)
    if en_curso and job.updated_at < timezone.now() - UMBRAL_HUERFANO:
        _marcar_error(
            job.pk,
            "El escaneo quedó sin avanzar más de 15 minutos (probablemente el servicio se "
            "reinició). Vuelve a subir el archivo.",
        )
        job.refresh_from_db()
    return job
