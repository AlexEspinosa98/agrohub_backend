import datetime

from rest_framework import serializers


class IndiceItemSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=255)
    pagina = serializers.IntegerField(min_value=1)


def _validar_indice_vs_paginas(indice, paginas):
    if paginas and indice:
        fuera = [i["titulo"] for i in indice if i["pagina"] > paginas]
        if fuera:
            raise serializers.ValidationError(
                {"indice": f"Páginas fuera del PDF (tiene {paginas}): {', '.join(fuera)}"}
            )


class CartillaCreateSerializer(serializers.Serializer):
    tema = serializers.CharField(max_length=150)
    titulo = serializers.CharField(max_length=255)
    resumen = serializers.CharField()
    para = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=100)
    fecha_publicacion = serializers.DateField(required=False)
    # Si no se manda, se cuenta del propio PDF.
    paginas = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    indice = IndiceItemSerializer(many=True, required=False)

    def validate_fecha_publicacion(self, value):
        if value > datetime.date.today() + datetime.timedelta(days=1):
            raise serializers.ValidationError("La fecha de publicación no puede ser futura.")
        return value


class CartillaUpdateSerializer(serializers.Serializer):
    """PUT /cartillas/<id> — edición parcial. `indice`, si viene, reemplaza el índice completo."""

    tema = serializers.CharField(max_length=150, required=False)
    titulo = serializers.CharField(max_length=255, required=False)
    resumen = serializers.CharField(required=False)
    para = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=100)
    fecha_publicacion = serializers.DateField(required=False)
    paginas = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    indice = IndiceItemSerializer(many=True, required=False)

    def validate(self, attrs):
        _validar_indice_vs_paginas(attrs.get("indice"), attrs.get("paginas") or (self.context.get("cartilla") and self.context["cartilla"].paginas))
        return attrs
