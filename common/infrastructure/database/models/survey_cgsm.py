from common.infrastructure.database.models.base import BaseModel
from typing import Optional

from sqlalchemy import String, Text, Integer,Date,Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column


path_initial = "survey_cgsm_" # Data Ccgsm

class BaseSurveys(BaseModel):
    date_aplication: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    email_aplicator: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)

class SurveyCgsm(BaseSurveys):
    __tablename__ = path_initial + "survey_cgsm"
    
    ph : Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    salinity : Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    dissolved_oxygen : Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    conductivity : Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    temperature : Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    latitude : Mapped[Optional[str]] = mapped_column(String(50), nullable=False)
    longitude : Mapped[Optional[str]] = mapped_column(String(50), nullable=False)
