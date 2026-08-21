"""
Tests for the request workflow: creation, ownership scoping, status
transitions, assignment, comments and the history timeline.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.requests.models import Category, RequestHistory, ServiceRequest

REQUESTS_URL = "/api/requests/"

STRONG_PASSWORD = "S0l-Plaatje#2026"


def make_user(username, role):
    return User.objects.create_user(username=username, password=STRONG_PASSWORD, role=role)


class RequestWorkflowBase(APITestCase):
    def setUp(self):
        self.student = make_user("naledi", User.Role.STUDENT)
        self.other_student = make_user("sipho", User.Role.STUDENT)
        self.staff = make_user("lerato", User.Role.STAFF)
        self.admin = make_user("admin", User.Role.ADMIN)
        self.category = Category.objects.create(name="IT Support")

    def create_request(self, owner, **overrides):
        """Insert a request directly, bypassing the API, for setup purposes."""
        data = {
            "title": "WiFi outage in the library",
            "description": "No connection since this morning.",
            "category": self.category,
            "location": "Main library",
            "created_by": owner,
        }
        data.update(overrides)
        return ServiceRequest.objects.create(**data)

    def post_request(self, user, **overrides):
        payload = {
            "title": "Broken projector",
            "description": "Projector does not switch on.",
            "category_id": self.category.pk,
            "location": "Lecture hall 2",
            "priority": ServiceRequest.Priority.MEDIUM,
        }
        payload.update(overrides)
        self.client.force_authenticate(user=user)
        return self.client.post(REQUESTS_URL, payload)


class CreationTests(RequestWorkflowBase):
    def test_student_can_create_request(self):
        response = self.post_request(self.student)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_obj = ServiceRequest.objects.get(pk=response.data["id"])
        self.assertEqual(request_obj.status, ServiceRequest.Status.PENDING)
        self.assertEqual(request_obj.source, ServiceRequest.Source.USER)
        self.assertTrue(request_obj.reference.startswith("CSR-"))

    def test_creation_is_logged_as_first_history_entry(self):
        response = self.post_request(self.student)
        entries = RequestHistory.objects.filter(request_id=response.data["id"])
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().entry_type, RequestHistory.EntryType.CREATED)

    def test_authentication_required(self):
        response = self.client.post(REQUESTS_URL, {"title": "x"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VisibilityTests(RequestWorkflowBase):
    def test_student_list_contains_only_own_requests(self):
        mine = self.create_request(self.student)
        self.create_request(self.other_student)

        self.client.force_authenticate(user=self.student)
        response = self.client.get(REQUESTS_URL)
        ids = [item["id"] for item in response.data]
        self.assertEqual(ids, [mine.pk])

    def test_staff_sees_all_requests(self):
        self.create_request(self.student)
        self.create_request(self.other_student)

        self.client.force_authenticate(user=self.staff)
        response = self.client.get(REQUESTS_URL)
        self.assertEqual(len(response.data), 2)

    def test_student_cannot_read_another_students_request_by_id(self):
        other = self.create_request(self.other_student)
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f"{REQUESTS_URL}{other.pk}/")
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )

    def test_list_filters(self):
        self.create_request(self.student, priority=ServiceRequest.Priority.HIGH)
        self.create_request(self.student, title="Cleaning job")

        self.client.force_authenticate(user=self.staff)
        response = self.client.get(REQUESTS_URL, {"priority": "HIGH"})
        self.assertEqual(len(response.data), 1)
        response = self.client.get(REQUESTS_URL, {"status": "PENDING"})
        self.assertEqual(len(response.data), 2)


class StatusWorkflowTests(RequestWorkflowBase):
    def setUp(self):
        super().setUp()
        self.request_obj = self.create_request(self.student)
        self.status_url = f"{REQUESTS_URL}{self.request_obj.pk}/status/"

    def test_only_staff_can_change_status(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(self.status_url, {"status": "ASSIGNED"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_transition_assign_in_progress_resolve(self):
        self.client.force_authenticate(user=self.staff)
        for next_status in ("ASSIGNED", "IN_PROGRESS", "RESOLVED"):
            response = self.client.patch(self.status_url, {"status": next_status})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.request_obj.refresh_from_db()
            self.assertEqual(self.request_obj.status, next_status)

    def test_invalid_transition_rejected(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(self.status_url, {"status": "RESOLVED"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, ServiceRequest.Status.PENDING)

    def test_each_change_is_logged_with_comment(self):
        self.client.force_authenticate(user=self.staff)
        self.client.patch(self.status_url, {"status": "ASSIGNED", "comment": "Taking this one."})

        entry = RequestHistory.objects.filter(
            request=self.request_obj, entry_type=RequestHistory.EntryType.STATUS
        ).get()
        self.assertEqual(entry.from_status, ServiceRequest.Status.PENDING)
        self.assertEqual(entry.to_status, ServiceRequest.Status.ASSIGNED)
        self.assertEqual(entry.comment, "Taking this one.")
        self.assertEqual(entry.changed_by, self.staff)


class AssignmentTests(RequestWorkflowBase):
    def setUp(self):
        super().setUp()
        self.request_obj = self.create_request(self.student)
        self.assign_url = f"{REQUESTS_URL}{self.request_obj.pk}/assign/"

    def test_assignment_moves_pending_to_assigned_and_logs(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(self.assign_url, {"assigned_to": self.staff.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.assigned_to, self.staff)
        self.assertEqual(self.request_obj.status, ServiceRequest.Status.ASSIGNED)
        self.assertTrue(
            RequestHistory.objects.filter(
                request=self.request_obj, entry_type=RequestHistory.EntryType.ASSIGN
            ).exists()
        )

    def test_cannot_assign_to_a_student(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(self.assign_url, {"assigned_to": self.student.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.request_obj.refresh_from_db()
        self.assertIsNone(self.request_obj.assigned_to)

    def test_student_cannot_assign(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.assign_url, {"assigned_to": self.staff.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CommentsAndHistoryTests(RequestWorkflowBase):
    def setUp(self):
        super().setUp()
        self.request_obj = self.create_request(self.student)

    def test_owner_can_comment_and_comment_appears_in_history(self):
        self.client.force_authenticate(user=self.student)
        url = f"{REQUESTS_URL}{self.request_obj.pk}/updates/"
        response = self.client.post(url, {"comment": "Any update on this?"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        history_response = self.client.get(f"{REQUESTS_URL}{self.request_obj.pk}/history/")
        comments = [e for e in history_response.data if e["entry_type"] == "COMMENT"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["changed_by"]["username"], "naledi")

    def test_other_student_cannot_comment_or_read_history(self):
        self.client.force_authenticate(user=self.other_student)
        comment_response = self.client.post(
            f"{REQUESTS_URL}{self.request_obj.pk}/updates/", {"comment": "hi"}
        )
        history_response = self.client.get(f"{REQUESTS_URL}{self.request_obj.pk}/history/")
        self.assertEqual(comment_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(history_response.status_code, status.HTTP_403_FORBIDDEN)


class EditAndCancelTests(RequestWorkflowBase):
    def setUp(self):
        super().setUp()
        self.request_obj = self.create_request(self.student)

    def test_owner_edits_own_pending_request(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f"{REQUESTS_URL}{self.request_obj.pk}/", {"location": "Library, 2nd floor"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.location, "Library, 2nd floor")

    def test_owner_cannot_edit_once_work_started(self):
        self.request_obj.status = ServiceRequest.Status.IN_PROGRESS
        self.request_obj.save()

        self.client.force_authenticate(user=self.student)
        response = self.client.patch(f"{REQUESTS_URL}{self.request_obj.pk}/", {"location": "x"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_cancel_pending_request(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.delete(f"{REQUESTS_URL}{self.request_obj.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, ServiceRequest.Status.CANCELLED)

    def test_resolved_request_cannot_be_cancelled(self):
        self.request_obj.status = ServiceRequest.Status.RESOLVED
        self.request_obj.save()

        self.client.force_authenticate(user=self.staff)
        response = self.client.delete(f"{REQUESTS_URL}{self.request_obj.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CategoryTests(RequestWorkflowBase):
    def test_any_user_can_list_categories(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_admin_creates_categories(self):
        for user, expected in (
            (self.student, status.HTTP_403_FORBIDDEN),
            (self.staff, status.HTTP_403_FORBIDDEN),
            (self.admin, status.HTTP_201_CREATED),
        ):
            self.client.force_authenticate(user=user)
            response = self.client.post("/api/categories/", {"name": f"Cat {user.username}"})
            self.assertEqual(
                response.status_code,
                expected,
                f"{user}: {getattr(response, 'data', None)}",
            )
