from decimal import Decimal

from rest_framework import serializers

from apps.agrohubs.catalogos import GRUPOS_ETNICOS


def _lista_texto(**kwargs):
    return serializers.ListField(
        child=serializers.CharField(allow_blank=False, max_length=255), **kwargs
    )


def _validar_reglas(attrs, actual=None):
    """Reglas cruzadas. `actual` es el AgroHub existente en una edición parcial, para completar
    lo que no viene en el body."""
    def valor(campo):
        if campo in attrs:
            return attrs[campo]
        return getattr(actual, campo, None) if actual else None

    errores = {}
    if valor("es_cabecera_municipal") is False and not (valor("vereda") or "").strip():
        errores["vereda"] = "La vereda es obligatoria cuando no es cabecera municipal."
    # En una edición parcial, cambiar el grupo a no indígena sin mandar comunidad la limpia (abajo);
    # solo es error si la comunidad viene en el body con un grupo que no es indígena.
    if attrs.get("comunidad") and valor("grupo_etnico") != "indigena":
        errores["comunidad"] = "Solo aplica cuando grupo_etnico es 'indigena'."
    if errores:
        raise serializers.ValidationError(errores)

    if attrs.get("es_cabecera_municipal") is True:
        attrs["vereda"] = None
    if "grupo_etnico" in attrs and attrs["grupo_etnico"] != "indigena":
        attrs["comunidad"] = None
    return attrs


class AgroHubCreateSerializer(serializers.Serializer):
    numero = serializers.CharField(max_length=50)
    familias = _lista_texto(allow_empty=False)
    departamento = serializers.CharField(max_length=100)
    municipio = serializers.CharField(max_length=100)
    es_cabecera_municipal = serializers.BooleanField()
    vereda = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=150)
    asociaciones = _lista_texto(required=False)
    grupo_etnico = serializers.ChoiceField(choices=GRUPOS_ETNICOS, required=False, allow_null=True)
    comunidad = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=100)
    cultivos = _lista_texto(required=False)
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=Decimal("-90"), max_value=Decimal("90"))
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=Decimal("-180"), max_value=Decimal("180"))

    def validate(self, attrs):
        return _validar_reglas(attrs)


class AgroHubUpdateSerializer(serializers.Serializer):
    """PUT /agrohubs/<id> — edición parcial."""

    numero = serializers.CharField(max_length=50, required=False)
    familias = _lista_texto(required=False, allow_empty=False)
    departamento = serializers.CharField(max_length=100, required=False)
    municipio = serializers.CharField(max_length=100, required=False)
    es_cabecera_municipal = serializers.BooleanField(required=False)
    vereda = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=150)
    asociaciones = _lista_texto(required=False)
    grupo_etnico = serializers.ChoiceField(choices=GRUPOS_ETNICOS, required=False, allow_null=True)
    comunidad = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=100)
    cultivos = _lista_texto(required=False)
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=Decimal("-90"), max_value=Decimal("90"), required=False)
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=Decimal("-180"), max_value=Decimal("180"), required=False)

    def validate(self, attrs):
        return _validar_reglas(attrs, actual=self.context.get("agrohub"))
