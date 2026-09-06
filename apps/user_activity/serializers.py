from rest_framework import serializers


class AssociationCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    department = serializers.CharField(required=False, allow_null=True)
    municipality = serializers.CharField(required=False, allow_null=True)
    vereda = serializers.CharField(required=False, allow_null=True)


class AssociationUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    department = serializers.CharField(required=False, allow_null=True)
    municipality = serializers.CharField(required=False, allow_null=True)
    vereda = serializers.CharField(required=False, allow_null=True)


class UserRegisterSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone = serializers.CharField()
    identification = serializers.CharField()
    email = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField()
    association_id = serializers.IntegerField(required=False, allow_null=True)


class AdminUserCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone = serializers.CharField()
    identification = serializers.CharField()
    email = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField()
    association_id = serializers.IntegerField(required=False, allow_null=True)
    role = serializers.CharField(required=False, default="user")


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    identification = serializers.CharField(required=False)
    email = serializers.CharField(required=False, allow_null=True)
    association_id = serializers.IntegerField(required=False, allow_null=True)
    role = serializers.CharField(required=False, allow_null=True)


class UserLoginSerializer(serializers.Serializer):
    phone_or_identification = serializers.CharField()
    password = serializers.CharField()
    platform = serializers.ChoiceField(choices=["app", "web"], required=False, allow_null=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.CharField()
    otp = serializers.CharField()
    new_password = serializers.CharField()


class SuperadminCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    phone = serializers.CharField()
    identification = serializers.CharField()
    email = serializers.CharField(required=False, allow_null=True)
    password = serializers.CharField()
    association_id = serializers.IntegerField(required=False, allow_null=True)


class RoleCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)


class RoleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_null=True)


class RoleAssignSerializer(serializers.Serializer):
    role = serializers.CharField()


class LogbookCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    activity_date = serializers.DateField()


class LogbookUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    activity_date = serializers.DateField(required=False)
    association_id = serializers.IntegerField(required=False, allow_null=True)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    session_id = serializers.CharField(required=False, allow_null=True)
