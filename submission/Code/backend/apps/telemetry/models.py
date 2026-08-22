"""
IoT models: per-device API keys and the readings the sensors post.

Device keys are separate from user accounts. Only a SHA-256 hash of each key
is stored, so a database dump never contains a usable credential and any
single key can be revoked without touching user accounts.
"""
import hashlib

from django.db import models
from django.utils.crypto import get_random_string


class DeviceKey(models.Model):
    """Credential one physical (or simulated) sensor uses to reach the API."""

    class DeviceType(models.TextChoices):
        NETWORK = "network", "Network monitor"
        WATER = "water", "Water leak sensor"
        FIRE = "fire", "Fire/smoke sensor"

    name = models.CharField(max_length=120, unique=True)
    device_type = models.CharField(max_length=10, choices=DeviceType.choices)
    key_hash = models.CharField(max_length=64, unique=True)
    is_revoked = models.BooleanField(default=False)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash(raw_key):
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @classmethod
    def issue(cls, name, device_type):
        """
        Create a key and return it. The raw value is shown exactly once;
        from then on only the hash lives in the database.
        """
        raw = get_random_string(48)
        obj = cls.objects.create(name=name, device_type=device_type, key_hash=cls.hash(raw))
        return obj, raw

    def __str__(self):
        return self.name


class TelemetryReading(models.Model):
    """
    One measurement from one sensor.

    value holds the primary metric (latency in ms, moisture %, smoke level);
    secondary_value carries the fire sensor's temperature. reachable is only
    meaningful for network checks.
    """

    sensor_type = models.CharField(max_length=10, choices=DeviceKey.DeviceType.choices)
    recorded_at = models.DateTimeField()
    value = models.FloatField(default=0)
    secondary_value = models.FloatField(null=True, blank=True)
    reachable = models.BooleanField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)
    device_id = models.CharField(max_length=120, blank=True)
    posted_by = models.ForeignKey(
        DeviceKey,
        on_delete=models.SET_NULL,
        related_name="readings",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["recorded_at"]

    def __str__(self):
        return f"{self.sensor_type} @ {self.recorded_at:%Y-%m-%d %H:%M}: {self.value}"
