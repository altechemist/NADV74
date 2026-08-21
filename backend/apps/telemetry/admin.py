from django.contrib import admin

from .models import DeviceKey, TelemetryReading


@admin.register(DeviceKey)
class DeviceKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "device_type", "is_revoked", "last_used_at")
    list_filter = ("device_type", "is_revoked")


@admin.register(TelemetryReading)
class TelemetryReadingAdmin(admin.ModelAdmin):
    list_display = ("sensor_type", "value", "secondary_value", "reachable", "location", "recorded_at")
    list_filter = ("sensor_type",)
