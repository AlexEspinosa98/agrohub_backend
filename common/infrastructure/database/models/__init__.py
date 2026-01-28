"""
Database infrastructure module.

Import all models here to ensure they are registered with SQLAlchemy.
"""

# Import all models to register them with SQLAlchemy
from .base import Base, BaseModel
from .data_characterization import SurveyAgrohub,SurveyEducational, SurveyFoodRight
from .survey_cgsm import SurveyCgsm


__all__: list[str] = [
    "Base",
    "BaseModel",
    "SurveyAgrohub",
    "SurveyEducational",
    "SurveyFoodRight",
    "SurveyCgsm",
]
