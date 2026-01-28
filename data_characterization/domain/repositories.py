from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date
from data_characterization.domain.entities import Survey, SurveyLocationInfo

class EncuestaRepository(ABC):
    @abstractmethod
    def save_bulk(self, surveys: List[Survey]) -> List[Survey]:
        pass

    @abstractmethod
    def get_all(self, page: int, page_size: int, email: Optional[str] = None, survey_type: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, id: Optional[int] = None) -> List[Survey]:
        pass

    @abstractmethod
    def update(self, id: int, survey: Survey) -> Optional[Survey]:
        pass

    @abstractmethod
    def get_all_locations(self) -> List[SurveyLocationInfo]:
        pass
