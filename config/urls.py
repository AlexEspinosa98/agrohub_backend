from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
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
    path("riego-iot/", include("apps.riego_iot.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
