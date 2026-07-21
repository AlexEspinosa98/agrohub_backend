import logging
import os
import tempfile
import io
from datetime import date
from functools import lru_cache
from typing import Dict, Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, StreamingResponse

from data_characterization.application.services import EncuestaService
from data_characterization.domain.entities import (
    EncuestaAgrohub,
    EncuestaDerechoHumanoAlimentario,
    EncuestaEducativa,
)
from data_characterization.infrastructure.repositories.postgres_repository import (
    PostgresEncuestaRepository,
)
from data_characterization.infrastructure.routes.data_characterization_routes import (
    router as data_characterization_router,
)
from modules.hub_cgsm.infrastructure_hub_cgsm.routes.hub_cgsm_routes import (
    router as hub_cgsm_router,
)
from modules.encuesta_nutricional.infrastructure.routes.encuesta_nutricional_routes import (
    router as encuesta_nutricional_router,
)
from modules.user_activity.infrastructure.routes.user_routes import (
    router as user_activity_router,
)

load_dotenv()

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny")
ENABLE_TRANSCRIBE = os.getenv("ENABLE_TRANSCRIBE", "false").lower() == "true"

app = FastAPI(
    title="AgroHub Magdalena API",
    description=(
        "API para transcripción de audio y sincronización de datos de familias rurales.\n\n"
        "**Módulos disponibles:**\n"
        "- **Data Characterization**: encuestas AgroHub, educativa y de derecho humano alimentario.\n"
        "- **Hub CGSM**: actores, faenas, puntos de acopio y monitoreos ambientales.\n"
        "- **User Activity**: registro (sin rol hasta asignación por superadmin), login, gestión de roles y bitácoras con token.\n"
        "- **Encuesta Nutricional SAN**: encuestas de seguridad alimentaria y nutricional por hogar. "
        "Cada encuesta registra datos del hogar (secciones A, C y D/ELCSA) y los datos individuales "
        "de cada miembro (sección B — mediciones antropométricas) vinculados a una tabla maestra de "
        "participantes (`personas_nutricionales`) mediante FK. "
        "Un mismo participante puede aparecer en múltiples encuestas a lo largo del tiempo."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Devuelve los errores de validación en un formato claro, siempre en JSON,
    indicando el campo exacto, el valor recibido y (si aplica) a qué miembro del
    hogar corresponde, para que se pueda revisar y corregir el dato puntual."""
    body = exc.body if isinstance(exc.body, dict) else {}
    errores = []
    for err in exc.errors():
        loc = [p for p in err["loc"] if p != "body"]
        campo = ".".join(str(p) for p in loc)

        contexto = {}
        # Si el error viene de un miembro del hogar (ej. loc = ("miembros", 1, "edad_anios")),
        # agregamos su cédula/nombre para identificarlo sin tener que contar el índice.
        if len(loc) >= 2 and loc[0] == "miembros" and isinstance(loc[1], int):
            miembro = (body.get("miembros") or [{}])[loc[1]] if body.get("miembros") else {}
            if isinstance(miembro, dict):
                contexto = {
                    "miembro_index": loc[1],
                    "miembro_cedula": miembro.get("cedula_participante"),
                    "miembro_nombre": miembro.get("nombre_participante"),
                }

        errores.append(
            {
                "campo": campo,
                "mensaje": err["msg"],
                "tipo_error": err["type"],
                "valor_recibido": err.get("input"),
                **contexto,
            }
        )

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "status": 422,
                "message": "Datos inválidos en la solicitud",
                "total_errores": len(errores),
                "errores": errores,
            }
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Red de seguridad: cualquier error no controlado debe responder en JSON, nunca texto plano."""
    logger.error("Error no controlado en %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": 500, "message": "Error interno del servidor. Intente nuevamente."},
    )


@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Carga diferida del modelo Whisper para minimizar el tiempo de cold start en Vercel.
    Usa el modelo tiny por defecto (configurable con WHISPER_MODEL).
    """
    if not ENABLE_TRANSCRIBE:
        raise HTTPException(status_code=503, detail="Transcripción deshabilitada")
    try:
        import whisper  # pylint: disable=import-error
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=503, detail="Whisper no está instalado en este despliegue"
        ) from exc

    return whisper.load_model(WHISPER_MODEL_NAME)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    print(f" Request to {request.url} | Body: {body.decode('utf-8', errors='ignore')}")
    response = await call_next(request)
    return response


app.include_router(data_characterization_router)
app.include_router(hub_cgsm_router)
app.include_router(user_activity_router)
app.include_router(encuesta_nutricional_router)


@app.get("/")
async def read_root():
    return {"message": "AgroHub API operativa en Vercel"}


@app.get("/hello")
async def hello():
    return {"message": "Hola mundo"}


@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Endpoint para transcribir audio usando Whisper.
    Acepta archivos de audio en formatos: mp3, wav, m4a, ogg, etc.
    """

    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser de audio")

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        model = get_whisper_model()
        result = model.transcribe(temp_file_path, language="es")

        return {
            "text": result["text"],
            "language": result["language"],
            "filename": file.filename,
        }

    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Error al procesar el audio: {e}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.post("/transcribe-srt/")
async def transcribe_audio_srt(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Endpoint para transcribir audio y generar subtítulos en formato SRT.
    Acepta archivos de audio en formatos: mp3, wav, m4a, ogg, etc.
    """

    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser de audio")

    temp_file_path = None
    temp_dir = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[1]
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        model = get_whisper_model()
        result = model.transcribe(temp_file_path, language="es")

        from whisper.utils import get_writer

        temp_dir = tempfile.mkdtemp()
        writer = get_writer("srt", temp_dir)
        writer(result, os.path.splitext(os.path.basename(temp_file_path))[0])

        srt_filename = os.path.splitext(os.path.basename(temp_file_path))[0] + ".srt"
        srt_path = os.path.join(temp_dir, srt_filename)

        with open(srt_path, "r", encoding="utf-8") as srt_file:
            srt_content = srt_file.read()

        return {
            "srt_content": srt_content,
            "text": result["text"],
            "language": result["language"],
            "filename": file.filename,
        }

    except Exception as e:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Error al procesar el audio: {e}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if temp_dir and os.path.exists(temp_dir):
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


def get_encuesta_service():
    repository = PostgresEncuestaRepository()
    return EncuestaService(repository)


@app.get("/export/surveys/excel")
async def export_surveys_excel(
    email: Optional[str] = None,
    survey_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    service: EncuestaService = Depends(get_encuesta_service),
):
    surveys = service.get_all_surveys(
        page=1,
        page_size=500,
        email=email,
        survey_type=survey_type,
        start_date=start_date,
        end_date=end_date,
    )

    if not surveys:
        return {"message": "No surveys found to export."}

    df = pd.DataFrame([dict(s) for s in surveys])

    modelos_por_tipo = {
        "agrohub": EncuestaAgrohub,
        "educativa": EncuestaEducativa,
        "derecho_humano_alimentario": EncuestaDerechoHumanoAlimentario,
    }

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if "type" in df.columns:
            for tipo, group in df.groupby("type"):
                modelo = modelos_por_tipo.get(tipo)
                if not modelo:
                    continue

                columnas = list(modelo.model_fields.keys())
                group_df = group[columnas]
                group_df.to_excel(writer, index=False, sheet_name=str(tipo)[:31])
        else:
            columnas = list(EncuestaAgrohub.model_fields.keys())
            df[columnas].to_excel(writer, index=False, sheet_name="Surveys")

        if writer.sheets:
            writer.book.active = 0

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=surveys.xlsx"},
    )
