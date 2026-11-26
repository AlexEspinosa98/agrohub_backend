"""Tarea diaria (HU-HB02): cuando una cama cambia de etapa su umbral cambia (+4 recién sembrada,
−4 al final si conviene secar). Recalcula todas las huertas y reenvía solo lo que cambió.
Con HUERTAS_ENVIAR_UMBRALES apagado solo recalcula (no toca los gateways).

    python manage.py huertas_revisar_etapas [--agrohub AH-002] [--forzar]
"""
from django.core.management.base import BaseCommand

from apps.agrohubs.models import AgroHub
from apps.huertas import plan


class Command(BaseCommand):
    help = "Recalcula los umbrales por etapa y los reenvía a los gateways si cambiaron."

    def add_arguments(self, parser):
        parser.add_argument("--agrohub", help="Número o id de un solo AgroHub")
        parser.add_argument("--forzar", action="store_true", help="Reenviar aunque no haya cambiado nada")

    def handle(self, *args, **opts):
        qs = AgroHub.objects.filter(camas__isnull=False).distinct()
        if opts.get("agrohub"):
            ref = opts["agrohub"]
            qs = qs.filter(id=int(ref)) if ref.isdigit() else qs.filter(numero__iexact=ref)
        for a in qs:
            r = plan.recalcular_y_enviar(a, forzar=opts["forzar"])
            detalle = ", ".join(f"{z}:{v['resultado']}" for z, v in r["camas"].items())
            self.stdout.write(f"{a.numero}: {r['resultado']} ({detalle})")
