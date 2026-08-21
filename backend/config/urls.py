"""Root URL configuration. Every CSRMS endpoint lives under /api/."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.requests.urls")),
    path("api/telemetry/", include("apps.telemetry.urls")),
    path("api/", include("apps.dashboard.urls")),
]
