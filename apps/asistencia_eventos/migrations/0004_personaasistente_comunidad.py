from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia_eventos', '0003_evento_editado_por_evento_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='personaasistente',
            name='comunidad',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
