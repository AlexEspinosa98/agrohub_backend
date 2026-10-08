import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia_eventos', '0004_personaasistente_comunidad'),
        ('user_activity', '0003_remove_user_auth_token_session'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScanJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('procesando', 'Procesando'), ('completo', 'Completo'), ('error', 'Error')], default='pendiente', max_length=12)),
                ('archivo', models.TextField()),
                ('nombre_archivo', models.CharField(blank=True, max_length=255)),
                ('paginas_total', models.IntegerField(blank=True, null=True)),
                ('paginas_procesadas', models.IntegerField(default=0)),
                ('resultado', models.JSONField(blank=True, default=dict)),
                ('error_mensaje', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completado_en', models.DateTimeField(blank=True, null=True)),
                ('registrado_por', models.ForeignKey(blank=True, db_column='registrado_por_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scan_jobs_asistencia', to='user_activity.user')),
            ],
            options={
                'db_table': 'scan_jobs_asistencia',
                'ordering': ['-created_at'],
            },
        ),
    ]
