from django.db import models


class PersonaNutricional(models.Model):
    cedula = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255, null=True, blank=True)
    edad_anios = models.IntegerField(null=True, blank=True)
    sexo = models.CharField(max_length=20, null=True, blank=True)
    area_residencia = models.CharField(max_length=20, null=True, blank=True)
    nivel_educativo = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "personas_nutricionales"


class EncuestaNutricional(models.Model):
    numero_encuesta = models.CharField(max_length=50, unique=True, null=True, blank=True)

    # Encabezado
    nombre_encuestador = models.CharField(max_length=255)
    cedula_encuestador = models.CharField(max_length=50)
    fecha_aplicacion = models.DateField()
    codigo_cuestionario = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=100)
    vereda_comunidad = models.CharField(max_length=255)

    # Sección A — Hogar
    num_personas_hogar = models.IntegerField(null=True, blank=True)
    num_mujeres_hogar = models.IntegerField(null=True, blank=True)
    hay_menores_18 = models.BooleanField(null=True, blank=True)
    num_ninos_menores_5 = models.IntegerField(null=True, blank=True)
    fuente_ingreso_principal = models.CharField(max_length=100, null=True, blank=True)
    tiene_huerta_o_animales = models.BooleanField(null=True, blank=True)
    jefatura_hogar = models.CharField(max_length=50, null=True, blank=True)
    estabilidad_ingreso = models.CharField(max_length=100, null=True, blank=True)

    # Sección C — Hábitos del hogar
    dias_cereales_tuberculos = models.IntegerField(null=True, blank=True)
    dias_leguminosas = models.IntegerField(null=True, blank=True)
    dias_carnes_pescado_huevo = models.IntegerField(null=True, blank=True)
    dias_lacteos = models.IntegerField(null=True, blank=True)
    dias_frutas = models.IntegerField(null=True, blank=True)
    dias_verduras = models.IntegerField(null=True, blank=True)
    dias_grasas = models.IntegerField(null=True, blank=True)
    dias_azucares_ultraprocesados = models.IntegerField(null=True, blank=True)
    puntaje_diversidad_dietetica = models.IntegerField(null=True, blank=True)
    frecuencia_frutas_semana = models.CharField(max_length=30, null=True, blank=True)
    frecuencia_verduras_semana = models.CharField(max_length=30, null=True, blank=True)
    frecuencia_bebidas_azucaradas = models.CharField(max_length=30, null=True, blank=True)
    comidas_por_dia = models.CharField(max_length=20, null=True, blank=True)
    frecuencia_comida_fuera_hogar = models.CharField(max_length=30, null=True, blank=True)
    proporcion_autoconsumo = models.CharField(max_length=30, null=True, blank=True)
    alimentos_preferidos = models.JSONField(null=True, blank=True)

    # Sección D — ELCSA
    preocupacion_alimentos_acabaran = models.BooleanField(null=True, blank=True)
    alimentos_se_acabaron = models.BooleanField(null=True, blank=True)
    adulto_omitio_comida_principal = models.BooleanField(null=True, blank=True)
    sintio_hambre_sin_comer = models.BooleanField(null=True, blank=True)
    puntaje_inseguridad_alimentaria = models.IntegerField(null=True, blank=True)
    clasificacion_seguridad_alimentaria = models.CharField(max_length=60, null=True, blank=True)

    # Cierre
    consentimiento_informado = models.BooleanField()
    observaciones_encuestador = models.TextField(null=True, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "encuestas_nutricionales"


class Miembro(models.Model):
    encuesta = models.ForeignKey(
        EncuestaNutricional,
        on_delete=models.CASCADE,
        db_column="encuesta_id",
        related_name="miembros",
    )
    persona = models.ForeignKey(
        PersonaNutricional,
        on_delete=models.CASCADE,
        db_column="persona_id",
        related_name="miembros",
    )

    # Sección B — Estado nutricional (mediciones de esta encuesta)
    percepcion_estado_nutricional = models.CharField(max_length=20, null=True, blank=True)
    cambio_peso_no_intencional = models.BooleanField(null=True, blank=True)
    nino_en_control_crecimiento = models.CharField(max_length=10, null=True, blank=True)
    peso_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    talla_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    circunferencia_cintura_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    perimetro_brazo_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    grupo_perimetro_brazo = models.CharField(max_length=30, null=True, blank=True)
    imc_calculado = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "encuesta_nutricional_miembros"
