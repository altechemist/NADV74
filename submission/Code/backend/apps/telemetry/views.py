"""
Telemetry endpoints.

POST /api/telemetry/network|water|fire/  - device-key authenticated ingest
GET  /api/telemetry/history/             - staff/admin chart data
"""
from collections import defaultdict

from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStaffOrAdmin

from .authentication import DeviceKeyAuthentication
from .models import DeviceKey, TelemetryReading
from .serializers import TelemetryReadingSerializer
from .services import handle_reading


class IsDeviceKey(IsAuthenticated):
    """
    Only requests that presented a device key get through. A valid user JWT
    is deliberately not enough here: sensors are not people.
    """

    def has_permission(self, request, view):
        return isinstance(getattr(request, "auth", None), DeviceKey)


def _as_float(payload, field, required=True):
    raw = payload.get(field)
    if raw is None or raw == "":
        if required:
            raise ValueError(f"'{field}' is required.")
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"'{field}' must be a number.")


class TelemetryIngestView(APIView):
    """Receive one reading from a sensor and run the auto-request rules."""

    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [IsDeviceKey]

    def post(self, request, sensor_type):
        sensor_type = sensor_type.lower()
        if sensor_type not in DeviceKey.DeviceType.values:
            return Response(
                {"detail": f"Unknown sensor type '{sensor_type}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        device_key = request.auth
        # A water key must not be able to post fire data, for example.
        if device_key.device_type != sensor_type:
            return Response(
                {"detail": "This device key is not allowed to post to this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = request.data
        try:
            reading = self._build_reading(sensor_type, payload, device_key)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        reading.save()
        created_request = handle_reading(reading)

        data = TelemetryReadingSerializer(reading).data
        data["auto_request"] = (
            {"id": created_request.pk, "reference": created_request.reference} if created_request else None
        )
        return Response(data, status=status.HTTP_201_CREATED)

    def _build_reading(self, sensor_type, payload, device_key):
        recorded_at = timezone.now()
        common = {
            "sensor_type": sensor_type,
            "recorded_at": recorded_at,
            "location": str(payload.get("location", ""))[:180],
            "device_id": str(payload.get("device_id", "") or device_key.name)[:120],
            "posted_by": device_key,
        }

        if sensor_type == "network":
            reachable = payload.get("reachable")
            if not isinstance(reachable, bool):
                raise ValueError("'reachable' must be true or false.")
            latency = _as_float(payload, "latency_ms", required=False)
            return TelemetryReading(value=latency or 0.0, reachable=reachable, **common)

        if sensor_type == "water":
            moisture = _as_float(payload, "moisture_percent")
            if not 0 <= moisture <= 100:
                raise ValueError("'moisture_percent' must be between 0 and 100.")
            return TelemetryReading(value=moisture, **common)

        # fire/smoke: both metrics in one reading
        smoke = _as_float(payload, "smoke_level")
        temperature = _as_float(payload, "temperature_c")
        return TelemetryReading(value=smoke, secondary_value=temperature, **common)


class TelemetryHistoryView(APIView):
    """Recent readings per sensor for the dashboard charts."""

    permission_classes = [IsStaffOrAdmin]

    def get(self, request):
        range_name = request.query_params.get("range", "live")
        hours = {"live": 12, "24_hours": 24, "7_days": 24 * 7}.get(range_name, 12)
        since = timezone.now() - timedelta(hours=hours)

        readings = TelemetryReading.objects.filter(recorded_at__gte=since).order_by("recorded_at")
        grouped = defaultdict(list)
        for item in TelemetryReadingSerializer(readings, many=True).data:
            grouped[item["sensor_type"]].append(item)

        return Response(
            {
                "network": grouped.get("network", []),
                "water": grouped.get("water", []),
                "fire": grouped.get("fire", []),
            }
        )
