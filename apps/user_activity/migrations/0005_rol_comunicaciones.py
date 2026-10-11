from django.db import migrations


def crear_rol(apps, schema_editor):
    Role = apps.get_model("user_activity", "Role")
    Role.objects.get_or_create(name="comunicaciones", defaults={"description": "Comunicaciones"})


def borrar_rol(apps, schema_editor):
    apps.get_model("user_activity", "Role").objects.filter(name="comunicaciones").delete()


class Migration(migrations.Migration):
    dependencies = [("user_activity", "0004_rol_investigador")]
    operations = [migrations.RunPython(crear_rol, borrar_rol)]
