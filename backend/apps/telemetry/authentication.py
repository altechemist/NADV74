"""
Authentication for the telemetry endpoints.

Devices present their key in the X-Device-Key header instead of a user JWT.
A matching, non-revoked key produces a DeviceUser principal so the standard
DRF permission machinery still applies; the key itself is attached as
request.auth for the views to inspect.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from .models import DeviceKey


class DeviceUser(AnonymousUser):
    """Stand-in principal for a sensor. It owns no data and has no role."""

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return "device"


class DeviceKeyAuthentication(BaseAuthentication):
    header = "X-Device-Key"

    def authenticate(self, request):
        raw_key = request.headers.get(self.header)
        if not raw_key:
            # No device credential supplied; let other authenticators run so
            # the caller gets the usual "credentials not provided" answer.
            return None

        key = (
            DeviceKey.objects.filter(key_hash=DeviceKey.hash(raw_key), is_revoked=False)
            .select_related()
            .first()
        )
        if key is None:
            raise AuthenticationFailed("Unknown or revoked device key.")

        key.last_used_at = timezone.now()
        key.save(update_fields=["last_used_at"])
        return (DeviceUser(), key)

    def authenticate_header(self, request):
        # Telling DRF where the credential belongs keeps failed attempts at
        # HTTP 401 instead of being downgraded to 403.
        return f'{self.header} realm="csrms-telemetry"'
