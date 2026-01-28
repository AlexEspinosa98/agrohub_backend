from fastapi import APIRouter, Depends, HTTPException, Query, Form, File, UploadFile
from modules.hub_cgsm.application_hub_cgsm.services import EncuestaService
from modules.hub_cgsm.domain_hub_cgsm.entities import SurveyListRequest, Survey, EncuestaActores, EncuestaFaena, EncuestaPuntoAcopio
from modules.hub_cgsm.infrastructure_hub_cgsm.repositories.postgres_repository import PostgresEncuestaRepository
from typing import List, Optional
from datetime import date
from fastapi.responses import JSONResponse
import json
import base64
from pydantic import ValidationError

#####
from modules.hub_cgsm.lib_hub_cgsm.schema import SurveyParametersCreate

router = APIRouter(tags=["HUB CGSM"], prefix="/hub-cgsm")


def get_encuesta_service():
    repository = PostgresEncuestaRepository()
    return EncuestaService(repository)

@router.post("/surveys/")
async def save_surveys(
    survey: SurveyParametersCreate
    ):
    return survey

@router.get("/surveys/", response_model=List[Survey])
async def get_all_surveys(
    page: int = 1,
    page_size: int = 10,
    email: Optional[str] = Query(None),
    survey_type: Optional[str] = Query(None, alias="surveyType"),
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    id: Optional[int] = Query(None),
    service: EncuestaService = Depends(get_encuesta_service)
):
    return service.get_all_surveys(page, page_size, email, survey_type, start_date, end_date, id)

@router.put("/surveys/{id}", response_model=Survey)
async def update_survey(
    id: int,
    survey_data: Survey,
    service: EncuestaService = Depends(get_encuesta_service)
):
    updated_survey = service.update_survey(id, survey_data)
    if not updated_survey:
        raise HTTPException(status_code=404, detail="Survey not found or update failed")
    return updated_survey


@router.post("/survey/actors")
async def save_actor_survey(
    survey_json: str = Form(...),
    service: EncuestaService = Depends(get_encuesta_service),
    fotografia_actor: UploadFile = File(...),
    fotografia_activo: UploadFile = File(...),
):
    try:
        survey = EncuestaActores.model_validate_json(survey_json)
        await service.save_actor_survey(survey, fotografia_actor, fotografia_activo)
        return JSONResponse(content={"message": "Actor survey saved successfully"}, status_code=201)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/survey/faena")
async def save_faena_survey(
    survey_json: str = Form(...),
    service: EncuestaService = Depends(get_encuesta_service),
    fotografia_antes: UploadFile = File(...),
    fotografia_despues: UploadFile = File(...)
):
    try:
        survey = EncuestaFaena.model_validate_json(survey_json)
        await service.save_faena_survey(survey, fotografia_antes, fotografia_despues)
        return JSONResponse(content={"message": "Faena survey saved successfully"}, status_code=201)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/survey/punto-acopio")
async def save_punto_acopio_survey(
    survey_json: str = Form(...),
    service: EncuestaService = Depends(get_encuesta_service),
    fotografia_georreferenciada: UploadFile = File(...)
):
    try:
        survey = EncuestaPuntoAcopio.model_validate_json(survey_json)
        await service.save_punto_acopio_survey(survey, fotografia_georreferenciada)
        return JSONResponse(content={"message": "Punto de Acopio survey saved successfully"}, status_code=201)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))