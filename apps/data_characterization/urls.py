from django.urls import path

from apps.data_characterization import views

urlpatterns = [
    path("surveys/locations/", views.get_all_locations, name="dc_locations"),
    path("surveys/<int:id>", views.update_survey, name="dc_update_survey"),
    path("surveys/", views.surveys_list_create, name="dc_surveys"),
]
