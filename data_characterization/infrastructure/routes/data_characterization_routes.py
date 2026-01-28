from fastapi import APIRouter, Depends, HTTPException, Query
from data_characterization.application.services import EncuestaService
from data_characterization.domain.entities import SurveyListRequest, Survey, SurveyLocationInfo
from data_characterization.infrastructure.repositories.postgres_repository import PostgresEncuestaRepository
from typing import List, Optional
from datetime import date
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Data Characterization"])

def get_encuesta_service():
    repository = PostgresEncuestaRepository()
    return EncuestaService(repository)

@router.post("/surveys/")
async def save_surveys(
    request: SurveyListRequest,
    service: EncuestaService = Depends(get_encuesta_service)
):
    try:
        service.save_surveys(request)
        return JSONResponse(content={"message": "Surveys saved successfully"}, status_code=201)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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


@router.get("/surveys/locations/", response_model=List[SurveyLocationInfo])
async def get_all_locations(
    service: EncuestaService = Depends(get_encuesta_service)
):
    return service.get_all_locations()
