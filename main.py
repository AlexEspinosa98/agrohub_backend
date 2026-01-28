import os
import tempfile
import io
from datetime import date
from functools import lru_cache
from typing import Dict, Optional

import pandas as pd
import whisper
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import StreamingResponse

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

load_dotenv()

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny")

app = FastAPI(
    title="AgroHub Magdalena API",
    description="API para transcripción de audio y sincronización de datos de familias rurales",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Carga diferida del modelo Whisper para minimizar el tiempo de cold start en Vercel.
    Usa el modelo tiny por defecto (configurable con WHISPER_MODEL).
    """
    return whisper.load_model(WHISPER_MODEL_NAME)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    print(f" Request to {request.url} | Body: {body.decode('utf-8', errors='ignore')}")
    response = await call_next(request)
    return response


app.include_router(data_characterization_router)
app.include_router(hub_cgsm_router)


@app.get("/")
async def read_root():
    return {"message": "AgroHub API operativa en Vercel"}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
