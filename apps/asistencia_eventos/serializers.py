from rest_framework import serializers


class AsistenteDataSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tipo_documento = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    numero_documento = serializers.CharField()
    municipio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    telefono = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    edad = serializers.IntegerField(required=False, allow_null=True)
    genero = serializers.ChoiceField(choices=["F", "M", "O"], required=False, allow_null=True)
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
