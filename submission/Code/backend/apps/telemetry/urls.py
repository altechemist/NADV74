from django.urls import path

from .models import DeviceKey
from .views import TelemetryHistoryView, TelemetryIngestView

# The sensor type is part of the URL; hand it to the shared view explicitly.
urlpatterns = [
    path(
        "network/",
        TelemetryIngestView.as_view(),
        {"sensor_type": DeviceKey.DeviceType.NETWORK},
        name="telemetry-network",
    ),
    path(
        "water/",
        TelemetryIngestView.as_view(),
        {"sensor_type": DeviceKey.DeviceType.WATER},
        name="telemetry-water",
    ),
    path(
        "fire/",
        TelemetryIngestView.as_view(),
        {"sensor_type": DeviceKey.DeviceType.FIRE},
        name="telemetry-fire",
    ),
    path("history/", TelemetryHistoryView.as_view(), name="telemetry-history"),
]
