from abc import abstractmethod

from modules.hub_cgsm.application_hub_cgsm.dtos import (
    input_dto as application_input_dtos,
)
from modules.hub_cgsm.domain_hub_cgsm import entities

from common.domain import repositories as common_repositories


class SurveyRepository(
    common_repositories.BaseRepository[entities.Survey]
):
    """
    Repository interface for survey operations.

    Handles operations related to surveys.
    """

    @abstractmethod
    def find_survey_by_id(self, survey_id: str) -> entities.Survey | None:
        pass

    @abstractmethod
    def create_survey(self, survey_data: application_input_dtos.CreateSurveyInputDTO) -> None:
        pass