"""Camas por defecto para que ninguna huerta salga vacía mientras el equipo técnico arma las reales.

Para cada AgroHub SIN camas:
- una cama por cada sonda de tierra que su gateway reportó en los últimos 30 días (A, B, C…),
  con la humedad REAL de esa sonda;
- el cultivo sale de lo que el micrositio del AgroHub dice que se siembra (la misma lista que
  usaba la demostración del front), con una fecha de siembra de referencia;
- SIN válvula ni zona del gateway: así no se inventan riegos ni alarmas de «el agua no llega».
  «Regar» queda deshabilitado hasta que el equipo diga qué llave tiene cada cama;
- si el AgroHub no tiene gateway, se crean las camas del micrositio sin sonda.

Quedan con `origen="referencia"` (la web lo avisa) y pasan a «equipo» apenas una persona cambia
el plan o la configuración. No toca huertas que ya tengan camas.

    python manage.py huertas_camas_por_defecto              # ver qué crearía
    python manage.py huertas_camas_por_defecto --aplicar    # crearlas
    python manage.py huertas_camas_por_defecto --borrar     # quitar las de referencia sin tocar
"""
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as dj_timezone

from apps.agrohubs.models import AgroHub
from apps.huertas import ciclo
from apps.huertas.models import Cama, Cultivo

ZONAS = "ABCDEFGH"
MAXIMO = 4
# Lo que cada micrositio dice que se siembra (front, `huertas.ts` de la demostración).
CULTIVOS_MICROSITIO = {
    "AH-001": ["tomate", "pepino", "aji"],
    "AH-002": ["aji", "yuca"],
    "AH-003": ["tomate", "habichuela", "cilantro", "berenjena"],
    "AH-004": ["berenjena", "habichuela", "cebollin", "tomate"],
    "AH-005": ["tomate", "pimenton", "cilantro"],
    "AH-006": ["aji", "berenjena", "oregano"],
    "AH-007": ["lechuga", "col", "tomate"],
    "AH-008": ["aji", "cilantro"],
    "AH-009": ["maiz", "ahuyama", "frijol", "patilla"],
    "AH-010": ["yuca", "platano"],
    "AH-011": ["tomate", "melon", "cebollin"],
    "AH-012": ["maiz", "yuca", "cilantro"],
    "AH-013": ["maiz", "ahuyama", "yuca"],
    "AH-014": ["aji", "cilantro", "tomate"],
    "AH-015": ["maiz", "ahuyama", "pimenton", "berenjena"],
    "AH-016": ["yuca", "maiz", "cilantro"],
}
RESPALDO = ["aji", "cilantro"]
# En qué punto de su ciclo se pone cada cama (fracción de los días hasta la primera cosecha).
AVANCE = [0.55, 0.3, 0.8, 0.45]


def sondas(device_id, dias=30):
    """dev_eui de las sondas de tierra del gateway, ordenadas por su nombre (SE01-01, SE01-02…)."""
    from apps.riego_iot.models import LecturaSuelo

    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    vistos = {}
    for dev_eui, equipo in (
        LecturaSuelo.objects.using("mqtt")
        .filter(device_id=device_id, medido_en__gte=desde, humedad_suelo__isnull=False)
        .values_list("dev_eui", "payload_crudo__equipo")
        .distinct()
    ):
        if dev_eui:
            vistos.setdefault(dev_eui, equipo or dev_eui)
    return [d for d, _ in sorted(vistos.items(), key=lambda x: x[1])]


def propuesta(agrohub, fichas):
    """Lista de camas que se crearían para este AgroHub."""
    cultivos = [c for c in CULTIVOS_MICROSITIO.get(agrohub.numero, RESPALDO) if c in fichas] or RESPALDO
    lista_sondas = sondas(agrohub.dispositivo) if agrohub.dispositivo else []
    n = min(MAXIMO, len(lista_sondas) or len(cultivos))
    hoy = dj_timezone.localdate()
    camas = []
    for i in range(n):
        cultivo = cultivos[i % len(cultivos)]
        dias = round(ciclo.dias_a_cosecha(fichas[cultivo]) * AVANCE[i % len(AVANCE)])
        camas.append({
            "zona": ZONAS[i],
            "orden": i,
            "cultivo_id": cultivo,
            "sembrado_el": hoy - timedelta(days=dias),
            "sensor": lista_sondas[i] if i < len(lista_sondas) else None,
        })
    return camas


class Command(BaseCommand):
    help = "Crea camas de referencia (sondas reales + cultivos del micrositio) en las huertas sin camas."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Crear las camas (sin esto solo muestra)")
        parser.add_argument("--borrar", action="store_true", help="Quitar las camas de referencia")
        parser.add_argument("--agrohub", help="Número o id de un solo AgroHub")

    def handle(self, *args, **opts):
        qs = AgroHub.objects.order_by("numero")
        if opts.get("agrohub"):
            ref = opts["agrohub"]
            qs = qs.filter(id=int(ref)) if ref.isdigit() else qs.filter(numero__iexact=ref)

        if opts["borrar"]:
            borradas, _ = Cama.objects.filter(agrohub__in=qs, origen="referencia").delete()
            self.stdout.write(f"Camas de referencia borradas: {borradas}")
            return

        fichas = {c.id: c.ficha_dict() for c in Cultivo.objects.prefetch_related("etapas")}
        total = 0
        for a in qs:
            if a.camas.exists():
                self.stdout.write(f"{a.numero}: ya tiene camas, no se toca")
                continue
            camas = propuesta(a, fichas)
            detalle = ", ".join(
                f"{c['zona']}={c['cultivo_id']}{' (sonda)' if c['sensor'] else ' (sin sonda)'}" for c in camas
            )
            self.stdout.write(f"{a.numero}: {detalle}")
            if opts["aplicar"]:
                with transaction.atomic():
                    Cama.objects.bulk_create([Cama(agrohub=a, origen="referencia", **c) for c in camas])
                total += len(camas)
        if opts["aplicar"]:
            self.stdout.write(f"Camas creadas: {total}")
        else:
            self.stdout.write("Vista previa: corre con --aplicar para crearlas.")
