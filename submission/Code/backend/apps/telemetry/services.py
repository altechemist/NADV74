"""
Automatic request creation from sensor readings.

Each rule checks its threshold, then reuses an existing open SYSTEM ticket
for the same problem (dedupe_key) so a sensor that keeps tripping does not
flood the queue. Auto-created requests enter exactly the same workflow as
student reports.
"""
from django.conf import settings

from apps.requests.models import Category, RequestHistory, ServiceRequest
from apps.accounts.models import User

from .models import TelemetryReading


def _has_open_request(dedupe_key):
    return ServiceRequest.objects.filter(
        dedupe_key=dedupe_key,
        status__in=ServiceRequest.OPEN_STATUSES,
    ).exists()


def _raise_system_request(category_name, priority, title, description, location, dedupe_key):
    category, _ = Category.objects.get_or_create(name=category_name)
    request_obj = ServiceRequest.objects.create(
        title=title,
        description=description,
        category=category,
        location=location or "Unspecified location",
        priority=priority,
        status=ServiceRequest.Status.PENDING,
        source=ServiceRequest.Source.SYSTEM,
        created_by=None,
        dedupe_key=dedupe_key,
    )
    RequestHistory.objects.create(
        request=request_obj,
        entry_type=RequestHistory.EntryType.CREATED,
        to_status=ServiceRequest.Status.PENDING,
        comment="Auto-created by the telemetry service.",
    )

    # Administrators are the safety net for anything the sensors pick up.
    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    for admin in admins:
        admin.notifications.create(
            title=f"{request_obj.reference} raised automatically",
            message=f"{title} at {location or 'unspecified location'}.",
            request=request_obj,
        )
    return request_obj


def _consecutive_failures(reading, limit):
    """
    Count how many of this device's most recent checks reported unreachable.
    Scoping by device keeps one faulty sensor from failing another's streak.
    """
    queryset = TelemetryReading.objects.filter(
        sensor_type="network",
        reachable__isnull=False,
    )
    if reading.device_id:
        queryset = queryset.filter(device_id=reading.device_id)
    elif reading.location:
        queryset = queryset.filter(location=reading.location)

    streak = 0
    recent = queryset.order_by("-recorded_at", "-id")[:limit]
    for item in recent:
        if item.reachable:
            break
        streak += 1
    return streak


def handle_reading(reading):
    """Apply the rule for this sensor type. Returns a new request or None."""
    if reading.sensor_type == "network":
        return _handle_network(reading)
    if reading.sensor_type == "water":
        return _handle_water(reading)
    if reading.sensor_type == "fire":
        return _handle_fire(reading)
    return None


def _handle_network(reading):
    # A successful ping ends any failure streak, so there is nothing to do.
    if reading.reachable:
        return None

    failures = _consecutive_failures(reading, settings.NETWORK_FAILURE_COUNT)
    if failures < settings.NETWORK_FAILURE_COUNT:
        return None

    dedupe_key = f"network:{reading.device_id or reading.location}"
    if _has_open_request(dedupe_key):
        return None
    return _raise_system_request(
        category_name="IT Support",
        priority=ServiceRequest.Priority.HIGH,
        title=f"Network unreachable at {reading.location or reading.device_id}",
        description=(
            f"The network monitor reported {failures} consecutive failed gateway "
            f"checks (last latency {reading.value:.0f} ms)."
        ),
        location=reading.location,
        dedupe_key=dedupe_key,
    )


def _handle_water(reading):
    if reading.value < settings.WATER_MOISTURE_THRESHOLD:
        return None

    dedupe_key = f"water:{reading.device_id or reading.location}"
    if _has_open_request(dedupe_key):
        return None
    return _raise_system_request(
        category_name="Facilities",
        priority=ServiceRequest.Priority.HIGH,
        title=f"Possible water leak at {reading.location or reading.device_id}",
        description=(
            f"The water leak sensor measured {reading.value:.0f}% moisture, above "
            f"the configured threshold of {settings.WATER_MOISTURE_THRESHOLD:.0f}%."
        ),
        location=reading.location,
        dedupe_key=dedupe_key,
    )


def _handle_fire(reading):
    smoke = reading.value
    temperature = reading.secondary_value or 0.0
    smoke_breached = smoke >= settings.FIRE_SMOKE_THRESHOLD
    temperature_breached = temperature >= settings.FIRE_TEMPERATURE_THRESHOLD
    if not (smoke_breached or temperature_breached):
        return None

    dedupe_key = f"fire:{reading.device_id or reading.location}"
    if _has_open_request(dedupe_key):
        return None

    reasons = []
    if smoke_breached:
        reasons.append(f"smoke level {smoke:.0f}")
    if temperature_breached:
        reasons.append(f"temperature {temperature:.0f} °C")
    return _raise_system_request(
        category_name="Safety",
        priority=ServiceRequest.Priority.CRITICAL,
        title=f"Fire/smoke alert at {reading.location or reading.device_id}",
        description=(
            f"The fire/smoke sensor crossed a threshold: {', '.join(reasons)}. "
            "Immediate inspection required."
        ),
        location=reading.location,
        dedupe_key=dedupe_key,
    )
