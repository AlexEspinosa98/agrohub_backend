from data_characterization.domain.entities import SurveyListRequest, Survey, SurveyLocationInfo
from data_characterization.domain.repositories import EncuestaRepository
from typing import List, Optional
from datetime import date

class EncuestaService:
    def __init__(self, repository: EncuestaRepository):
        self.repository = repository

    def save_surveys(self, request: SurveyListRequest) -> List:
        for survey in request.surveys:
            survey.email = request.email
        return self.repository.save_bulk(request.surveys)

    def get_all_surveys(self, page: int, page_size: int, email: Optional[str] = None, survey_type: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, id: Optional[int] = None) -> List:
        return self.repository.get_all(page, page_size, email, survey_type, start_date, end_date, id)

    def update_survey(self, id: int, survey_data: Survey) -> Optional[Survey]:
        return self.repository.update(id, survey_data)

    def get_all_locations(self) -> List[SurveyLocationInfo]:
        return self.repository.get_all_locations()
