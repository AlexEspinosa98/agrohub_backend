from django.db import migrations

DEFAULT_ROLES = [
    ("user", "Usuario estándar"),
    ("admin", "Administrador"),
    ("superadmin", "Super administrador"),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("user_activity", "Role")
    for name, description in DEFAULT_ROLES:
        Role.objects.get_or_create(name=name, defaults={"description": description})


def remove_roles(apps, schema_editor):
    Role = apps.get_model("user_activity", "Role")
    Role.objects.filter(name__in=[name for name, _ in DEFAULT_ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("user_activity", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, remove_roles),
    ]
