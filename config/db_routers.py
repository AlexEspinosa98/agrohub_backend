class RiegoIotRouter:
    """Enruta apps.riego_iot (gateways de riego IoT) a la base 'mqtt' (Postgres), todo lo demás
    sigue yendo a 'default' (MySQL) sin cambios — ver settings.py, sección DATABASES."""

    app_label = "riego_iot"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return "mqtt"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return "mqtt"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == self.app_label or obj2._meta.app_label == self.app_label:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # apps.riego_iot son modelos managed=False sobre tablas que ya existen (las escribe el
        # daemon de ingesta de mqtt_agrohub) — nunca correr `migrate` sobre ellas, en ninguna base.
        if app_label == self.app_label:
            return False
        # Y nada de las otras apps debería terminar en la base 'mqtt' por accidente.
        if db == "mqtt":
            return False
        return None
