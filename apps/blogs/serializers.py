from rest_framework import serializers

ESTADOS = ["borrador", "publicado"]


def _etiquetas():
    return serializers.ListField(child=serializers.CharField(max_length=60, allow_blank=False), required=False)


class BlogCreateSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=255)
    resumen = serializers.CharField(max_length=600)
    contenido = serializers.CharField()
    slug = serializers.SlugField(max_length=280, required=False, allow_blank=True)
    autor = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    etiquetas = _etiquetas()
    estado = serializers.ChoiceField(choices=ESTADOS, required=False, default="borrador")
    # Si se publica sin fecha, es "ahora"; con fecha futura queda programada.
    fecha_publicacion = serializers.DateTimeField(required=False, allow_null=True)


class BlogUpdateSerializer(serializers.Serializer):
    """PUT /blogs/<id> — edición parcial. `etiquetas`, si viene, reemplaza la lista completa."""

    titulo = serializers.CharField(max_length=255, required=False)
    resumen = serializers.CharField(max_length=600, required=False)
    contenido = serializers.CharField(required=False)
    slug = serializers.SlugField(max_length=280, required=False)
    autor = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    etiquetas = _etiquetas()
    estado = serializers.ChoiceField(choices=ESTADOS, required=False)
    fecha_publicacion = serializers.DateTimeField(required=False, allow_null=True)
