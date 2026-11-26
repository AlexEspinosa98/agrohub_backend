import re

from rest_framework import serializers

from apps.huertas.models import FAMILIAS, FORMAS, LUCES, SIEMBRAS, TIPOS_ETAPA, Reporte

_ZONA_GATEWAY = re.compile(r"^z\d+$")


class EtapaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TIPOS_ETAPA)
    nombre = serializers.CharField(max_length=60)
    desde = serializers.IntegerField(min_value=0)


def _par(minimo=None, maximo=None):
    return serializers.ListField(child=serializers.FloatField(min_value=minimo, max_value=maximo), min_length=2, max_length=2)


class CultivoSerializer(serializers.Serializer):
    """Ficha completa para crear un cultivo. En PUT/PATCH todos los campos son opcionales."""

    id = serializers.SlugField(max_length=40)
    nombre = serializers.CharField(max_length=80)
    familia = serializers.ChoiceField(choices=FAMILIAS)
    forma = serializers.ChoiceField(choices=FORMAS)
    fruto = serializers.RegexField(r"^#[0-9a-fA-F]{6}$", allow_null=True, required=False)
    sed = serializers.FloatField(min_value=0.1, max_value=3)
    abrir = serializers.IntegerField(min_value=0, max_value=97)
    cerrar = serializers.IntegerField(min_value=3, max_value=100)
    kc = serializers.ListField(child=serializers.FloatField(min_value=0, max_value=2), min_length=3, max_length=3)
    agotable = serializers.FloatField(min_value=0, max_value=1)
    raiz = _par(0, 5)
    secar_al_final = serializers.BooleanField(default=False)
    optimo = _par(0, 50)
    calor_fuerte = serializers.FloatField(min_value=0, max_value=60)
    siembra = serializers.ChoiceField(choices=SIEMBRAS)
    etapas = EtapaSerializer(many=True, min_length=1)
    cosecha_dias = serializers.IntegerField(min_value=0, max_value=3650, default=0)
    perenne = serializers.BooleanField(default=False)
    distancia = serializers.CharField(max_length=200, allow_blank=True, default="")
    luz = serializers.ChoiceField(choices=LUCES, default="sol")
    amigas = serializers.ListField(child=serializers.SlugField(), default=list)
    evitar = serializers.ListField(child=serializers.SlugField(), default=list)
    plagas = serializers.ListField(child=serializers.CharField(max_length=80), default=list)
    senal = serializers.CharField(allow_blank=True, default="")
    consejo = serializers.CharField(allow_blank=True, default="")
    fuentes = serializers.DictField(child=serializers.CharField(max_length=200), default=dict)
    validado = serializers.BooleanField(default=False)
    activo = serializers.BooleanField(default=True)

    def validate(self, data):
        abrir = data.get("abrir", getattr(self.instance, "abrir", None))
        cerrar = data.get("cerrar", getattr(self.instance, "cerrar", None))
        if abrir is not None and cerrar is not None and cerrar - abrir < 3:
            raise serializers.ValidationError({"cerrar": "Debe superar a «abrir» por al menos 3 puntos."})
        etapas = data.get("etapas")
        if etapas:
            if etapas[0]["desde"] != 0:
                raise serializers.ValidationError({"etapas": "La primera etapa empieza el día 0."})
            if any(b["desde"] <= a["desde"] for a, b in zip(etapas, etapas[1:])):
                raise serializers.ValidationError({"etapas": "Los días de inicio deben ir en aumento."})
        return data


class CamaPlanSerializer(serializers.Serializer):
    """Cambio del plan de una cama. `cultivo_id: null` la deja en descanso."""

    cultivo_id = serializers.SlugField(required=False, allow_null=True)
    sembrado_el = serializers.DateField(required=False, allow_null=True)
    cosechando = serializers.BooleanField(required=False)
    ajuste = serializers.IntegerField(required=False)

    def validate(self, data):
        if not data:
            raise serializers.ValidationError("Nada para cambiar.")
        return data


class IntercambiarSerializer(serializers.Serializer):
    zonas = serializers.ListField(child=serializers.CharField(max_length=10), min_length=2, max_length=2)


class CalibrarSerializer(serializers.Serializer):
    zona = serializers.CharField(max_length=10)
    puntos = serializers.IntegerField(min_value=-6, max_value=6)


class RegarSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=["abrir", "cerrar"])


class CamaConfigSerializer(serializers.Serializer):
    """Configuración técnica de una cama (solo equipo)."""

    zona = serializers.RegexField(r"^[A-Za-z0-9]{1,10}$", required=False)
    orden = serializers.IntegerField(min_value=0, max_value=99, required=False)
    gateway_zona = serializers.CharField(max_length=10, required=False, allow_null=True, allow_blank=True)
    valvula = serializers.ChoiceField(choices=["RO1", "RO2"], required=False, allow_null=True)
    sensor = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)

    def validate_gateway_zona(self, valor):
        valor = (valor or "").strip() or None
        if valor and not _ZONA_GATEWAY.match(valor):
            raise serializers.ValidationError("Debe ser una zona del gateway: z1, z2…")
        return valor

    def validate_sensor(self, valor):
        return (valor or "").strip().lower() or None


class ReporteSerializer(serializers.Serializer):
    zona = serializers.CharField(max_length=10, required=False, allow_null=True, allow_blank=True)
    matas = serializers.ChoiceField(choices=Reporte.MATAS)
    tierra = serializers.ChoiceField(choices=Reporte.TACTO)
    plaga = serializers.ChoiceField(choices=Reporte.PLAGA)
    riego_mano = serializers.ChoiceField(choices=Reporte.RIEGO_MANO)
    cosecha = serializers.ChoiceField(choices=Reporte.COSECHA)
    nota = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    autoria = serializers.ChoiceField(choices=Reporte.AUTORIA, default="rol")
    autor_nombre = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    autor_rol = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class ModeracionSerializer(serializers.Serializer):
    moderacion = serializers.ChoiceField(choices=Reporte.MODERACION)


class CuidadorSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField()
