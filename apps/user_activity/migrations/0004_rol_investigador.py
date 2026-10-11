from django.db import migrations


def crear_rol(apps, schema_editor):
    Role = apps.get_model("user_activity", "Role")
    Role.objects.get_or_create(name="investigador", defaults={"description": "Investigador"})


def borrar_rol(apps, schema_editor):
    apps.get_model("user_activity", "Role").objects.filter(name="investigador").delete()


class Migration(migrations.Migration):
    dependencies = [("user_activity", "0003_remove_user_auth_token_session")]
    operations = [migrations.RunPython(crear_rol, borrar_rol)]
