from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class Association(BaseModel):
    id: Optional[int] = None
    name: str
    latitude: Optional[float] = Field(None, description="Latitud en decimal")
    longitude: Optional[float] = Field(None, description="Longitud en decimal")
    department: Optional[str] = None
    municipality: Optional[str] = None
    vereda: Optional[str] = None
    created_at: Optional[datetime] = None


class User(BaseModel):
    id: Optional[int] = None
    name: str
    phone: str
    identification: str
    email: Optional[EmailStr] = None
    password: str
    association_id: Optional[int] = None
    role: str = Field(default="user", description="Rol del usuario (user/admin)")
    created_at: Optional[datetime] = None

class UserPublic(BaseModel):
    id: int
    name: str
    phone: str
    identification: str
    email: Optional[EmailStr] = None
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

class LogbookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    activity_date: Optional[date] = None
    association_id: Optional[int] = None
