from django.db import models


class EncuestaAgrohub(models.Model):
    email = models.TextField(null=True, blank=True)
    nombre_aplicador = models.TextField(null=True, blank=True)
    fecha_aplicacion = models.DateField(null=True, blank=True)
    municipio = models.TextField(null=True, blank=True)
    vereda = models.TextField(null=True, blank=True)
    nombre_organizacion = models.TextField(null=True, blank=True)
    tipo_organizacion = models.TextField(null=True, blank=True)

    # 1. Información General
    anio_conformacion = models.IntegerField(null=True, blank=True)
    numero_miembros = models.IntegerField(null=True, blank=True)
    numero_nucleos_familiares = models.IntegerField(null=True, blank=True)
    cobertura_territorial = models.TextField(null=True, blank=True)
    representante_legal = models.TextField(null=True, blank=True)
    contacto = models.TextField(null=True, blank=True)

    # 2. Perfil Productivo y Agroecológico
    tipos_agricultura = models.TextField(null=True, blank=True)
    cultivan_hortalizas = models.TextField(null=True, blank=True)
    cuales_hortalizas = models.TextField(null=True, blank=True)
    area_hortalizas = models.IntegerField(null=True, blank=True)
    destino_hortalizas = models.TextField(null=True, blank=True)
    actividades_complementarias = models.TextField(null=True, blank=True)
    tiene_patio = models.TextField(null=True, blank=True)
    area_patio = models.IntegerField(null=True, blank=True)
    condiciones_terreno = models.TextField(null=True, blank=True)

    # 3. Madurez Organizativa
    formalizacion = models.TextField(null=True, blank=True)
    asociatividad = models.TextField(null=True, blank=True)
    experiencia_proyectos = models.TextField(null=True, blank=True)
    descripcion_experiencia = models.TextField(null=True, blank=True)
    tiene_estatutos_plan = models.TextField(null=True, blank=True)
    acceso_mercado = models.TextField(null=True, blank=True)
    frecuencia_venta = models.TextField(null=True, blank=True)
    manejo_administrativo = models.TextField(null=True, blank=True)

    # 4. Apropiación Tecnológica
    tecnologias_usadas = models.TextField(null=True, blank=True)
    otras_tecnologias = models.TextField(null=True, blank=True)
    capacidad_aprendizaje = models.TextField(null=True, blank=True)
    comentarios = models.TextField(null=True, blank=True)
    conectividad = models.TextField(null=True, blank=True)

    # 5. Perspectivas
    expectativas = models.TextField(null=True, blank=True)
    compromisos = models.TextField(null=True, blank=True)
    limitaciones = models.TextField(null=True, blank=True)

    # 6. Geolocalización
    latitud = models.TextField(null=True, blank=True)
    longitud = models.TextField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encuestas_agrohub"

    SURVEY_TYPE = "agrohub"


class EncuestaEducativa(models.Model):
    email = models.TextField(null=True, blank=True)
    nombre_aplicador = models.TextField(null=True, blank=True)
    fecha_aplicacion = models.DateField(null=True, blank=True)
    municipio = models.TextField(null=True, blank=True)
    vereda = models.TextField(null=True, blank=True)
    nombre_institucion = models.TextField(null=True, blank=True)
    codigo_dane = models.TextField(null=True, blank=True)
    nombre_directivo = models.TextField(null=True, blank=True)
    contacto = models.TextField(null=True, blank=True)

    # 1. Información General
    tipo_institucion = models.TextField(null=True, blank=True)
    sedes = models.TextField(null=True, blank=True)
    numero_estudiantes = models.IntegerField(null=True, blank=True)
    numero_docentes = models.IntegerField(null=True, blank=True)
    grados_atiende = models.TextField(null=True, blank=True)
    tiene_prae = models.BooleanField(null=True, blank=True)
    prae_descripcion = models.TextField(null=True, blank=True)

    # 2. Experiencia y Enfoque
    experiencia_proyectos = models.BooleanField(null=True, blank=True)
    descripcion_proyectos = models.TextField(null=True, blank=True)
    tiene_huerta = models.BooleanField(null=True, blank=True)
    area_huerta = models.IntegerField(null=True, blank=True)
    uso_huerta = models.TextField(null=True, blank=True)
    temas_agroambientales = models.TextField(null=True, blank=True)

    # 3. Infraestructura
    espacio_agrohub = models.BooleanField(null=True, blank=True)
    area_agrohub = models.IntegerField(null=True, blank=True)
    condiciones_terreno = models.TextField(null=True, blank=True)
    internet = models.TextField(null=True, blank=True)
    espacios_complementarios = models.BooleanField(null=True, blank=True)
    cantidad_espacios = models.IntegerField(null=True, blank=True)
    laboratorio = models.BooleanField(null=True, blank=True)
    laboratorio_funciona = models.BooleanField(null=True, blank=True)

    # 4. Vinculación Comunitaria
    actores_comunitarios = models.TextField(null=True, blank=True)
    tiene_alianzas = models.BooleanField(null=True, blank=True)
    descripcion_alianzas = models.TextField(null=True, blank=True)

    # 5. Capacidades de Innovación
    tiene_semilleros = models.BooleanField(null=True, blank=True)
    nombre_grupo = models.TextField(null=True, blank=True)
    interes_agricultura = models.TextField(null=True, blank=True)
    medios_comunicacion = models.TextField(null=True, blank=True)

    # 6. Expectativas
    expectativas = models.TextField(null=True, blank=True)
    compromisos = models.TextField(null=True, blank=True)
    limitaciones = models.TextField(null=True, blank=True)

    # 7. Observaciones Finales
    comentarios = models.TextField(null=True, blank=True)
    anexa_documentos = models.BooleanField(null=True, blank=True)

    # 8. Geolocalización
    latitud = models.TextField(null=True, blank=True)
    longitud = models.TextField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encuestas_educativas"

    SURVEY_TYPE = "educativa"


class EncuestaDerechoHumanoAlimentario(models.Model):
    email = models.TextField(null=True, blank=True)
    fecha_aplicacion = models.DateField(null=True, blank=True)
    nombre_jefe_hogar = models.TextField(null=True, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    genero = models.TextField(null=True, blank=True)
    departamento = models.TextField(null=True, blank=True)
    municipio = models.TextField(null=True, blank=True)
    subregion = models.TextField(null=True, blank=True)
    numero_miembros_hogar = models.IntegerField(null=True, blank=True)
    nivel_educativo = models.TextField(null=True, blank=True)
    nombre_encuestador = models.TextField(null=True, blank=True)
    cargo_encuestador = models.TextField(null=True, blank=True)

    # Agricultura Familiar
    dedicado_agricultura = models.BooleanField(null=True, blank=True)
    cultivos_principales = models.TextField(null=True, blank=True)
    razon_produccion = models.TextField(null=True, blank=True)

    # Disponibilidad de alimentos
    cobertura_necesidades = models.BooleanField(null=True, blank=True)
    meses_escasez = models.TextField(null=True, blank=True)
    cambios_produccion = models.TextField(null=True, blank=True)
    razon_cambios = models.TextField(null=True, blank=True)
    acceso_insumos_agricolas = models.BooleanField(null=True, blank=True)
    asistencia_tecnica = models.BooleanField(null=True, blank=True)

    # Accesibilidad a alimentos
    compra_suficiente_alimentos = models.BooleanField(null=True, blank=True)
    acceso_mercado = models.BooleanField(null=True, blank=True)
    distancia_mercado = models.TextField(null=True, blank=True)
    alimento_asequible = models.BooleanField(null=True, blank=True)
    reduccion_consumo = models.BooleanField(null=True, blank=True)
    ayuda_alimentaria = models.BooleanField(null=True, blank=True)

    # Adecuación de alimentos
    dieta_balanceada = models.BooleanField(null=True, blank=True)
    consumo_grupos_alimenticios = models.TextField(null=True, blank=True)
    agua_potable_preparacion = models.BooleanField(null=True, blank=True)
    enfermedades_transmitidas = models.BooleanField(null=True, blank=True)
    alimentos_culturalmente_aceptables = models.BooleanField(null=True, blank=True)
    higiene_manipulacion = models.BooleanField(null=True, blank=True)

    # Percepción y conocimiento
    conoce_derecho_alimentacion = models.BooleanField(null=True, blank=True)
    cree_derecho_respetado = models.BooleanField(null=True, blank=True)
    medidas_mejorar_acceso = models.TextField(null=True, blank=True)

    # Geolocalización
    latitud = models.TextField(null=True, blank=True)
    longitud = models.TextField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encuestas_derecho_humano_alimentario"

    SURVEY_TYPE = "derecho_humano_alimentario"
