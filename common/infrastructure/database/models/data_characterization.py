from common.infrastructure.database.models.base import BaseModel
from typing import Optional

from sqlalchemy import String, Text, Integer,Date,Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column


path_initial = "dta_charact" # Data Characterization

class BaseSurveys(BaseModel):
    date_aplication: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    email_aplicator: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)

class SurveyAgrohub(BaseSurveys):
    __tablename__ = path_initial + "_survey_agrohub"

    # metadata
    name_aplicator : Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    date_aplication : Mapped[Optional[str]] = mapped_column(Date, nullable=False)
    city : Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    hamlet : Mapped[Optional[str]] = mapped_column(String(100), nullable=False) # hamlet is vereda
    name_organization: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    type_organization: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)

    # 1. Information general
    year_formation: Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    number_of_members: Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    number_of_households: Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    territorial_coverage: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    legal_representative: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    contact_legal_representative: Mapped[Optional[str]] = mapped_column(String(100), nullable=False) # representante legal

    # 2. perfil productive and agroecological
    types_of_agriculture : Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    grow_vegetables: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    wich_vegetables: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    vegetable_area: Mapped[Optional[int]] = mapped_column(Integer, nullable=False)
    vegetable_destination: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    complementary_activities: Mapped[Optional[str]] = mapped_column(String(150), nullable=False)
    has_backyard: Mapped[Optional[str]] = mapped_column(String(100), nullable=False) # tiene patio
    backyard_area: Mapped[Optional[int]] = mapped_column(Integer, nullable=False) # area de patio
    land_conditions: Mapped[Optional[str]] = mapped_column(String(150), nullable=False) # condiciones de la tierra

    # 3. Organizational Maturity
    formalitation: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    associativity: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    project_experience: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    has_statutes_plan: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    market_access: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    sales_frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    administrative_management: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)

    # technological appropiation
    technologies_used: Mapped[Optional[str]] = mapped_column(String(150), nullable=False)
    other_technologies: Mapped[Optional[str]] = mapped_column(String(150), nullable=False)
    learning_capacity: Mapped[Optional[str]] = mapped_column(String(150), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=False)
    connectivity: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)

    # perspective

    expectations: Mapped[Optional[str]] = mapped_column(Text, nullable=False)
    commitments: Mapped[Optional[str]] = mapped_column(Text, nullable=False) # compromisos
    limitations: Mapped[Optional[str]] = mapped_column(Text, nullable=False) # limitaciones

    # geolocation
    latitude: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)
    longitude: Mapped[Optional[str]] = mapped_column(String(100), nullable=False)



class SurveyEducational(BaseSurveys):
    __tablename__ = path_initial + "_educational_survey"

    # Metadata
    surveyor_name: Mapped[str] = mapped_column(String(100))
    application_date: Mapped[str] = mapped_column(Date)
    municipality: Mapped[str] = mapped_column(String(100))
    village: Mapped[str] = mapped_column(String(100))
    institution_name: Mapped[str] = mapped_column(String(150))
    dane_code: Mapped[str] = mapped_column(String(50))
    director_name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(100))

    # General Information
    institution_type: Mapped[str] = mapped_column(String(100))
    branches: Mapped[str] = mapped_column(String(255))
    student_count: Mapped[int] = mapped_column(Integer)
    teacher_count: Mapped[int] = mapped_column(Integer)
    grades_served: Mapped[str] = mapped_column(String(255))
    has_prae: Mapped[bool] = mapped_column(Boolean)
    prae_description: Mapped[str] = mapped_column(String(255))

    # Experience & Focus
    has_project_experience: Mapped[bool] = mapped_column(Boolean)
    project_description: Mapped[str] = mapped_column(String(500))
    has_garden: Mapped[bool] = mapped_column(Boolean)
    garden_area: Mapped[int] = mapped_column(Integer)
    garden_use: Mapped[str] = mapped_column(String(100))
    agro_environmental_topics: Mapped[str] = mapped_column(String(255))

    # Infrastructure
    has_agrohub_space: Mapped[bool] = mapped_column(Boolean)
    agrohub_area: Mapped[int] = mapped_column(Integer)
    land_conditions: Mapped[str] = mapped_column(String(255))
    internet: Mapped[str] = mapped_column(String(50))
    has_complementary_spaces: Mapped[bool] = mapped_column(Boolean)
    complementary_space_count: Mapped[int] = mapped_column(Integer)
    has_lab: Mapped[bool] = mapped_column(Boolean)
    lab_operational: Mapped[bool] = mapped_column(Boolean)

    # Community Involvement
    community_actors: Mapped[str] = mapped_column(String(255))
    has_alliances: Mapped[bool] = mapped_column(Boolean)
    alliance_description: Mapped[str] = mapped_column(String(500))

    # Innovation Capacity
    has_research_groups: Mapped[bool] = mapped_column(Boolean)
    group_name: Mapped[str] = mapped_column(String(150))
    agriculture_interest: Mapped[str] = mapped_column(String(50))
    communication_media: Mapped[str] = mapped_column(String(255))

    # Expectations
    expectations: Mapped[str] = mapped_column(String(500))
    commitments: Mapped[str] = mapped_column(String(500))
    limitations: Mapped[str] = mapped_column(String(500))

    # Final Observations
    comments: Mapped[str] = mapped_column(String(500))
    attached_documents: Mapped[bool] = mapped_column(Boolean)

    # Geolocation
    latitude: Mapped[str] = mapped_column(String(50))
    longitude: Mapped[str] = mapped_column(String(50))


class SurveyFoodRight(BaseSurveys):
    __tablename__ = path_initial + "_food_right_survey"

    # Metadata & General Data
    application_date: Mapped[str] = mapped_column(Date)
    household_head_name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(20))
    department: Mapped[str] = mapped_column(String(100))
    municipality: Mapped[str] = mapped_column(String(100))
    subregion: Mapped[str] = mapped_column(String(100))
    household_members_count: Mapped[int] = mapped_column(Integer)
    education_level: Mapped[str] = mapped_column(String(100))
    surveyor_name: Mapped[str] = mapped_column(String(100))
    surveyor_role: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))

    # Family Farming
    dedicated_to_agriculture: Mapped[bool] = mapped_column(Boolean)
    main_crops: Mapped[str] = mapped_column(String(255))
    production_reason: Mapped[str] = mapped_column(String(255))

    # Food Availability
    covers_needs: Mapped[bool] = mapped_column(Boolean)
    scarcity_months: Mapped[str] = mapped_column(String(255))
    production_change: Mapped[str] = mapped_column(String(50))
    change_reason: Mapped[str] = mapped_column(String(255))
    has_agricultural_inputs: Mapped[bool] = mapped_column(Boolean)
    has_technical_assistance: Mapped[bool] = mapped_column(Boolean)

    # Food Accessibility
    sufficient_food_purchase: Mapped[bool] = mapped_column(Boolean)
    has_market_access: Mapped[bool] = mapped_column(Boolean)
    market_distance: Mapped[str] = mapped_column(String(50))
    affordable_food: Mapped[bool] = mapped_column(Boolean)
    reduced_consumption: Mapped[bool] = mapped_column(Boolean)
    received_food_aid: Mapped[bool] = mapped_column(Boolean)

    # Food Adequacy
    balanced_diet: Mapped[bool] = mapped_column(Boolean)
    food_group_consumption: Mapped[str] = mapped_column(String(255))
    potable_water_for_cooking: Mapped[bool] = mapped_column(Boolean)
    foodborne_diseases: Mapped[bool] = mapped_column(Boolean)
    culturally_acceptable_food: Mapped[bool] = mapped_column(Boolean)
    safe_food_handling: Mapped[bool] = mapped_column(Boolean)

    # Perception & Knowledge
    knows_food_right: Mapped[bool] = mapped_column(Boolean)
    believes_right_respected: Mapped[bool] = mapped_column(Boolean)
    measures_to_improve_access: Mapped[str] = mapped_column(String(255))

    # Geolocation
    latitude: Mapped[str] = mapped_column(String(50))
    longitude: Mapped[str] = mapped_column(String(50))