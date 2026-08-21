"""Tests for dashboard counts and the notification feed."""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.requests.models import Category, Notification, ServiceRequest

STRONG_PASSWORD = "S0l-Plaatje#2026"


class DashboardTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="naledi", password=STRONG_PASSWORD)
        self.other = User.objects.create_user(username="sipho", password=STRONG_PASSWORD)
        self.staff = User.objects.create_user(
            username="lerato", password=STRONG_PASSWORD, role=User.Role.STAFF
        )
        category = Category.objects.create(name="IT Support")

        ServiceRequest.objects.create(
            title="A", description="", category=category, location="x",
            status=ServiceRequest.Status.PENDING, created_by=self.student,
        )
        ServiceRequest.objects.create(
            title="B", description="", category=category, location="x",
            status=ServiceRequest.Status.IN_PROGRESS, created_by=self.student,
        )
        # Belongs to someone else; a student must not count it.
        ServiceRequest.objects.create(
            title="C", description="", category=category, location="x",
            status=ServiceRequest.Status.PENDING, created_by=self.other,
        )

    def test_student_counts_are_scoped_to_own_requests(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.data["pending"], 1)
        self.assertEqual(response.data["in_progress"], 1)
        self.assertEqual(response.data["assigned"], 0)
        self.assertEqual(response.data["resolved"], 0)

    def test_staff_counts_cover_the_campus(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.data["pending"], 2)
        self.assertEqual(response.data["in_progress"], 1)

    def test_authentication_required(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationTests(APITestCase):
    def test_users_only_see_their_own_notifications(self):
        alice = User.objects.create_user(username="alice", password=STRONG_PASSWORD)
        bob = User.objects.create_user(username="bob", password=STRONG_PASSWORD)
        Notification.objects.create(user=alice, title="t", message="for alice")
        Notification.objects.create(user=bob, title="t", message="for bob")

        self.client.force_authenticate(user=alice)
        response = self.client.get("/api/notifications/")
        messages = [item["message"] for item in response.data]
        self.assertEqual(messages, ["for alice"])
