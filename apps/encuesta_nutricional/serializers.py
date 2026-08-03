from rest_framework import serializers


def _positive(value, field_name):
    if value is not None and value <= 0:
        raise serializers.ValidationError(f"{field_name} debe ser mayor que 0")
    return value


class MiembroCreateSerializer(serializers.Serializer):
    cedula_participante = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nombre_participante = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    edad_anios = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=120)
    sexo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    area_residencia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nivel_educativo = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    percepcion_estado_nutricional = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cambio_peso_no_intencional = serializers.BooleanField(required=False, allow_null=True)
    nino_en_control_crecimiento = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    peso_kg = serializers.FloatField(required=False, allow_null=True)
    talla_cm = serializers.FloatField(required=False, allow_null=True)
    circunferencia_cintura_cm = serializers.FloatField(required=False, allow_null=True)
    perimetro_brazo_cm = serializers.FloatField(required=False, allow_null=True)
    grupo_perimetro_brazo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    imc_calculado = serializers.FloatField(required=False, allow_null=True)

    def validate_peso_kg(self, value):
        return _positive(value, "peso_kg")

    def validate_talla_cm(self, value):
        return _positive(value, "talla_cm")

    def validate_circunferencia_cintura_cm(self, value):
        return _positive(value, "circunferencia_cintura_cm")

    def validate_perimetro_brazo_cm(self, value):
        return _positive(value, "perimetro_brazo_cm")


class MiembroUpdateSerializer(MiembroCreateSerializer):
    pass


class PersonaNutricionalUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    edad_anios = serializers.IntegerField(required=False, allow_null=True)
    sexo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    area_residencia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nivel_educativo = serializers.CharField(required=False, allow_null=True, allow_blank=True)


_DIAS_KWARGS = dict(required=False, allow_null=True, min_value=0, max_value=7)


class EncuestaNutricionalCreateSerializer(serializers.Serializer):
    nombre_encuestador = serializers.CharField()
    cedula_encuestador = serializers.CharField()
    fecha_aplicacion = serializers.DateField()
    codigo_cuestionario = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    municipio = serializers.CharField()
    vereda_comunidad = serializers.CharField()

    num_personas_hogar = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    num_mujeres_hogar = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    hay_menores_18 = serializers.BooleanField(required=False, allow_null=True)
    num_ninos_menores_5 = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    fuente_ingreso_principal = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tiene_huerta_o_animales = serializers.BooleanField(required=False, allow_null=True)
    jefatura_hogar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    estabilidad_ingreso = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    dias_cereales_tuberculos = serializers.IntegerField(**_DIAS_KWARGS)
    dias_leguminosas = serializers.IntegerField(**_DIAS_KWARGS)
    dias_carnes_pescado_huevo = serializers.IntegerField(**_DIAS_KWARGS)
    dias_lacteos = serializers.IntegerField(**_DIAS_KWARGS)
    dias_frutas = serializers.IntegerField(**_DIAS_KWARGS)
    dias_verduras = serializers.IntegerField(**_DIAS_KWARGS)
    dias_grasas = serializers.IntegerField(**_DIAS_KWARGS)
    dias_azucares_ultraprocesados = serializers.IntegerField(**_DIAS_KWARGS)
    puntaje_diversidad_dietetica = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=8
    )
    frecuencia_frutas_semana = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    frecuencia_verduras_semana = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    frecuencia_bebidas_azucaradas = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    comidas_por_dia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    frecuencia_comida_fuera_hogar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    proporcion_autoconsumo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    alimentos_preferidos = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True, max_length=5
    )

    preocupacion_alimentos_acabaran = serializers.BooleanField(required=False, allow_null=True)
    alimentos_se_acabaron = serializers.BooleanField(required=False, allow_null=True)
    adulto_omitio_comida_principal = serializers.BooleanField(required=False, allow_null=True)
    sintio_hambre_sin_comer = serializers.BooleanField(required=False, allow_null=True)
    puntaje_inseguridad_alimentaria = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=4
    )
    clasificacion_seguridad_alimentaria = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    consentimiento_informado = serializers.BooleanField()
    observaciones_encuestador = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    miembros = MiembroCreateSerializer(many=True, allow_empty=False)


class EncuestaNutricionalUpdateSerializer(serializers.Serializer):
    nombre_encuestador = serializers.CharField(required=False)
    cedula_encuestador = serializers.CharField(required=False)
    fecha_aplicacion = serializers.DateField(required=False)
    codigo_cuestionario = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    municipio = serializers.CharField(required=False)
    vereda_comunidad = serializers.CharField(required=False)
    num_personas_hogar = serializers.IntegerField(required=False, allow_null=True)
    num_mujeres_hogar = serializers.IntegerField(required=False, allow_null=True)
    hay_menores_18 = serializers.BooleanField(required=False, allow_null=True)
    num_ninos_menores_5 = serializers.IntegerField(required=False, allow_null=True)
    fuente_ingreso_principal = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tiene_huerta_o_animales = serializers.BooleanField(required=False, allow_null=True)
    jefatura_hogar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    estabilidad_ingreso = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dias_cereales_tuberculos = serializers.IntegerField(required=False, allow_null=True)
    dias_leguminosas = serializers.IntegerField(required=False, allow_null=True)
    dias_carnes_pescado_huevo = serializers.IntegerField(required=False, allow_null=True)
    dias_lacteos = serializers.IntegerField(required=False, allow_null=True)
    dias_frutas = serializers.IntegerField(required=False, allow_null=True)
    dias_verduras = serializers.IntegerField(required=False, allow_null=True)
    dias_grasas = serializers.IntegerField(required=False, allow_null=True)
    dias_azucares_ultraprocesados = serializers.IntegerField(required=False, allow_null=True)
    puntaje_diversidad_dietetica = serializers.IntegerField(required=False, allow_null=True)
    frecuencia_frutas_semana = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    frecuencia_verduras_semana = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    frecuencia_bebidas_azucaradas = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    comidas_por_dia = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    frecuencia_comida_fuera_hogar = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    proporcion_autoconsumo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    alimentos_preferidos = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    preocupacion_alimentos_acabaran = serializers.BooleanField(required=False, allow_null=True)
    alimentos_se_acabaron = serializers.BooleanField(required=False, allow_null=True)
    adulto_omitio_comida_principal = serializers.BooleanField(required=False, allow_null=True)
    sintio_hambre_sin_comer = serializers.BooleanField(required=False, allow_null=True)
    puntaje_inseguridad_alimentaria = serializers.IntegerField(required=False, allow_null=True)
    clasificacion_seguridad_alimentaria = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    consentimiento_informado = serializers.BooleanField(required=False, allow_null=True)
    observaciones_encuestador = serializers.CharField(required=False, allow_null=True, allow_blank=True)
