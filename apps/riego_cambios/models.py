from django.db import models


class CambioRiego(models.Model):
    """Auditoría de lo que la plataforma le manda a un gateway (configuración y órdenes de válvula):
    quién, cuándo, qué se envió y cómo terminó. Vive en la base default (MySQL), no en la de
    mqtt_agrohub, porque riego_iot está enrutado a esa otra base y no admite migraciones."""

    TIPO_CONFIG = "config"
    TIPO_VALVULA = "valvula"

    device_id = models.CharField(max_length=64, db_index=True)
    tipo = models.CharField(max_length=16)
    usuario = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", db_column="usuario_id",
    )
    rev = models.IntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    # config: aplicada | rechazada | sin_respuesta · valvula: enviada | sin_eco
    resultado = models.CharField(max_length=20)
    errores = models.JSONField(default=list, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "riego_cambios"
        ordering = ["-id"]
