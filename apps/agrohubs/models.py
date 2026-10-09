from django.db import models


class AgroHub(models.Model):
    """Ficha de un AgroHub para el geovisor. Las listas (familias, asociaciones, cultivos) son
    listas de texto libre guardadas como JSON: no hay catálogo ni integrantes por familia."""

    numero = models.CharField(max_length=50, unique=True)
    familias = models.JSONField(default=list)
    departamento = models.CharField(max_length=100)
    municipio = models.CharField(max_length=100)
    es_cabecera_municipal = models.BooleanField()
    # Solo se llena cuando NO es cabecera municipal.
    vereda = models.CharField(max_length=150, null=True, blank=True)
    asociaciones = models.JSONField(default=list)
    grupo_etnico = models.CharField(max_length=20, null=True, blank=True)
    # Solo con grupo_etnico == "indigena" (mismo catálogo que asistencia_eventos).
    comunidad = models.CharField(max_length=100, null=True, blank=True)
    cultivos = models.JSONField(default=list)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    # Ruta relativa en el storage de media; un solo video por AgroHub.
    video = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", db_column="creado_por_id",
    )
    editado_por = models.ForeignKey(
        "user_activity.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", db_column="editado_por_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agrohubs"
        ordering = ["numero"]

    def __str__(self):
        return self.numero
