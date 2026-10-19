from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agrohubs', '0002_agrohub_dispositivo'),
    ]

    operations = [
        migrations.AddField(model_name='agrohub', name='nombre', field=models.CharField(blank=True, max_length=150, null=True)),
        migrations.AddField(model_name='agrohub', name='tipologia', field=models.CharField(blank=True, max_length=50, null=True)),
        migrations.AddField(model_name='agrohub', name='responsable', field=models.CharField(blank=True, max_length=200, null=True)),
        migrations.AddField(model_name='agrohub', name='celular', field=models.CharField(blank=True, max_length=30, null=True)),
        migrations.AddField(model_name='agrohub', name='tipo_fuente', field=models.CharField(blank=True, max_length=100, null=True)),
        migrations.AddField(model_name='agrohub', name='punto_captacion', field=models.CharField(blank=True, max_length=150, null=True)),
        migrations.AlterField(model_name='agrohub', name='familias', field=models.JSONField(blank=True, default=list)),
    ]
