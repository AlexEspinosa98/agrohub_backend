from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from apps.agrohubs.views import agrohubs_list_create
from apps.blogs.views import BlogsView
from apps.cartillas.views import CartillasView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def read_root(request):
    return JsonResponse({"message": "AgroHub API operativa"})


def hello(request):
    return JsonResponse({"message": "Hola mundo"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", read_root),
    path("hello", hello),
    path("", include("apps.data_characterization.urls")),
    path("hub-cgsm/", include("apps.hub_cgsm.urls")),
    path("user-activity/", include("apps.user_activity.urls")),
    path("encuesta-nutricional/", include("apps.encuesta_nutricional.urls")),
    path("asistencia-eventos/", include("apps.asistencia_eventos.urls")),
    # Los listados también responden SIN la barra final (/agrohubs?page=1): un proxy/frontend que la
    # quita recibía un 301 de APPEND_SLASH (sin cuerpo útil, y que además rompe el preflight CORS y los POST).
    path("agrohubs", agrohubs_list_create),
    path("cartillas", CartillasView.as_view()),
    path("blogs", BlogsView.as_view()),
    path("agrohubs/", include("apps.agrohubs.urls")),
    path("cartillas/", include("apps.cartillas.urls")),
    path("blogs/", include("apps.blogs.urls")),
    path("riego-iot/", include("apps.riego_iot.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
