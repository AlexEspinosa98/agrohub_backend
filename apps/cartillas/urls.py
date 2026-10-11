from django.urls import path

from apps.cartillas import views

urlpatterns = [
    path("", views.CartillasView.as_view(), name="cartillas_list_create"),
    path("filtros", views.filtros, name="cartillas_filtros"),
    path("<int:cartilla_id>", views.CartillaDetailView.as_view(), name="cartillas_detail"),
    path("<int:cartilla_id>/archivo", views.cartilla_archivo, name="cartillas_archivo"),
]
