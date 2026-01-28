"""
This module contains the schemas for ultrasound API.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic.functional_validators import model_validator




class SurveyParametersCreate(BaseModel):
    email: str = Field(..., example="user@example.com")
    date_aplication: date = Field(..., example="2023-10-01")
    ph: int = Field(..., example=7)
    salinity: int = Field(..., example=35)
    dissolved_oxygen: int = Field(..., example=8)
    conductivity: int = Field(..., example=500)
    temperature: int = Field(..., example=22)
    latitude: str = Field(..., example="-34.6037")
    longitude: str = Field(..., example="-58.3816")
