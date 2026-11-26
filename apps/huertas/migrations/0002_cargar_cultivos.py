"""Carga inicial de la biblioteca: las 18 fichas de la demostración (biblioteca.ts). Son valores de
REFERENCIA (validado=False) hasta revisarlos con AGROSAVIA y la Mesa Técnica Agroclimática."""
import json
from pathlib import Path

from django.db import migrations

ARCHIVO = Path(__file__).resolve().parent.parent / "datos" / "cultivos_iniciales.json"
FUENTES = {
    "kc": "FAO-56, tabla 12",
    "agotable": "FAO-56, tabla 22",
    "raiz": "FAO-56, tabla 22",
    "optimo": "FAO Ecocrop, llevado a tierra caliente",
    "abrir": "Punto de partida para sensor de 0 a 100: calibrar en cada huerta",
    "cerrar": "Punto de partida para sensor de 0 a 100: calibrar en cada huerta",
    "etapas": "Ciclos usuales en clima cálido (0–500 m)",
}


def cargar(apps, schema_editor):
    Cultivo = apps.get_model("huertas", "Cultivo")
    CultivoEtapa = apps.get_model("huertas", "CultivoEtapa")
    for f in json.loads(ARCHIVO.read_text(encoding="utf-8")):
        if Cultivo.objects.filter(id=f["id"]).exists():
            continue
        c = Cultivo.objects.create(
            id=f["id"], nombre=f["nombre"], familia=f["familia"], forma=f["forma"], fruto=f.get("fruto"),
            sed=f["sed"], abrir=f["abrir"], cerrar=f["cerrar"], kc=f["kc"], agotable=f["agotable"],
            raiz=f["raiz"], secar_al_final=f["secarAlFinal"], optimo=f["optimo"], calor_fuerte=f["calorFuerte"],
            siembra=f["siembra"], cosecha_dias=f["cosechaDias"], perenne=f["perenne"],
            distancia=f.get("distancia", ""), luz=f.get("luz", "sol"), amigas=f.get("amigas", []),
            evitar=f.get("evitar", []), plagas=f.get("plagas", []), senal=f.get("senal", ""),
            consejo=f.get("consejo", ""), fuentes=FUENTES, validado=False,
        )
        CultivoEtapa.objects.bulk_create([
            CultivoEtapa(cultivo=c, orden=i, tipo=e["tipo"], nombre=e["nombre"], desde=e["desde"])
            for i, e in enumerate(f["etapas"])
        ])


def borrar(apps, schema_editor):
    apps.get_model("huertas", "Cultivo").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("huertas", "0001_initial")]
    operations = [migrations.RunPython(cargar, borrar)]
