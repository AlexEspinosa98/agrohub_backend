from rest_framework import serializers

# El frontend a veces manda el género como palabra completa ("Femenino"/"Masculino"/"Otro", en
# vez del código corto que se guarda realmente — ver PersonaAsistente.genero, CharField(max_length=1)
# y el reporte de estadísticas, que ya distingue Masculino/Femenino/Otro). En vez de rechazar esas
# variantes con un 422, GeneroField las normaliza al código antes de validar contra los choices.
_GENERO_ALIASES = {
    "femenino": "F", "mujer": "F", "f": "F",
    "masculino": "M", "hombre": "M", "m": "M",
    "otro": "O", "otra": "O", "o": "O",
}


class GeneroField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        kwargs.setdefault("choices", ["F", "M", "O"])
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            normalizado = _GENERO_ALIASES.get(data.strip().lower())
            if normalizado:
                data = normalizado
        return super().to_internal_value(data)


class AsistenteDataSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tipo_documento = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    numero_documento = serializers.CharField()
    municipio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    edad = serializers.IntegerField(required=False, allow_null=True)
    genero = GeneroField(required=False, allow_null=True)
    pertenencia_etnica = serializers.ChoiceField(
        choices=["ninguno", "indigena", "afro", "rom", "raizal"],
        required=False,
        allow_null=True,
    )


class EventoConfirmSerializer(serializers.Serializer):
    tema = serializers.CharField()
    responsable = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lugar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    fecha = serializers.DateField(required=False, allow_null=True)
    hora_inicio = serializers.TimeField(required=False, allow_null=True)
    hora_final = serializers.TimeField(required=False, allow_null=True)
    asistentes = AsistenteDataSerializer(many=True)

    def validate_asistentes(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos un asistente")
        documentos = [a["numero_documento"] for a in value]
        duplicados = {d for d in documentos if documentos.count(d) > 1}
        if duplicados:
            raise serializers.ValidationError(
                f"Documentos repetidos en la misma carga: {', '.join(sorted(duplicados))}"
            )
        return value


class EventoHeaderUpdateSerializer(serializers.Serializer):
    """PUT /eventos/<id> — edición parcial: solo se aplican los campos que vienen en el body."""

    tema = serializers.CharField(required=False)
    responsable = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lugar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    fecha = serializers.DateField(required=False, allow_null=True)
    hora_inicio = serializers.TimeField(required=False, allow_null=True)
    hora_final = serializers.TimeField(required=False, allow_null=True)


class PersonaUpdateSerializer(serializers.Serializer):
    """PUT /personas/<numero_documento> — edición parcial de la ficha maestra."""

    tipo_documento = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nombre = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    genero = GeneroField(required=False, allow_null=True)
    pertenencia_etnica = serializers.ChoiceField(
        choices=["ninguno", "indigena", "afro", "rom", "raizal"],
        required=False,
        allow_null=True,
    )


class RegistroAsistenciaUpdateSerializer(serializers.Serializer):
    """PUT /eventos/<evento_id>/asistentes/<numero_documento> — edición parcial
    de la participación de una persona en un evento puntual."""

    municipio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    edad = serializers.IntegerField(required=False, allow_null=True)
