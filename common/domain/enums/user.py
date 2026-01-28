from enum import Enum


class UserStatus(Enum):
    CREATED = "Created"
    ACTIVE = "Active"
    LOCKED = "Locked"
    DELETED = "Deleted"


class UserTypes(Enum):
    SONA_MOM = "Sona Mom"
    SONA_DAD = "Sona Dad"
    GUEST = "Guest"


class UserGenders(Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class UserRoles(Enum):
    ADMIN = "Admin"
    USER = "User"
    SUPERUSER = "Superuser"


class CountryCodes(Enum):
    US = "+1"
    CO = "+57"
