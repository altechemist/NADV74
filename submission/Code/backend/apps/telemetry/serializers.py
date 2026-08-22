"""Serializers for telemetry readings, matching the frontend chart shape."""
from rest_framework import serializers

from .models import TelemetryReading


class TelemetryReadingSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="recorded_at")

    class Meta:
        model = TelemetryReading
        fields = ["timestamp", "sensor_type", "value", "secondary_value", "reachable", "location", "device_id"]
