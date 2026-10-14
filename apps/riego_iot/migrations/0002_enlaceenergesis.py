import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('riego_iot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EnlaceEnergesis',
            fields=[
                ('device', models.OneToOneField(db_column='device_id', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='enlace_energesis', serialize=False, to='riego_iot.dispositivo')),
                ('thingsboard_token', models.TextField(db_column='thingsboard_token')),
                ('thingsboard_nombre', models.CharField(blank=True, db_column='thingsboard_nombre', max_length=255, null=True)),
                ('activo', models.BooleanField(db_column='activo', default=True)),
                ('creado_en', models.DateTimeField(db_column='creado_en')),
                ('actualizado_en', models.DateTimeField(db_column='actualizado_en')),
                ('ultimo_envio_en', models.DateTimeField(blank=True, db_column='ultimo_envio_en', null=True)),
                ('ultimo_error', models.TextField(blank=True, db_column='ultimo_error', null=True)),
                ('ultimo_error_en', models.DateTimeField(blank=True, db_column='ultimo_error_en', null=True)),
            ],
            options={
                'db_table': 'enlaces_energesis',
                'managed': False,
            },
        ),
    ]
