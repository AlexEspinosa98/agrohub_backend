from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class AssociationListItem(BaseModel):
    id: int
    name: str
    municipality: Optional[str] = Field(None, description="Municipio (ciudad) de la asociación")


class AssociationCreate(BaseModel):
    name: str
    latitude: Optional[float] = Field(None, description="Latitud en decimal")
    longitude: Optional[float] = Field(None, description="Longitud en decimal")
    department: Optional[str] = None
    municipality: Optional[str] = None
    vereda: Optional[str] = None


class Association(BaseModel):
    id: Optional[int] = None
    name: str
    latitude: Optional[float] = Field(None, description="Latitud en decimal")
    longitude: Optional[float] = Field(None, description="Longitud en decimal")
    department: Optional[str] = None
    municipality: Optional[str] = None
    vereda: Optional[str] = None
    created_at: Optional[datetime] = None


class AssociationUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    department: Optional[str] = None
    municipality: Optional[str] = None
    vereda: Optional[str] = None


class User(BaseModel):
    id: Optional[int] = None
    name: str
    phone: str
    identification: str
    email: Optional[str] = None
    password: str
    association_id: Optional[int] = None
    role: str = Field(default="user", description="Rol del usuario (user/admin)")
    created_at: Optional[datetime] = None


class UserRegister(BaseModel):
    name: str
    phone: str
    identification: str
    email: Optional[str] = None
    password: str
    association_id: int = Field(..., description="ID de la asociación a la que se vincula el usuario")
    class Config:
        schema_extra = {
            "example": {
                "name": "Laura Méndez",
                "phone": "3001234567",
                "identification": "1020304050",
                "email": "laura@example.com",
                "password": "contraseña_segura",
                "association_id": 1,
            }
        }


class AdminUserCreate(BaseModel):
    name: str
    phone: str
    identification: str
    email: Optional[str] = None
    password: str
    association_id: Optional[int] = Field(None, description="Asociación a la que se vincula el usuario")
    role: str = Field(default="user", description="Rol a asignar (user/admin)")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    identification: Optional[str] = None
    email: Optional[str] = None
    association_id: Optional[int] = None
    role: Optional[str] = None
class UserPublic(BaseModel):
    id: int
    name: str
    phone: str
    identification: str
    email: Optional[str] = None
    association_id: Optional[int] = None
    role: str
    created_at: Optional[datetime] = None

class UserLogin(BaseModel):
    phone_or_identification: str
    password: str

class Logbook(BaseModel):
    id: Optional[int] = None
    user_id: int
    association_id: Optional[int] = None
    title: str
    description: str
    activity_date: date
    created_at: Optional[datetime] = None

class LogbookCreate(BaseModel):
    title: str
    description: str
    activity_date: date

class LogbookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    activity_date: Optional[date] = None
    association_id: Optional[int] = None
