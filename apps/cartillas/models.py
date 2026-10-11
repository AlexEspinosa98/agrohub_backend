from django.db import models
from django.utils import timezone


class Cartilla(models.Model):
    """Cartilla educativa en PDF (ej. "Lo que aprendimos del mercado de nuestras hortalizas"),
    con su índice de páginas. La lectura es pública; subir/editar/borrar es de admin, superadmin,
    investigador y comunicaciones."""

    tema = models.CharField(max_length=150, db_index=True)
    titulo = models.CharField(max_length=255)
    resumen = models.TextField()
    # A quién va dirigida (ej. "Productor").
    para = models.CharField(max_length=100, null=True, blank=True)
    paginas = models.PositiveIntegerField(null=True, blank=True)
    # Ruta relativa en el storage de media y su tamaño (se calculan al subir el PDF).
    archivo = models.TextField()
    tamano_bytes = models.BigIntegerField(default=0)
    fecha_publicacion = models.DateField(default=timezone.localdate, db_index=True)
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
        db_table = "cartillas"
        ordering = ["-fecha_publicacion", "-id"]

    def __str__(self):
        return self.titulo


class CartillaIndice(models.Model):
    """Una entrada del índice: título de la sección y página del PDF donde empieza."""

    cartilla = models.ForeignKey(Cartilla, on_delete=models.CASCADE, related_name="indice")
    titulo = models.CharField(max_length=255)
    pagina = models.PositiveIntegerField()
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "cartillas_indice"
        ordering = ["orden", "pagina", "id"]
