import re

from rest_framework import serializers

from apps.riego_iot.models import Dispositivo, EnlaceEnergesis

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


class DispositivoEditarSerializer(serializers.Serializer):
    """Solo 'nombre' es editable aquí — device_id/client_id/base_topic identifican la
    credencial MQTT real y cambiarlos requeriría recrearla (ver POST /dispositivos/ y
    rotar-password/), no un simple update de fila."""

    nombre = serializers.CharField(allow_null=True, allow_blank=True)


class ConfigCambioSerializer(serializers.Serializer):
    """PUT /dispositivos/<id>/config/ — cambio PARCIAL: solo lo que venga se modifica. La
    validación fina (0-100, histéresis >= 3, zonas existentes) la hace control_mqtt.validar_config."""

    zonas = serializers.DictField(child=serializers.DictField())


class ComandoValvulaSerializer(serializers.Serializer):
    zona = serializers.CharField()
    valvula = serializers.CharField()
    accion = serializers.CharField()


class EnlaceEnergesisSerializer(serializers.ModelSerializer):
    """Salida: el token nunca sale completo, solo si está configurado y sus últimos 4 caracteres."""

    device_id = serializers.CharField(read_only=True)
    token_configurado = serializers.SerializerMethodField()
    token_ultimos4 = serializers.SerializerMethodField()

    class Meta:
        model = EnlaceEnergesis
        fields = [
            "device_id", "thingsboard_nombre", "activo", "token_configurado", "token_ultimos4",
            "creado_en", "actualizado_en", "ultimo_envio_en", "ultimo_error", "ultimo_error_en",
        ]

    def get_token_configurado(self, obj):
        return bool(obj.thingsboard_token)

    def get_token_ultimos4(self, obj):
        return obj.thingsboard_token[-4:] if obj.thingsboard_token else None


class EnlaceEnergesisEscrituraSerializer(serializers.Serializer):
    """Entrada (PUT/PATCH). `thingsboard_token` es solo de escritura: el "Access token" del
    dispositivo en ThingsBoard (Device -> Manage credentials)."""

    thingsboard_token = serializers.CharField(max_length=128, trim_whitespace=True, required=False, write_only=True)
    thingsboard_nombre = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    activo = serializers.BooleanField(required=False)

    def validate_thingsboard_token(self, value):
        if not value or any(c.isspace() for c in value):
            raise serializers.ValidationError("El token no puede estar vacío ni contener espacios.")
        return value
