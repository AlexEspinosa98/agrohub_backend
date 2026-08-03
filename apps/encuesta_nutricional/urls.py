from django.urls import path

from apps.encuesta_nutricional import views

urlpatterns = [
    path("personas/<str:value>", views.persona_detail, name="persona_detail"),
    path("dashboard/municipios", views.dashboard_municipios, name="dashboard_municipios"),
    path("dashboard/veredas", views.dashboard_veredas, name="dashboard_veredas"),
    path(
        "dashboard/municipios/<str:municipio>",
        views.dashboard_detalle_municipio,
        name="dashboard_detalle_municipio",
    ),
    path("export/excel", views.export_encuestas_excel, name="export_excel"),
    path("<str:numero_encuesta>/miembros/<int:miembro_id>", views.miembro_detail, name="miembro_detail"),
    path("<str:numero_encuesta>/miembros", views.add_miembro, name="add_miembro"),
    path("<str:numero_encuesta>", views.encuesta_detail, name="encuesta_detail"),
    path("", views.encuestas_list_create, name="encuestas_list_create"),
]
