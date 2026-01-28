from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import whisper
import tempfile
import os
import io
import pandas as pd
import base64
from typing import Dict, Optional
from elevenlabs.client import ElevenLabs
from elevenlabs import text_to_speech, voices
import requests
from datetime import date

from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai

# Family sync service imports

# Data characterization imports
from data_characterization.infrastructure.routes.data_characterization_routes import router as data_characterization_router
from data_characterization.domain.entities import EncuestaAgrohub, EncuestaEducativa, EncuestaDerechoHumanoAlimentario

# Game imports
from data_characterization.application.services import EncuestaService
from data_characterization.infrastructure.repositories.postgres_repository import PostgresEncuestaRepository

# Mamobot imports

# surveys Hub_cgsm
from modules.hub_cgsm.infrastructure_hub_cgsm.routes.hub_cgsm_routes import router as hub_cgsm_router
from modules.hub_cgsm.application_hub_cgsm.services import EncuestaService as EncuestaService_2
from modules.hub_cgsm.infrastructure_hub_cgsm.repositories.postgres_repository import PostgresEncuestaRepository as PostgresEncuestaRepository_2
from modules.hub_cgsm.domain_hub_cgsm.entities import Survey, SurveyListRequest

# Happiness routes

##


app = FastAPI(
    title="AgroHub Magdalena API", 
    description="API para transcripción de audio, síntesis de voz y sincronización de datos de familias rurales",
    version="1.0.0"
)

# Configurar CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


conversation_repository_2 = PostgresEncuestaRepository()
encuesta_service = EncuestaService_2(conversation_repository_2)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    print(f" Request to {request.url} | Body: {body.decode('utf-8', errors='ignore')}")
    response = await call_next(request)
    return response

# Configurar cliente de ElevenLabs
ELEVENLABS_API_KEY = "sk_934d06839a97b8c68cf9d2c1d90e1aa30830009751190cc2"
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Cargar el modelo de Whisper al iniciar la aplicación
print("Cargando modelo Whisper...")
model = whisper.load_model("base")
print("Modelo Whisper cargado exitosamente!")


# Include family routes

app.include_router(data_characterization_router)

app.include_router(hub_cgsm_router)


@app.get("/")
async def read_root():
    return {"message": "¡Hola, FastAPI con Whisper y ElevenLabs en tu Mac!"}


@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(..., max_upload_size=104857600)) -> Dict[str, str]:
    """
    Endpoint para transcribir audio usando Whisper
    Acepta archivos de audio en formatos: mp3, wav, m4a, ogg, etc.
    """
    
    # Verificar que el archivo sea de audio
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser de audio")
    
    try:
        # Crear un archivo temporal para guardar el audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            # Leer y escribir el contenido del archivo
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Transcribir el audio con Whisper (español por defecto)
        result = model.transcribe(temp_file_path, language='es')
        
        # Limpiar el archivo temporal
        os.unlink(temp_file_path)
        
        return {
            "text": result["text"],
            "language": result["language"],
            "filename": file.filename
        }
        
    except Exception as e:
        # Limpiar el archivo temporal en caso de error
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Error al procesar el audio: {str(e)}")

@app.post("/transcribe-srt/")
async def transcribe_audio_srt(file: UploadFile = File(..., max_upload_size=104857600)) -> Dict[str, str]:
    """
    Endpoint para transcribir audio y generar subtítulos en formato SRT
    Acepta archivos de audio en formatos: mp3, wav, m4a, ogg, etc.
    """
    
    # Verificar que el archivo sea de audio
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="El archivo debe ser de audio")
    
    try:
        # Crear un archivo temporal para guardar el audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            # Leer y escribir el contenido del archivo
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Transcribir el audio con Whisper (español por defecto)
        result = model.transcribe(temp_file_path, language='es')
        
        # Generar archivo SRT usando whisper.utils
        from whisper.utils import get_writer
        
        # Crear directorio temporal para el output
        temp_dir = tempfile.mkdtemp()
        
        # Generar archivo SRT
        writer = get_writer('srt', temp_dir)
        writer(result, os.path.splitext(os.path.basename(temp_file_path))[0])
        
        # Leer el contenido SRT generado
        srt_filename = os.path.splitext(os.path.basename(temp_file_path))[0] + '.srt'
        srt_path = os.path.join(temp_dir, srt_filename)
        
        with open(srt_path, 'r', encoding='utf-8') as srt_file:
            srt_content = srt_file.read()
        
        # Limpiar archivos temporales
        os.unlink(temp_file_path)
        os.unlink(srt_path)
        os.rmdir(temp_dir)
        
        return {
            "srt_content": srt_content,
            "text": result["text"],
            "language": result["language"],
            "filename": file.filename
        }
        
    except Exception as e:
        # Limpiar archivos temporales en caso de error
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        if 'temp_dir' in locals():
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Error al procesar el audio: {str(e)}")

# Modelo para recibir texto con opciones de voz
class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: Optional[str] = "21m00Tcm4TlvDq8ikWAM"  # Rachel (voz femenina por defecto)
    model: Optional[str] = "eleven_multilingual_v2"
    stability: Optional[float] = 0.5
    similarity_boost: Optional[float] = 0.8
    style: Optional[float] = 0.0



class ResponseModel(BaseModel):
    response: str = Field(..., description="Respuesta generada por el modelo")
    general: bool = Field(False, description="True si la respuesta es general como saludos o despedida, False si es específica de RAG sobre temas de aluna ia, inteligencia artificial, temas relacionados con la universidad o cultura indígena de la Sierra Nevada de Santa Marta")
    question_user: str = Field(..., description="Pregunta del usuario que se está respondiendo")

def prompt_introduction(text: str) -> str:
    """
    Genera un prompt de introducción para el modelo de generación de texto.
    """
    prompt = f''' Eres Bunachi Rector, rector de la Universidad del Magdalena y líder de ALUNA IA. Sabio académico con expertise en inteligencia artificial y profundo conocimiento de la cultura indígena de la Sierra Nevada de Santa Marta. Tu origen costeño te da una perspectiva única y cálida.

    IMPORTANTE: Si en el texto aparece "la luna", entiende que se refiere a "ALUNA" (error común de transcripción).

    La persona te ha dicho:

    "{text}"

    reglas:
    - Debes determinar en una primera instancia si la persona te está saludando o despidiendo, o si te está haciendo una pregunta específica.
    - Si es un saludo o despedida, responde de manera general y cálida con la key general en True.
    - Si es una pregunta específica sobre aluna ia o alguna pregunta sobre Aluna ia o relacionados con universidad, utiliza la información de RAG para responder con la key general en False.

    RESPONDE DIRECTAMENTE como Bunachi Rector en primera persona. No analices el texto, sino responde como si estuvieras hablando con esa persona. Sé cálido, sabio y mantén la formalidad de un rector. Máximo 3-5 líneas.'''
    return prompt

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)



def get_encuesta_service():
    repository = PostgresEncuestaRepository()
    return EncuestaService(repository)


@app.get("/export/surveys/excel")
async def export_surveys_excel(
    email: Optional[str] = None,
    survey_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    service: EncuestaService = Depends(get_encuesta_service)
):
    surveys = service.get_all_surveys(
        page=1,
        page_size=500,
        email=email,
        survey_type=survey_type,
        start_date=start_date,
        end_date=end_date
    )

    if not surveys:
        return {"message": "No surveys found to export."}

    df = pd.DataFrame([dict(s) for s in surveys])

    # Mapeo de survey_type -> modelo Pydantic
    modelos_por_tipo = {
        "agrohub": EncuestaAgrohub,
        "educativa": EncuestaEducativa,
        "derecho_humano_alimentario": EncuestaDerechoHumanoAlimentario
    }

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if "type" in df.columns:
            for tipo, group in df.groupby("type"):
                modelo = modelos_por_tipo.get(tipo)
                if not modelo:
                    continue

                columnas = list(modelo.model_fields.keys())
                group_df = group[columnas]  # solo las columnas de ese modelo
                group_df.to_excel(writer, index=False, sheet_name=str(tipo)[:31])
        else:
            # si no hay type, usa el default (por ejemplo agrohub)
            columnas = list(EncuestaAgrohub.model_fields.keys())
            df[columnas].to_excel(writer, index=False, sheet_name="Surveys")

        if writer.sheets:
            writer.book.active = 0

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=surveys.xlsx"}
    )


class BotConversationRequest(BaseModel):
    session_id: str
    message: str


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
