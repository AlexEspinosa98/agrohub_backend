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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personas_asistentes"

    def __str__(self):
        return f"{self.nombre} ({self.numero_documento})"


class Evento(models.Model):
    tema = models.CharField(max_length=255)
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
    created_at = models.DateTimeField(auto_now_add=True)

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
