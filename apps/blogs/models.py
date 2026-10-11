from django.db import models
from django.utils import timezone


class Etiqueta(models.Model):
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        db_table = "blog_tags"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Blog(models.Model):
    """Entrada de blog. `contenido` es Markdown (el front lo renderiza y debe sanitizarlo). Pública
    solo si estado = publicado y fecha_publicacion ya llegó (permite programar); borradores y
    programadas solo las ve el equipo editor."""

    ESTADO_BORRADOR = "borrador"
    ESTADO_PUBLICADO = "publicado"

    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    resumen = models.TextField()
    contenido = models.TextField()
    # Ruta relativa en el storage de media de la imagen de portada (opcional).
    portada = models.TextField(null=True, blank=True)
    etiquetas = models.ManyToManyField(Etiqueta, related_name="blogs", blank=True)
    # Nombre que se muestra como autor; por defecto el de quien la crea.
    autor = models.CharField(max_length=150, null=True, blank=True)
    estado = models.CharField(max_length=12, default=ESTADO_BORRADOR, db_index=True)
    fecha_publicacion = models.DateTimeField(null=True, blank=True, db_index=True)
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
        db_table = "blogs"
        ordering = ["-fecha_publicacion", "-id"]

    def __str__(self):
        return self.titulo

    @property
    def publicado(self):
        return (
            self.estado == self.ESTADO_PUBLICADO
            and self.fecha_publicacion is not None
            and self.fecha_publicacion <= timezone.now()
        )
