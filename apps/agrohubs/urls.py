from django.urls import path

from apps.agrohubs import views

urlpatterns = [
    path("", views.agrohubs_list_create, name="agrohubs_list_create"),
    path("puntos", views.puntos, name="agrohubs_puntos"),
    path("catalogos", views.catalogos, name="agrohubs_catalogos"),
    path("<int:agrohub_id>", views.agrohub_detail, name="agrohubs_detail"),
    path("<int:agrohub_id>/video", views.agrohub_video, name="agrohubs_video"),
]
