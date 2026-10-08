import uuid

from django.db import models


class PersonaAsistente(models.Model):
    """Registro maestro de una persona por número de documento único —
    mismo patrón que PersonaNutricional en encuesta_nutricional: una persona
    puede aparecer en varios eventos a lo largo del tiempo, pero solo existe
    un registro por número de documento."""

    tipo_documento = models.CharField(max_length=20, null=True, blank=True)
    numero_documento = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    genero = models.CharField(max_length=1, null=True, blank=True)
    pertenencia_etnica = models.CharField(max_length=20, null=True, blank=True)
    # Opcional y solo con sentido si pertenencia_etnica == "indigena": a qué comunidad/pueblo
    # pertenece (ver catalogos.COMUNIDADES_INDIGENAS_SUGERIDAS). Se limpia si la etnia deja de ser
    # indígena. No viene del OCR — se escoge/corrige en la revisión.
    comunidad = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personas_asistentes"

    def __str__(self):
        return f"{self.nombre} ({self.numero_documento})"


class Evento(models.Model):
    tema = models.CharField(max_length=255)
    # Responsable del evento tal como aparece escrito en la hoja física (dato del OCR).
    responsable = models.CharField(max_length=255, null=True, blank=True)
    lugar = models.CharField(max_length=255, null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_final = models.TimeField(null=True, blank=True)
    # Ruta del PDF/imagen original escaneado, guardado tal cual como evidencia.
    documento_escaneado = models.TextField(null=True, blank=True)
    # Texto crudo devuelto por el OCR, para poder revisar manualmente lo que
    # el parser de la tabla no haya logrado interpretar correctamente.
    texto_crudo_ocr = models.TextField(null=True, blank=True)
    # Usuario logueado que digitalizó/guardó el evento (distinto de `responsable`,
    # que es el nombre del responsable del evento leído del papel por el OCR).
    registrado_por = models.ForeignKey(
        "user_activity.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="registrado_por_id",
        related_name="eventos_asistencia_registrados",
    )
    # Usuario logueado que hizo la última edición del evento (PUT /eventos/<id>) — None
    # si nunca se ha editado desde que se registró.
    editado_por = models.ForeignKey(
        "user_activity.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="editado_por_id",
        related_name="eventos_asistencia_editados",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "eventos_asistencia"

    def __str__(self):
        return f"{self.tema} ({self.fecha})"


class RegistroAsistencia(models.Model):
    """Un renglón de la tabla de asistencia de un evento — datos que
    cambian de un evento a otro (municipio, teléfono, edad), a diferencia de
    los datos estables de la persona (nombre, género, etnia) en
    PersonaAsistente."""

    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, db_column="evento_id", related_name="asistentes"
    )
    persona = models.ForeignKey(
        PersonaAsistente, on_delete=models.CASCADE, db_column="persona_id", related_name="asistencias"
    )
    municipio = models.CharField(max_length=100, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registros_asistencia"
        unique_together = [("evento", "persona")]


class ScanJob(models.Model):
    """Escaneo en segundo plano de una hoja (POST /scan-async). Con el motor LLM cada página tarda
    ~2-3 min, así que una hoja de varias páginas no cabe en una petición HTTP (límite de 300 s en
    nginx/gunicorn): el front sube el archivo, recibe este job al instante y consulta su estado
    hasta que termine. El resultado final tiene la misma forma que la respuesta de POST /scan."""

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PROCESANDO = "procesando"
    ESTADO_COMPLETO = "completo"
    ESTADO_ERROR = "error"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PROCESANDO, "Procesando"),
        (ESTADO_COMPLETO, "Completo"),
        (ESTADO_ERROR, "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    archivo = models.TextField()
    nombre_archivo = models.CharField(max_length=255, blank=True)
    paginas_total = models.IntegerField(null=True, blank=True)
    paginas_procesadas = models.IntegerField(default=0)
    # Mientras procesa: lo extraído hasta la última página terminada (mismo formato que el
    # resultado final, para poder ir mostrándolo). Al completar: el borrador final enriquecido.
    resultado = models.JSONField(default=dict, blank=True)
    error_mensaje = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        "user_activity.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="registrado_por_id",
        related_name="scan_jobs_asistencia",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scan_jobs_asistencia"
        ordering = ["-created_at"]
