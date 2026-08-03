from django.urls import path

from apps.hub_cgsm import views

urlpatterns = [
    path("surveys/<int:id>", views.update_survey, name="hub_update_survey"),
    path("surveys/", views.surveys_list_create, name="hub_surveys"),
    path("survey/actors", views.save_actor_survey, name="hub_save_actor"),
    path("survey/faena", views.save_faena_survey, name="hub_save_faena"),
    path("survey/punto-acopio", views.save_punto_acopio_survey, name="hub_save_punto_acopio"),
]
