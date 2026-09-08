"""Modelos NO administrados (managed = False) sobre la base Postgres 'agrohub_mqtt' — las tablas
ya existen y las escribe el daemon de ingesta del repo mqtt_agrohub (proceso Python aparte,
suscrito por MQTT a los gateways, corriendo 24/7 en este mismo servidor), nunca Django. Esta app
solo LEE esas tablas (salvo `Dispositivo`, que si crea/actualiza filas — ver views.py) y nunca
corre migraciones sobre ellas (ver config/db_routers.py: `allow_migrate` devuelve False para
todo lo de esta app). El esquema real está documentado en el repo mqtt_agrohub, `schema.sql`."""
from django.db import models


class Dispositivo(models.Model):
    device_id = models.CharField(max_length=64, primary_key=True, db_column="device_id")
    base_topic = models.CharField(max_length=128, db_column="base_topic")
    client_id = models.CharField(max_length=64, unique=True, null=True, blank=True, db_column="client_id")
    nombre = models.CharField(max_length=255, null=True, blank=True, db_column="nombre")
    activo = models.BooleanField(default=True, db_column="activo")
    primera_vez_visto = models.DateTimeField(db_column="primera_vez_visto")
    ultima_vez_visto = models.DateTimeField(null=True, blank=True, db_column="ultima_vez_visto")
    creado_en = models.DateTimeField(db_column="creado_en")

    class Meta:
        managed = False
        db_table = "dispositivos"

    def __str__(self):
        return self.device_id


class LecturaAmbiente(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="id")
    device_id = models.CharField(max_length=64, db_column="device_id")
    dev_eui = models.CharField(max_length=64, null=True, blank=True, db_column="dev_eui")
    medido_en = models.DateTimeField(db_column="medido_en")
    temperatura = models.FloatField(null=True, blank=True, db_column="temperatura")
    humedad = models.FloatField(null=True, blank=True, db_column="humedad")
    recuperado = models.BooleanField(default=False, db_column="recuperado")
    guardado_en = models.DateTimeField(null=True, blank=True, db_column="guardado_en")
    reenviado_en = models.DateTimeField(null=True, blank=True, db_column="reenviado_en")
    recibido_en = models.DateTimeField(db_column="recibido_en")
    payload_crudo = models.JSONField(db_column="payload_crudo")

    class Meta:
        managed = False
        db_table = "lecturas_ambiente"


class LecturaSuelo(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="id")
    device_id = models.CharField(max_length=64, db_column="device_id")
    dev_eui = models.CharField(max_length=64, null=True, blank=True, db_column="dev_eui")
    medido_en = models.DateTimeField(db_column="medido_en")
    humedad_suelo = models.FloatField(null=True, blank=True, db_column="humedad_suelo")
    temperatura_suelo = models.FloatField(null=True, blank=True, db_column="temperatura_suelo")
    conductividad = models.FloatField(null=True, blank=True, db_column="conductividad")
    recuperado = models.BooleanField(default=False, db_column="recuperado")
    guardado_en = models.DateTimeField(null=True, blank=True, db_column="guardado_en")
    reenviado_en = models.DateTimeField(null=True, blank=True, db_column="reenviado_en")
    recibido_en = models.DateTimeField(db_column="recibido_en")
    payload_crudo = models.JSONField(db_column="payload_crudo")

    class Meta:
        managed = False
        db_table = "lecturas_suelo"


class EstadoValvula(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="id")
    device_id = models.CharField(max_length=64, db_column="device_id")
    medido_en = models.DateTimeField(db_column="medido_en")
    ro1 = models.CharField(max_length=32, null=True, blank=True, db_column="ro1")
    ro2 = models.CharField(max_length=32, null=True, blank=True, db_column="ro2")
    origen = models.CharField(max_length=32, db_column="origen")
    ultimo_comando = models.CharField(max_length=64, null=True, blank=True, db_column="ultimo_comando")
    recibido_en = models.DateTimeField(db_column="recibido_en")
    payload_crudo = models.JSONField(db_column="payload_crudo")

    class Meta:
        managed = False
        db_table = "estados_valvula"


class Healthcheck(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="id")
    device_id = models.CharField(max_length=64, db_column="device_id")
    medido_en = models.DateTimeField(db_column="medido_en")
    mqtt_conectado = models.BooleanField(null=True, blank=True, db_column="mqtt_conectado")
    ultimo_uplink = models.DateTimeField(null=True, blank=True, db_column="ultimo_uplink")
    modo_control = models.CharField(max_length=16, null=True, blank=True, db_column="modo_control")
    override_manual = models.BooleanField(null=True, blank=True, db_column="override_manual")
    valvulas = models.JSONField(null=True, blank=True, db_column="valvulas")
    recibido_en = models.DateTimeField(db_column="recibido_en")
    payload_crudo = models.JSONField(db_column="payload_crudo")

    class Meta:
        managed = False
        db_table = "healthchecks"


class EstadoConexion(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="id")
    device_id = models.CharField(max_length=64, db_column="device_id")
    estado = models.CharField(max_length=16, db_column="estado")
    recibido_en = models.DateTimeField(db_column="recibido_en")

    class Meta:
        managed = False
        db_table = "estados_conexion"
