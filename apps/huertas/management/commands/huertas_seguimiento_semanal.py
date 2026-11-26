"""Seguimiento automático (HU-HB06): una vez por semana (cron: lunes 5 a. m.) genera el
seguimiento de cada huerta que tenga novedades. Respeta el tope de 6 horas y el tope mensual.

    python manage.py huertas_seguimiento_semanal [--agrohub AH-002]
"""
from django.core.management.base import BaseCommand

from apps.agrohubs.models import AgroHub
from apps.huertas import seguimiento


class Command(BaseCommand):
    help = "Genera el seguimiento de las huertas con novedades."

    def add_arguments(self, parser):
        parser.add_argument("--agrohub", help="Número o id de un solo AgroHub")

    def handle(self, *args, **opts):
        qs = AgroHub.objects.filter(camas__isnull=False).distinct()
        if opts.get("agrohub"):
            ref = opts["agrohub"]
            qs = qs.filter(id=int(ref)) if ref.isdigit() else qs.filter(numero__iexact=ref)
        for a in qs:
            if not seguimiento.estado(a)["hay_novedades"]:
                self.stdout.write(f"{a.numero}: sin novedades")
                continue
            try:
                s, nuevo = seguimiento.generar(a, automatico=True)
                self.stdout.write(f"{a.numero}: {'nuevo' if nuevo else 'guardado'} ({s.modelo}, ${s.costo_usd})")
            except seguimiento.SeguimientoError as exc:
                self.stdout.write(f"{a.numero}: {exc.mensaje}")
