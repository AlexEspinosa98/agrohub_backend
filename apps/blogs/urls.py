from django.urls import path

from apps.blogs import views

urlpatterns = [
    path("", views.BlogsView.as_view(), name="blogs_list_create"),
    path("etiquetas", views.etiquetas, name="blogs_etiquetas"),
    path("imagenes", views.subir_imagen, name="blogs_imagenes"),
    path("<str:ref>", views.BlogDetailView.as_view(), name="blogs_detail"),
    path("<int:blog_id>/portada", views.blog_portada, name="blogs_portada"),
]
