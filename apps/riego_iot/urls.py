from django.urls import path

from apps.riego_iot import views

urlpatterns = [
    path("dispositivos/", views.dispositivos, name="riego_dispositivos"),
    path("dispositivos/<str:device_id>/", views.dispositivo_detalle, name="riego_dispositivo_detalle"),
    path(
        "dispositivos/<str:device_id>/rotar-password/",
        views.rotar_password_dispositivo,
        name="riego_rotar_password",
    ),
    path("dashboard/resumen/", views.dashboard_resumen, name="riego_dashboard_resumen"),
    path("dashboard/<str:device_id>/", views.dashboard_detalle, name="riego_dashboard_detalle"),
    path(
        "dashboard/<str:device_id>/lecturas/ambiente/",
        views.lecturas_ambiente_dispositivo,
        name="riego_lecturas_ambiente",
    ),
    path(
        "dashboard/<str:device_id>/lecturas/suelo/",
        views.lecturas_suelo_dispositivo,
        name="riego_lecturas_suelo",
    ),
]
