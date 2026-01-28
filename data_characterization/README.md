# Data Characterization Module

This module is responsible for managing and storing different types of surveys related to agricultural, educational, and human food rights data characterization. It follows a clean architecture pattern, separating domain logic, application services, and infrastructure concerns.

## Architecture

The module is divided into three main layers:

-   **Domain**: Contains the core business logic, including entities and repository interfaces.
-   **Application**: Contains the services that orchestrate the domain logic.
-   **Infrastructure**: Contains the implementation details, such as database interactions and API routes.

## Components

### Domain

-   **`entities.py`**: Defines the data models for the different survey types using Pydantic:
    -   `EncuestaAgrohub`: Survey for agro-hub characterization.
    -   `EncuestaEducativa`: Survey for educational institutions.
    -   `EncuestaDerechoHumanoAlimentario`: Survey related to the human right to food.
    -   `Survey`: A Union type that can represent any of the survey types.
    -   `SurveyListRequest`: A model for receiving a list of surveys associated with an email.

-   **`repositories.py`**: Defines the `EncuestaRepository` abstract base class, which specifies the contract for data persistence operations:
    -   `save_bulk(surveys)`: Saves a list of surveys.
    -   `get_all(...)`: Retrieves a paginated and filtered list of surveys.
    -   `update(id, survey)`: Updates an existing survey.

### Application

-   **`services.py`**: Implements the `EncuestaService` class, which contains the business logic for handling surveys. It depends on the `EncuestaRepository` interface to interact with the data layer.
    -   `save_surveys(request)`: Saves a list of surveys from a `SurveyListRequest`.
    -   `get_all_surveys(...)`: Retrieves all surveys with optional filters.
    -   `update_survey(id, survey_data)`: Updates a specific survey.

### Infrastructure

-   **`repositories/postgres_repository.py`**: Provides a concrete implementation of the `EncuestaRepository` using a PostgreSQL database. It handles the creation of the necessary tables and the implementation of the data access logic.

-   **`routes/data_characterization_routes.py`**: Exposes the survey functionality through a FastAPI `APIRouter`. It defines the following endpoints:

    -   **`POST /surveys/`**: Saves a list of surveys.
        -   **Request Body**: `SurveyListRequest`
        -   **Response**: A confirmation message.

    -   **`GET /surveys/`**: Retrieves a list of surveys with optional query parameters for filtering and pagination.
        -   **Query Parameters**: `page`, `page_size`, `email`, `surveyType`, `startDate`, `endDate`, `id`.
        -   **Response**: A list of `Survey` objects.

    -   **`PUT /surveys/{id}`**: Updates a survey by its ID.
        -   **Path Parameter**: `id` (the ID of the survey to update).
        -   **Request Body**: `Survey`
        -   **Response**: The updated `Survey` object.

## Database Schema

The `PostgresEncuestaRepository` automatically creates and manages three tables in the database:

-   `encuestas_agrohub`
-   `encuestas_educativas`
-   `encuestas_derecho_humano_alimentario`

Each table stores the data for the corresponding survey type. An `email` column is added to each table to associate the survey with a user.

## How to Use

To use this module, you need to include its router in your main FastAPI application. The endpoints can then be accessed as described above.

**Example: Saving a survey**

Send a `POST` request to `/surveys/` with the following body:

```json
{
  "email": "user@example.com",
  "surveys": [
    {
      "type": "agrohub",
      "nombre_aplicador": "John Doe",
      "fecha_aplicacion": "2023-10-27",
      "municipio": "Some Municipality",
      // ... other survey fields
    }
  ]
}
```



Data Characterization Module Documentation


  1. Documentation for Product Manager / Product Owner (PM/PO)

  This document provides a high-level overview of the data_characterization
  module, its purpose, features, and the data it handles, from a product
  perspective.

  1.1. Purpose & Value


  The primary purpose of this module is to capture, store, and manage survey 
  data from various sources. It acts as a centralized system for three distinct
  types of surveys, each aimed at characterizing a different group:


   1. Agro-Hubs: Organizations or associations related to agriculture.
   2. Educational Institutions: Schools and other educational bodies.
   3. Households (Human Right to Food): Families and their access to food.

  This module enables the business to collect structured data, associate it with
  a specific user (via email), and retrieve it for analysis, reporting, or other
  operational purposes.


  1.2. Key Features


   * Save Multiple Surveys: The system can accept and store a batch of different
     surveys for a single user in one transaction.
   * Retrieve Surveys: It provides a powerful query interface to fetch surveys
     based on various filters:
       * User email
       * Survey type (e.g., only "educational" surveys)
       * Date range of submission
       * Unique survey ID
   * Update Surveys: Existing surveys can be updated with new information.
   * Data Association: Every survey submitted is linked to a user's email address,
     allowing for easy tracking and data ownership.

  1.3. Data Models: The Surveys

  The module handles three types of surveys. Below is a summary of the information
  each one collects.

  ##### A. Agro-Hub Survey (EncuestaAgrohub)


   * Goal: To understand the profile, capacity, and needs of agricultural
     organizations.
   * Key Information Collected:
       * General Info: Organization name, location, year founded, number of
         members.
       * Production Profile: Types of agriculture practiced, specific crops (like
         vegetables), and what they do with their produce (e.g., sell, consume).
       * Organizational Maturity: If they are formally registered, have experience
         with projects, and how they access markets.
       * Technology Use: What technologies they use, their internet connectivity,
         and learning capacity.
       * Goals: Their expectations, commitments, and limitations.
       * Location: GPS coordinates (Latitude/Longitude).

  ##### B. Educational Survey (EncuestaEducativa)


   * Goal: To characterize educational institutions, focusing on their
     infrastructure, projects, and connection to agro-environmental topics.
   * Key Information Collected:
       * General Info: Institution name, location, number of students and teachers.
       * Experience & Focus: If they have experience with projects, if they have a
         school garden (huerta), and what it's used for.
       * Infrastructure: If they have space for an "Agro-hub", internet access, and
         laboratories.
       * Community Links: Connections with community actors and existing
         partnerships.
       * Innovation Capacity: If they have research groups (semilleros) and their
         level of interest in agriculture.
       * Goals: Their expectations, commitments, and limitations.
       * Location: GPS coordinates (Latitude/Longitude).

  ##### C. Human Right to Food Survey (EncuestaDerechoHumanoAlimentario)



   * Goal: To assess food security and the understanding of the right to food at
     the household level.
   * Key Information Collected:
       * General Info: Household location, head of household's details, and number
         of family members.
       * Family Agriculture: If the family is involved in agriculture and what they
         produce.
       * Food Availability: If their own production covers their needs, and if they
         experience months of scarcity.
       * Food Accessibility: If they can afford enough food, their access to
         markets, and if they receive food aid.
       * Food Adequacy: If their diet is balanced, if they have access to clean
         water, and if their food is culturally appropriate.
       * Perception & Knowledge: If they are aware of the "right to food" and if
         they feel it is respected.
       * Location: GPS coordinates (Latitude/Longitude).

  1.4. How It Works (User Flow)


   1. A user on a client application (like a mobile or web app) fills out one or
      more surveys.
   2. The client application gathers the survey data and the user's email.
   3. The application sends this data to our system's POST /surveys/ endpoint.
   4. The data_characterization module validates the data, associates it with the
      user's email, and saves it to the appropriate database table.
   5. Later, an administrator or analyst can use another application to request
      this data via the GET /surveys/ endpoint, using filters to get the exact
      information they need.

  ---


  2. Technical Documentation

  This document provides a detailed technical explanation of the
  data_characterization module.

  2.1. Overview & Architecture


  This module is responsible for managing and storing different types of
  surveys. It follows a Clean Architecture pattern, separating concerns into
  three distinct layers: Domain, Application, and Infrastructure. This design
  promotes maintainability, testability, and independence from external
  frameworks.


   * Domain: Contains the core business logic and definitions, including Pydantic
     entity models and abstract repository interfaces. It is the heart of the
     module and has no dependencies on other layers.
   * Application: Orchestrates the domain logic. It contains the application
     services that are called by the API layer to perform business operations.
   * Infrastructure: Contains all the implementation details, such as the database
     repository implementation (PostgreSQL) and the API routes (FastAPI). This
     layer depends on the Application and Domain layers.


  2.2. Components

  ##### 2.2.1. Domain Layer


   * `domain/entities.py`: Defines the data structures using Pydantic BaseModel.
       * EncuestaAgrohub: Model for the agro-hub characterization survey.
       * EncuestaEducativa: Model for the educational institution survey.
       * EncuestaDerechoHumanoAlimentario: Model for the human right to food
         survey.
       * Survey: A Union type representing any of the three concrete survey types,
         enabling polymorphic behavior.
       * SurveyListRequest: A model defining the structure for bulk survey
         submission, containing a user email and a list of surveys.


   * `domain/repositories.py`: Defines the contract for data persistence.
       * EncuestaRepository(ABC): An abstract base class that specifies the
         methods any repository implementation must provide:
           * save_bulk(surveys: List[Survey]): Saves a list of surveys.
           * get_all(...): Retrieves a filtered and paginated list of surveys.
           * update(id: int, survey: Survey): Updates a survey by its ID.

  ##### 2.2.2. Application Layer


   * `application/services.py`: Implements the core business logic.
       * EncuestaService: A class that orchestrates data operations. It is
         initialized with a repository that conforms to the EncuestaRepository
         interface (Dependency Inversion).
           * save_surveys(request): Assigns the request's email to each survey in
             the list and passes them to the repository to be saved.
           * get_all_surveys(...): Forwards the query to the repository to fetch
             all surveys with the specified filters.
           * update_survey(id, survey_data): Calls the repository to update a
             specific survey.

  ##### 2.2.3. Infrastructure Layer


   * `infrastructure/repositories/postgres_repository.py`: Provides the concrete
     implementation for data persistence using PostgreSQL.
       * PostgresEncuestaRepository: Implements the EncuestaRepository interface.
       * Table Creation: On initialization (__init__), it executes CREATE TABLE IF 
         NOT EXISTS statements to ensure the necessary tables (encuestas_agrohub,
         encuestas_educativas, encuestas_derecho_humano_alimentario) exist in the
         database. It also adds an email column to each table if it doesn't already
          exist.
       * `save_bulk(...)`: Iterates through the list of surveys, determines the
         type of each survey (isinstance), and executes the appropriate INSERT
         statement for the corresponding table.
       * `get_all(...)`: Dynamically constructs a SQL query to fetch data. It can
         query a specific table if survey_type is provided or perform a UNION ALL
         across all three tables to fetch combined results. It handles filtering by
         email, date range, and id.
       * `update(...)`: Constructs and executes an UPDATE SQL statement to modify
         an existing record in the correct table based on the survey type.


   * `infrastructure/routes/data_characterization_routes.py`: Exposes the module's
     functionality via a FastAPI APIRouter.
       * Dependency Injection: Uses Depends to inject an EncuestaService instance
         into the route functions, promoting separation of concerns.
       * Endpoints:
           * POST /surveys/:
               * Purpose: Saves a list of surveys for a user.
               * Request Body: SurveyListRequest.
               * Response: 201 Created with a success message.
           * GET /surveys/:
               * Purpose: Retrieves a list of surveys based on query parameters.
               * Query Parameters: page, page_size, email, surveyType, startDate,
                 endDate, id.
               * Response: 200 OK with a list of Survey objects.
           * PUT /surveys/{id}:
               * Purpose: Updates a single survey identified by its ID.
               * Path Parameter: id (the survey's primary key).
               * Request Body: A Survey object.
               * Response: 200 OK with the updated Survey object, or 404 Not Found.

  2.3. Database Schema



  The module automatically manages three tables in the PostgreSQL database. An
  email column is present in all tables to link the survey to a user.


   * `encuestas_agrohub`: Stores data for EncuestaAgrohub.
   * `encuestas_educativas`: Stores data for EncuestaEducativa.
   * `encuestas_derecho_humano_alimentario`: Stores data for
     EncuestaDerechoHumanoAlimentario.


  All tables have an id SERIAL PRIMARY KEY column for unique identification and
  a fecha_creacion TIMESTAMP column that defaults to the current time on record
  creation. The remaining columns directly map to the fields defined in the
  Pydantic models in domain/entities.py.