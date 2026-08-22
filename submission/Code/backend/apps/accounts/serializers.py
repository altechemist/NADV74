"""Serializers for accounts: public profile, registration and admin writes."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Read-only profile shape used in responses across the API."""

    role = serializers.CharField(source="effective_role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public sign-up. The role field is deliberately not writable here:
    whatever the client posts, the account is created as a STUDENT. Staff
    and admin accounts can only be issued by an administrator via /users/.
    """

    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]

    def validate_password(self, value):
        # Runs Django's standard strength rules (length, similarity, common
        # passwords, all-numeric).
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
            role=User.Role.STUDENT,
        )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields a user may change on their own profile."""

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]


class UserManageSerializer(serializers.ModelSerializer):
    """
    Admin-side create/update of staff and admin accounts. Passwords are
    write-only and validated with the same rules as registration.
    """

    role = serializers.ChoiceField(choices=User.Role.choices)
    password = serializers.CharField(write_only=True, trim_whitespace=False, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "password",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
