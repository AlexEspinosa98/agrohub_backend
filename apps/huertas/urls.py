"""Rutas bajo /agrohubs/<ref>/… (montadas después de apps.agrohubs.urls). `<ref>` = id o número."""
from django.urls import path

from apps.huertas import views

urlpatterns = [
    path("huertas", views.huertas_todas, name="huertas_todas"),
    path("<str:ref>/huerta", views.agrohub_huerta, name="huertas_huerta"),
    path("<str:ref>/permisos", views.agrohub_permisos, name="huertas_permisos"),
    path("<str:ref>/cuidadores", views.cuidadores, name="huertas_cuidadores"),
    path("<str:ref>/cuidadores/<int:usuario_id>", views.cuidador_quitar, name="huertas_cuidador_quitar"),
    path("<str:ref>/camas", views.camas, name="huertas_camas"),
    path("<str:ref>/camas/<str:zona>", views.cama_config, name="huertas_cama_config"),
    path("<str:ref>/camas/<str:zona>/regar", views.cama_regar, name="huertas_cama_regar"),
    path("<str:ref>/sensores", views.sensores, name="huertas_sensores"),
    path("<str:ref>/plan", views.agrohub_plan, name="huertas_plan"),
    path("<str:ref>/plan/camas/<str:zona>", views.plan_cama, name="huertas_plan_cama"),
    path("<str:ref>/plan/intercambiar", views.plan_intercambiar, name="huertas_plan_intercambiar"),
    path("<str:ref>/plan/reenviar", views.plan_reenviar, name="huertas_plan_reenviar"),
    path("<str:ref>/lecturas", views.agrohub_lecturas, name="huertas_lecturas"),
    path("<str:ref>/reportes", views.agrohub_reportes, name="huertas_reportes"),
    path("<str:ref>/reportes/<int:reporte_id>/moderacion", views.reporte_moderar, name="huertas_reporte_moderar"),
    path("<str:ref>/bitacora", views.agrohub_bitacora, name="huertas_bitacora"),
    path("<str:ref>/movimientos", views.agrohub_movimientos, name="huertas_movimientos"),
    path("<str:ref>/recomendaciones", views.agrohub_recomendaciones, name="huertas_recomendaciones"),
    path("<str:ref>/calibracion/aceptar", views.calibracion_aceptar, name="huertas_calibracion_aceptar"),
    path("<str:ref>/seguimiento", views.agrohub_seguimiento, name="huertas_seguimiento"),
]

cultivos_urlpatterns = [
    path("", views.cultivos, name="huertas_cultivos"),
    path("<slug:cultivo_id>", views.cultivo_detalle, name="huertas_cultivo_detalle"),
    path("<slug:cultivo_id>/cambios", views.cultivo_cambios, name="huertas_cultivo_cambios"),
]
