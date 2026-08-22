"""
Tests for the telemetry endpoints: device-key authentication, per-device
authorisation and the three auto-request rules (network, water, fire).
"""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.requests.models import RequestHistory, ServiceRequest
from apps.telemetry.models import DeviceKey, TelemetryReading

STRONG_PASSWORD = "S0l-Plaatje#2026"


class TelemetryBase(APITestCase):
    def setUp(self):
        self.network_key = DeviceKey.issue("net-01", DeviceKey.DeviceType.NETWORK)[1]
        self.water_key = DeviceKey.issue("water-01", DeviceKey.DeviceType.WATER)[1]
        self.fire_key = DeviceKey.issue("fire-01", DeviceKey.DeviceType.FIRE)[1]

    def post_network(self, key, reachable=False, latency_ms=0, **extra):
        payload = {"reachable": reachable, "latency_ms": latency_ms, "location": "Server room", **extra}
        return self.client.post(
            "/api/telemetry/network/", payload, HTTP_X_DEVICE_KEY=key, format="json"
        )

    def post_water(self, key, moisture_percent=10, **extra):
        payload = {"moisture_percent": moisture_percent, "location": "Residence C", **extra}
        return self.client.post("/api/telemetry/water/", payload, HTTP_X_DEVICE_KEY=key, format="json")

    def post_fire(self, key, smoke_level=10, temperature_c=22, **extra):
        payload = {"smoke_level": smoke_level, "temperature_c": temperature_c, "location": "ICT lab", **extra}
        return self.client.post("/api/telemetry/fire/", payload, HTTP_X_DEVICE_KEY=key, format="json")


class DeviceAuthenticationTests(TelemetryBase):
    def test_missing_key_rejected(self):
        response = self.client.post("/api/telemetry/network/", {"reachable": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_key_rejected(self):
        response = self.post_network("not-a-real-key", reachable=True)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoked_key_rejected(self):
        device_key = DeviceKey.objects.get(name="water-01")
        device_key.is_revoked = True
        device_key.save()

        response = self.post_water(self.water_key)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_jwt_is_not_enough_for_telemetry(self):
        # Sensors authenticate with keys, people with JWTs - never the mix.
        # A valid user is identified but still forbidden, hence 403 not 401.
        user = User.objects.create_user(username="lerato", password=STRONG_PASSWORD)
        self.client.force_authenticate(user=user)
        response = self.client.post("/api/telemetry/network/", {"reachable": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_key_is_tied_to_one_sensor_type(self):
        # The water key must not be able to post fire readings.
        response = self.post_fire(self.water_key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_sensor_endpoint_returns_404(self):
        response = self.client.post(
            "/api/telemetry/temperature/", {"value": 1}, HTTP_X_DEVICE_KEY=self.network_key, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class IngestTests(TelemetryBase):
    def test_valid_network_reading_stored(self):
        response = self.post_network(self.network_key, reachable=True, latency_ms=18)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reading = TelemetryReading.objects.latest("id")
        self.assertTrue(reading.reachable)
        self.assertEqual(reading.value, 18.0)

    def test_invalid_payload_rejected(self):
        response = self.post_water(self.water_key, moisture_percent=250)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.post_fire(self.fire_key, smoke_level="lots")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NetworkAutoRequestTests(TelemetryBase):
    def test_three_consecutive_failures_raise_request(self):
        for _ in range(2):
            self.post_network(self.network_key, reachable=False)
        self.assertFalse(ServiceRequest.objects.exists())

        response = self.post_network(self.network_key, reachable=False)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["auto_request"])

        request_obj = ServiceRequest.objects.get()
        self.assertEqual(request_obj.category.name, "IT Support")
        self.assertEqual(request_obj.priority, ServiceRequest.Priority.HIGH)
        self.assertEqual(request_obj.source, ServiceRequest.Source.SYSTEM)
        self.assertIsNone(request_obj.created_by)
        self.assertTrue(
            RequestHistory.objects.filter(request=request_obj, entry_type="CREATED").exists()
        )

    def test_successful_ping_resets_the_streak(self):
        for _ in range(3):
            self.post_network(self.network_key, reachable=False)
        self.post_network(self.network_key, reachable=True)  # streak broken
        for _ in range(2):
            self.post_network(self.network_key, reachable=False)

        self.assertEqual(ServiceRequest.objects.count(), 1)

    def test_no_duplicate_while_ticket_open(self):
        for _ in range(6):
            self.post_network(self.network_key, reachable=False)
        self.assertEqual(ServiceRequest.objects.count(), 1)

    def test_new_ticket_after_previous_resolved(self):
        for _ in range(3):
            self.post_network(self.network_key, reachable=False)
        ticket = ServiceRequest.objects.get()
        ticket.status = ServiceRequest.Status.RESOLVED
        ticket.save()

        for _ in range(3):
            self.post_network(self.network_key, reachable=False)
        self.assertEqual(ServiceRequest.objects.count(), 2)


class WaterAutoRequestTests(TelemetryBase):
    def test_moisture_below_threshold_creates_nothing(self):
        self.post_water(self.water_key, moisture_percent=40)
        self.assertFalse(ServiceRequest.objects.exists())

    def test_moisture_above_threshold_raises_high_facilities_request(self):
        response = self.post_water(self.water_key, moisture_percent=85)
        self.assertIsNotNone(response.data["auto_request"])

        request_obj = ServiceRequest.objects.get()
        self.assertEqual(request_obj.category.name, "Facilities")
        self.assertEqual(request_obj.priority, ServiceRequest.Priority.HIGH)
        self.assertEqual(request_obj.source, ServiceRequest.Source.SYSTEM)

    def test_repeated_breach_does_not_duplicate_ticket(self):
        for _ in range(4):
            self.post_water(self.water_key, moisture_percent=90)
        self.assertEqual(ServiceRequest.objects.count(), 1)


class FireAutoRequestTests(TelemetryBase):
    def test_normal_readings_create_nothing(self):
        self.post_fire(self.fire_key, smoke_level=8, temperature_c=24)
        self.assertFalse(ServiceRequest.objects.exists())

    def test_smoke_alone_raises_critical_safety_request(self):
        self.post_fire(self.fire_key, smoke_level=60, temperature_c=24)
        request_obj = ServiceRequest.objects.get()
        self.assertEqual(request_obj.category.name, "Safety")
        self.assertEqual(request_obj.priority, ServiceRequest.Priority.CRITICAL)

    def test_temperature_alone_raises_critical_safety_request(self):
        self.post_fire(self.fire_key, smoke_level=5, temperature_c=90)
        self.assertEqual(ServiceRequest.objects.get().priority, ServiceRequest.Priority.CRITICAL)

    def test_auto_created_ticket_follows_manual_workflow(self):
        # A SYSTEM ticket must behave like any other: staff can assign it
        # and move it through the same statuses.
        self.post_fire(self.fire_key, smoke_level=99, temperature_c=30)
        ticket = ServiceRequest.objects.get()

        staff = User.objects.create_user(username="lerato", password=STRONG_PASSWORD, role=User.Role.STAFF)
        self.client.force_authenticate(user=staff)
        response = self.client.post(f"/api/requests/{ticket.pk}/assign/", {"assigned_to": staff.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.patch(f"/api/requests/{ticket.pk}/status/", {"status": "IN_PROGRESS"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
