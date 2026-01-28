from common.domain import entities as common_entities


class SurveyParametersEntity(common_entities.BaseParametersEntity):
    email: str
    ph: int
    salinity: int
    dissolved_oxygen: int
    conductivity: int
    temperature: int
    latitude: str
    longitude: str