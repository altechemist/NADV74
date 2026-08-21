"""Serializers for categories, requests, timelines and notifications."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Notification, RequestHistory, ServiceRequest

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "active"]


class RequestUserSerializer(serializers.ModelSerializer):
    """Compact user shape used inside request payloads."""

    role = serializers.CharField(source="effective_role", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role"]


class ServiceRequestSerializer(serializers.ModelSerializer):
    created_by = RequestUserSerializer(read_only=True)
    assigned_to = RequestUserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    # Clients pick a category by id; the nested object above is response-only.
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(), write_only=True
    )

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "reference",
            "title",
            "description",
            "category",
            "category_id",
            "location",
            "priority",
            "status",
            "source",
            "created_by",
            "assigned_to",
            "created_at",
            "updated_at",
        ]
        # Status, assignment and source only ever change through their own
        # endpoints so every step is logged.
        read_only_fields = [
            "reference",
            "status",
            "source",
            "created_by",
            "assigned_to",
            "created_at",
            "updated_at",
        ]


class RequestStatusSerializer(serializers.Serializer):
    """Body of PATCH /requests/{id}/status/."""

    status = serializers.ChoiceField(choices=ServiceRequest.Status.choices)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class AssignRequestSerializer(serializers.Serializer):
    """Body of POST /requests/{id}/assign/."""

    assigned_to = serializers.IntegerField()


class CommentSerializer(serializers.Serializer):
    """Body of POST /requests/{id}/updates/."""

    comment = serializers.CharField(max_length=2000)


class RequestHistorySerializer(serializers.ModelSerializer):
    changed_by = RequestUserSerializer(read_only=True)

    class Meta:
        model = RequestHistory
        fields = [
            "id",
            "entry_type",
            "changed_by",
            "from_status",
            "to_status",
            "comment",
            "created_at",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    request = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "title", "message", "request", "is_read", "created_at"]
