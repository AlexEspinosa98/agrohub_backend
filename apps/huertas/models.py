"""Huertas abiertas: biblioteca de cultivos, plan de siembra por cama, reportes de la comunidad,
seguimiento con modelo de lenguaje y cuidadores por AgroHub (HU_HUERTAS_ABIERTAS.md, HB01–HB08).

Todo vive en la base principal (MySQL). Las lecturas de los sensores NO se copian: se leen de la
base de mqtt_agrohub (apps.riego_iot) al vuelo y se agregan cada 30 minutos (ver lecturas.py)."""
from django.db import models

FAMILIAS = [
    "solanaceas", "cucurbitaceas", "leguminosas", "brasicaceas", "apiaceas", "aliaceas",
    "asteraceas", "lamiaceas", "gramineas", "euforbiaceas", "musaceas", "ninguna",
]
FORMAS = ["mata", "hoja", "enredadera", "rastrera", "alta"]
SIEMBRAS = ["directa", "trasplante", "estaca", "colino"]
TIPOS_ETAPA = ["inicio", "crecimiento", "flor", "fruto", "cosecha"]
LUCES = ["sol", "media sombra"]


class Cultivo(models.Model):
    """Ficha de un cultivo (HU-HB01). Los campos son los de `Cultivo` en biblioteca.ts. `id` es el
    mismo identificador corto del frontend ("tomate", "aji") para que los planes guardados en el
    navegador y los de aquí hablen de lo mismo."""

    id = models.SlugField(max_length=40, primary_key=True)
    nombre = models.CharField(max_length=80)
    familia = models.CharField(max_length=20)
    forma = models.CharField(max_length=20)
    fruto = models.CharField(max_length=20, null=True, blank=True)  # color del fruto (#rrggbb)

    # Agua
    sed = models.FloatField()
    abrir = models.IntegerField()
    cerrar = models.IntegerField()
    kc = models.JSONField()  # [inicio, pleno, final] (FAO-56)
    agotable = models.FloatField()
    raiz = models.JSONField()  # [min, max] en metros
    secar_al_final = models.BooleanField(default=False)

    # Calor
    optimo = models.JSONField()  # [min, max] °C
    calor_fuerte = models.FloatField()

    # Ciclo
    siembra = models.CharField(max_length=20)
    cosecha_dias = models.IntegerField(default=0)
    perenne = models.BooleanField(default=False)

    # Siembra y vecinas
    distancia = models.CharField(max_length=200, blank=True, default="")
    luz = models.CharField(max_length=20, default="sol")
    amigas = models.JSONField(default=list)
    evitar = models.JSONField(default=list)

    # Cuidado
    plagas = models.JSONField(default=list)
    senal = models.TextField(blank=True, default="")
    consejo = models.TextField(blank=True, default="")

    # De dónde sale cada número: {"abrir": "calibración local", "kc": "FAO-56", ...}
    fuentes = models.JSONField(default=dict, blank=True)
    # Los valores de partida son de referencia: hasta que AGROSAVIA / la Mesa Técnica los valide
    # queda en False y el frontend lo puede advertir.
    validado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    editado_por = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        db_column="editado_por_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cultivos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def ficha_dict(self, etapas=None):
        """Forma que usan ciclo.py y la API (snake_case)."""
        if etapas is None:
            etapas = list(self.etapas.all())
        return {
            "id": self.id,
            "nombre": self.nombre,
            "familia": self.familia,
            "forma": self.forma,
            "fruto": self.fruto,
            "sed": self.sed,
            "abrir": self.abrir,
            "cerrar": self.cerrar,
            "kc": self.kc,
            "agotable": self.agotable,
            "raiz": self.raiz,
            "secar_al_final": self.secar_al_final,
            "optimo": self.optimo,
            "calor_fuerte": self.calor_fuerte,
            "siembra": self.siembra,
            "etapas": [{"tipo": e.tipo, "nombre": e.nombre, "desde": e.desde} for e in etapas],
            "cosecha_dias": self.cosecha_dias,
            "perenne": self.perenne,
            "distancia": self.distancia,
            "luz": self.luz,
            "amigas": self.amigas,
            "evitar": self.evitar,
            "plagas": self.plagas,
            "senal": self.senal,
            "consejo": self.consejo,
            "fuentes": self.fuentes,
            "validado": self.validado,
            "updated_at": self.updated_at,
        }


class CultivoEtapa(models.Model):
    cultivo = models.ForeignKey(Cultivo, on_delete=models.CASCADE, related_name="etapas")
    orden = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=60)  # como se dice en ese cultivo: «Echa bejuco»
    desde = models.PositiveIntegerField()  # día desde la siembra

    class Meta:
        db_table = "cultivo_etapas"
        ordering = ["cultivo_id", "orden"]
        unique_together = [("cultivo", "orden")]


class CultivoCambio(models.Model):
    """Quién cambió qué de una ficha (HU-HB01: «registro de quién cambió qué»)."""

    cultivo = models.ForeignKey(Cultivo, on_delete=models.CASCADE, related_name="cambios")
    usuario = models.ForeignKey(
        "user_activity.User", null=True, on_delete=models.SET_NULL, related_name="+", db_column="usuario_id",
    )
    cambios = models.JSONField()  # {"abrir": [30, 32], ...}
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cultivo_cambios"
        ordering = ["-creado_en"]


class Cama(models.Model):
    """Una cama de la huerta = una válvula de riego del gateway con su sensor de tierra (HU-HB02).

    `zona` es el nombre público ("A", "B"…) que se ve en la web. `gateway_zona` + `valvula` dicen
    qué umbral del gateway gobierna esa cama (config/set → zonas.z1.riego.RO1) y `sensor` qué sonda
    de tierra la mide (dev_eui). Esos tres campos solo los ve y edita el equipo técnico."""

    agrohub = models.ForeignKey("agrohubs.AgroHub", on_delete=models.CASCADE, related_name="camas")
    zona = models.CharField(max_length=10)
    orden = models.PositiveSmallIntegerField(default=0)

    gateway_zona = models.CharField(max_length=10, null=True, blank=True)  # "z1"
    valvula = models.CharField(max_length=5, null=True, blank=True)  # "RO1" | "RO2"
    sensor = models.CharField(max_length=32, null=True, blank=True)  # dev_eui de la sonda

    # «referencia»: la creó el sistema con lo que el micrositio dice que se siembra y una sonda
    # del gateway, para que la huerta no salga vacía. Pasa a «equipo» apenas una persona cambia
    # el plan o la configuración: desde ahí es dato confirmado.
    origen = models.CharField(max_length=12, default="equipo")
    cultivo = models.ForeignKey(Cultivo, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    sembrado_el = models.DateField(null=True, blank=True)
    cosechando = models.BooleanField(default=False)
    ajuste = models.SmallIntegerField(default=0)  # calibración en puntos (±6)

    # Último umbral calculado y lo que respondió el gateway al enviarlo.
    umbral_abrir = models.IntegerField(null=True, blank=True)
    umbral_cerrar = models.IntegerField(null=True, blank=True)
    etapa_tipo = models.CharField(max_length=20, null=True, blank=True)
    envio_resultado = models.CharField(max_length=20, null=True, blank=True)  # aplicada|rechazada|sin_respuesta|invalida|error|sin_gateway|desactivado
    envio_rev = models.IntegerField(null=True, blank=True)
    envio_detalle = models.JSONField(default=list, blank=True)
    envio_en = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agrohub_camas"
        ordering = ["agrohub_id", "orden", "zona"]
        unique_together = [("agrohub", "zona")]

    @property
    def conectada(self):
        return bool(self.gateway_zona and self.valvula)


class CamaHistorial(models.Model):
    """Lo que hubo antes en cada cama (para rotar)."""

    cama = models.ForeignKey(Cama, on_delete=models.CASCADE, related_name="historial")
    cultivo = models.ForeignKey(Cultivo, on_delete=models.PROTECT, related_name="+")
    sembrado_el = models.DateField(null=True, blank=True)
    hasta = models.DateField()

    class Meta:
        db_table = "agrohub_cama_historial"
        ordering = ["-hasta", "-id"]


class Movimiento(models.Model):
    """«Lo que ha pasado» en la huerta: cada cambio de plan, cosecha o calibración."""

    TIPOS = ["siembra", "descanso", "cambio", "cosecha", "calibracion", "riego"]

    agrohub = models.ForeignKey("agrohubs.AgroHub", on_delete=models.CASCADE, related_name="movimientos")
    cama = models.ForeignKey(Cama, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    tipo = models.CharField(max_length=20)
    texto = models.CharField(max_length=300)
    datos = models.JSONField(default=dict, blank=True)
    usuario = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_column="usuario_id",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agrohub_movimientos"
        ordering = ["-creado_en", "-id"]


class Reporte(models.Model):
    """Lo que la comunidad ve en la huerta (HU-HB04). Campos de `Reporte` en cuaderno.ts."""

    MATAS = ["bonitas", "regulares", "tristes"]
    TACTO = ["seca", "humeda", "encharcada"]
    PLAGA = ["no", "hojas", "manchas", "bichos"]
    RIEGO_MANO = ["no", "poco", "mucho"]
    COSECHA = ["no", "poco", "bastante"]
    AUTORIA = ["nombre", "rol", "anonimo"]
    MODERACION = ["visible", "pendiente", "oculto"]

    agrohub = models.ForeignKey("agrohubs.AgroHub", on_delete=models.CASCADE, related_name="reportes")
    cama = models.ForeignKey(Cama, null=True, blank=True, on_delete=models.SET_NULL, related_name="reportes")
    matas = models.CharField(max_length=12)
    tierra = models.CharField(max_length=12)
    plaga = models.CharField(max_length=12)
    riego_mano = models.CharField(max_length=12)
    cosecha = models.CharField(max_length=12)
    nota = models.TextField(blank=True, default="")
    foto = models.TextField(null=True, blank=True)  # ruta en el storage de media

    # Cómo se muestra quién reporta (principios CARE): con nombre, con su rol o anónimo.
    autoria = models.CharField(max_length=10, default="rol")
    autor_nombre = models.CharField(max_length=80, blank=True, default="")
    autor_rol = models.CharField(max_length=80, blank=True, default="")
    usuario = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", db_column="usuario_id",
    )

    # Lo que decía el sensor de esa cama al guardar: la base de la calibración (HB08).
    sensor = models.CharField(max_length=12, null=True, blank=True)
    sensor_humedad = models.FloatField(null=True, blank=True)

    moderacion = models.CharField(max_length=10, default="visible")
    # Huella del remitente para limitar abusos; nunca se publica y no guarda la IP en claro.
    origen_hash = models.CharField(max_length=64, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agrohub_reportes"
        ordering = ["-creado_en", "-id"]


class Seguimiento(models.Model):
    """Resumen de la huerta redactado por un modelo de lenguaje (HU-HB06). Se genera solo cuando
    cambió la huella (reportes, bitácora o plan), nunca al abrir la página."""

    agrohub = models.ForeignKey("agrohubs.AgroHub", on_delete=models.CASCADE, related_name="seguimientos")
    huella = models.CharField(max_length=64)
    resumen = models.TextField()
    va_bien = models.JSONField(default=list)
    cuidar = models.JSONField(default=list)
    pasos = models.JSONField(default=list)
    pregunta = models.TextField(blank=True, default="")
    modelo = models.CharField(max_length=60)
    version_prompt = models.CharField(max_length=20)
    tokens_entrada = models.IntegerField(default=0)
    tokens_salida = models.IntegerField(default=0)
    costo_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    reportes = models.IntegerField(default=0)
    notas = models.IntegerField(default=0)
    automatico = models.BooleanField(default=False)
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agrohub_seguimientos"
        ordering = ["-generado_en", "-id"]


class Cuidador(models.Model):
    """Persona que cuida un AgroHub concreto (permiso `huerta.cuidar`, HU-HB07): cambia el plan de
    siembra, riega sus camas y escribe bitácora de ESA huerta, sin acceso al panel técnico."""

    agrohub = models.ForeignKey("agrohubs.AgroHub", on_delete=models.CASCADE, related_name="cuidadores")
    usuario = models.ForeignKey("user_activity.User", on_delete=models.CASCADE, related_name="huertas_que_cuida")
    asignado_por = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        db_column="asignado_por_id",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agrohub_cuidadores"
        unique_together = [("agrohub", "usuario")]
