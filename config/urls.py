from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


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
]
