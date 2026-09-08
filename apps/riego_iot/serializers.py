import re

from rest_framework import serializers

from apps.riego_iot.models import Dispositivo

DEVICE_ID_RE = re.compile(r"^[a-z0-9_-]{3,40}$")
CLIENT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{3,60}$")


class DispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = [
            "device_id", "base_topic", "client_id", "nombre", "activo",
            "primera_vez_visto", "ultima_vez_visto",
        ]


class DispositivoCrearSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    client_id = serializers.CharField()
    nombre = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_device_id(self, value):
        if not DEVICE_ID_RE.match(value):
            raise serializers.ValidationError(
                "device_id inválido — solo minúsculas, números, '-' y '_', 3 a 40 caracteres "
                "(convención del manual UG56: 'device0001', 'device0002', ...)."
            )
        return value

    def validate_client_id(self, value):
        if not CLIENT_ID_RE.match(value):
            raise serializers.ValidationError("client_id inválido — 3 a 60 caracteres alfanuméricos, '-' o '_'.")
        return value
