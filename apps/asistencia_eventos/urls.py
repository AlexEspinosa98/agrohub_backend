from django.urls import path

from apps.asistencia_eventos import views

urlpatterns = [
    path("scan", views.scan_evento, name="asistencia_scan"),
    path("scan-async", views.scan_async, name="asistencia_scan_async"),
    path("scan-async/<uuid:job_id>", views.scan_async_detail, name="asistencia_scan_async_detail"),
    path("scan-bulk", views.scan_bulk, name="asistencia_scan_bulk"),
    path("eventos", views.eventos_list_create, name="asistencia_eventos_list_create"),
    path("eventos/<int:evento_id>", views.evento_detail, name="asistencia_evento_detail"),
    path("eventos/<int:evento_id>/asistentes", views.evento_asistentes_agregar, name="asistencia_evento_asistentes_agregar"),
    path("eventos/<int:evento_id>/documento", views.evento_documento, name="asistencia_evento_documento"),
    path(
        "eventos/<int:evento_id>/asistentes/<str:numero_documento>",
        views.evento_asistente_detail,
        name="asistencia_evento_asistente_detail",
    ),
    path("comunidades", views.comunidades_indigenas, name="asistencia_comunidades"),
    path("personas/<str:numero_documento>", views.persona_detail, name="asistencia_persona_detail"),
    path("dashboard/resumen", views.dashboard_resumen, name="asistencia_dashboard_resumen"),
    path("dashboard/estadisticas", views.dashboard_estadisticas, name="asistencia_dashboard_estadisticas"),
    path("dashboard/excel", views.dashboard_excel, name="asistencia_dashboard_excel"),
    path("admin/meta", views.admin_meta, name="asistencia_admin_meta"),
    path("admin/reporte/excel", views.admin_reporte_excel, name="asistencia_admin_reporte_excel"),
    path("admin/usuarios", views.admin_usuarios, name="asistencia_admin_usuarios"),
    path("admin/usuarios/<int:user_id>/eventos", views.admin_usuario_eventos, name="asistencia_admin_usuario_eventos"),
    path("admin/municipios", views.admin_municipios, name="asistencia_admin_municipios"),
    path("admin/municipios/corregir", views.admin_municipios_corregir, name="asistencia_admin_municipios_corregir"),
]
