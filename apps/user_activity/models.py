from django.db import models


class Association(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)
    municipality = models.CharField(max_length=255, null=True, blank=True)
    vereda = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "associations"

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class User(models.Model):
    """Custom auth domain, unrelated to django.contrib.auth.User.

    `role` is a loose varchar (not a FK) on purpose, matching the original
    schema — the roles table is just the catalog of valid values, checked in
    application code, not enforced by a DB constraint.
    """

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, unique=True)
    identification = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    association = models.ForeignKey(
        Association,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="association_id",
        related_name="users",
    )
    role = models.CharField(max_length=50, null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_otp_hash = models.CharField(max_length=255, null=True, blank=True)
    reset_otp_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name} <{self.phone}>"

    # Duck-typed so DRF permission helpers that check `.is_authenticated`
    # (a pattern borrowed from django.contrib.auth) work on this model too.
    @property
    def is_authenticated(self):
        return True


class Session(models.Model):
    """One active token per (user, platform).

    Replaces the old single `User.auth_token` column so the same account can
    hold one token for the app and a separate one for the web at the same
    time, instead of the newest login kicking out the other. `platform` is a
    loose label ("app"/"web"/null), not enforced — logging in without a
    platform just adds another concurrent session rather than replacing one.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="sessions"
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sessions"

    def __str__(self):
        return f"{self.user_id}:{self.platform or 'unknown'}"


class Logbook(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="logbooks"
    )
    association = models.ForeignKey(
        Association,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="association_id",
        related_name="logbooks",
    )
    title = models.TextField()
    description = models.TextField()
    activity_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logbooks"


class Conversation(models.Model):
    ROLE_CHOICES = [("user", "user"), ("model", "model")]

    session_id = models.CharField(max_length=36, db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column="user_id", related_name="conversations"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "conversations"
