from modules.hub_cgsm.domain_hub_cgsm.entities import SurveyListRequest, Survey, EncuestaActores
from modules.hub_cgsm.domain_hub_cgsm.repositories import EncuestaRepository
from typing import List, Optional
from datetime import date
from fastapi import UploadFile
import uuid
import os


class EncuestaService:
    def __init__(self, repository: EncuestaRepository):
        self.repository = repository
        self.image_folder = "./images/"

    def save_surveys(self, request: SurveyListRequest) -> List:
        for survey in request.surveys:
            survey.email = request.email
        return self.repository.save_bulk(request.surveys)

    def get_all_surveys(self, page: int, page_size: int, email: Optional[str] = None, survey_type: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, id: Optional[int] = None) -> List:
        return self.repository.get_all(page, page_size, email, survey_type, start_date, end_date, id)

    def update_survey(self, id: int, survey_data: Survey) -> Optional[Survey]:
        return self.repository.update(id, survey_data)

    async def save_actor_survey(self, survey: EncuestaActores, fotografia_actor: UploadFile, fotografia_activo: UploadFile) -> Survey:
        # Process fotografia_actor
        actor_filename = f"{uuid.uuid4()}_{fotografia_actor.filename}"
        actor_path = os.path.join(self.image_folder+"actores/", actor_filename)

        with open(actor_path, "wb") as f:
            f.write(await fotografia_actor.read())

        # Guardar fotografia_activo
        activo_filename = f"{uuid.uuid4()}_{fotografia_activo.filename}"
        activo_path = os.path.join(self.image_folder+"actores/", activo_filename)

        with open(activo_path, "wb") as f:
            f.write(await fotografia_activo.read())

        # Guardar solo la ruta en el survey
        survey.fotografia_actor = actor_path
        survey.fotografia_activo = activo_path

        # Guardar en la base de datos
        return self.repository.save_actor_survey(survey)
    
    async def save_faena_survey(self, survey: Survey, fotografia_antes: List[UploadFile], fotografia_despues: List[UploadFile]) -> Survey:
        # Process fotografia_antes
        filename = f"{uuid.uuid4()}_{fotografia_antes.filename}"
        file_path = os.path.join(self.image_folder+"faenas/", filename)

        with open(file_path, "wb") as f:
            f.write(await fotografia_antes.read())

            # Guardar solo la ruta en el survey
        survey.fotografia_antes = file_path

        # Process fotografia_despues
        filename = f"{uuid.uuid4()}_{fotografia_despues.filename}"
        file_path = os.path.join(self.image_folder+"faenas/", filename)

        with open(file_path, "wb") as f:
            f.write(await fotografia_despues.read())

            # Guardar solo la ruta en el survey
        survey.fotografia_despues = file_path

        # Guardar en la base de datos
        return self.repository.save_faena_survey(survey)
    

    async def save_punto_acopio_survey(self, survey: EncuestaActores, fotografia_georreferenciada: UploadFile) -> Survey:
        # Process fotografia_georreferenciada
        filename = f"{uuid.uuid4()}_{fotografia_georreferenciada.filename}"
        file_path = os.path.join(self.image_folder+"puntos_acopio/", filename)

        with open(file_path, "wb") as f:
            f.write(await fotografia_georreferenciada.read())

            # Guardar solo la ruta en el survey
        survey.fotografia_georreferenciada = file_path

        # Guardar en la base de datos
        return self.repository.save_punto_acopio_survey(survey)