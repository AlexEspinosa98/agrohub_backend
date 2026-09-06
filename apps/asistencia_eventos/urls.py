from django.urls import path

from apps.asistencia_eventos import views

urlpatterns = [
    path("scan", views.scan_evento, name="asistencia_scan"),
    path("eventos", views.eventos_list_create, name="asistencia_eventos_list_create"),
    path("eventos/<int:evento_id>", views.evento_detail, name="asistencia_evento_detail"),
    path("dashboard/resumen", views.dashboard_resumen, name="asistencia_dashboard_resumen"),
    path("dashboard/estadisticas", views.dashboard_estadisticas, name="asistencia_dashboard_estadisticas"),
    path("dashboard/excel", views.dashboard_excel, name="asistencia_dashboard_excel"),
]
