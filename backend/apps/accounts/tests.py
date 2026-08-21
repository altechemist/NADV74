"""
Tests for registration, login/logout, profile access and admin user
management. The security-critical behaviour here is that public signup can
never produce a staff or admin account.
"""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"
USERS_URL = "/api/users/"

STRONG_PASSWORD = "S0l-Plaatje#2026"


class RegistrationTests(APITestCase):
    def payload(self, **overrides):
        data = {
            "username": "naledi",
            "email": "naledi@student.spu.ac.za",
            "first_name": "Naledi",
            "last_name": "Khumalo",
            "password": STRONG_PASSWORD,
        }
        data.update(overrides)
        return data

    def test_registration_creates_student_account(self):
        response = self.client.post(REGISTER_URL, self.payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="naledi")
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_registration_ignores_submitted_role(self):
        # A client trying to escalate privileges by posting role=ADMIN must
        # still end up with a student account.
        response = self.client.post(REGISTER_URL, self.payload(role=User.Role.ADMIN))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username="naledi").role, User.Role.STUDENT)

    def test_duplicate_username_rejected(self):
        self.client.post(REGISTER_URL, self.payload())
        response = self.client.post(REGISTER_URL, self.payload(email="other@spu.ac.za"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        response = self.client.post(REGISTER_URL, self.payload(password="12345678"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="naledi").exists())

    def test_password_is_hashed_not_stored_plain(self):
        self.client.post(REGISTER_URL, self.payload())
        user = User.objects.get(username="naledi")
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_"))


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="lerato",
            password=STRONG_PASSWORD,
            first_name="Lerato",
            role=User.Role.STAFF,
        )

    def login(self, username="lerato", password=STRONG_PASSWORD):
        return self.client.post(LOGIN_URL, {"username": username, "password": password})

    def test_login_returns_tokens_and_profile(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], "STAFF")

    def test_login_with_wrong_password_fails(self):
        response = self.login(password="not-the-password")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_exchanges_tokens(self):
        refresh = self.login().data["refresh"]
        response = self.client.post(REFRESH_URL, {"refresh": refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_logout_blacklists_refresh_token(self):
        refresh = self.login().data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login().data['access']}")
        response = self.client.post(LOGOUT_URL, {"refresh": refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The blacklisted token may no longer be exchanged.
        response = self.client.post(REFRESH_URL, {"refresh": refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_and_updates_profile(self):
        access = self.login().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get(ME_URL)
        self.assertEqual(response.data["username"], "lerato")

        response = self.client.put(ME_URL, {"first_name": "Lerato", "last_name": "Mokoena", "email": "lerato@spu.ac.za"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "Mokoena")


class UserManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password=STRONG_PASSWORD, role=User.Role.ADMIN
        )
        self.staff = User.objects.create_user(
            username="lerato", password=STRONG_PASSWORD, role=User.Role.STAFF
        )
        self.student = User.objects.create_user(
            username="naledi", password=STRONG_PASSWORD, role=User.Role.STUDENT
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_list_users_admin_only(self):
        for user, expected in (
            (self.student, status.HTTP_403_FORBIDDEN),
            (self.staff, status.HTTP_403_FORBIDDEN),
            (self.admin, status.HTTP_200_OK),
        ):
            self.authenticate(user)
            response = self.client.get(USERS_URL)
            self.assertEqual(response.status_code, expected)

    def test_admin_can_create_staff_account(self):
        self.authenticate(self.admin)
        response = self.client.post(
            USERS_URL,
            {
                "username": "newstaff",
                "password": STRONG_PASSWORD,
                "role": User.Role.STAFF,
                "email": "newstaff@spu.ac.za",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username="newstaff").role, User.Role.STAFF)

    def test_delete_deactivates_instead_of_removing(self):
        self.authenticate(self.admin)
        response = self.client.delete(f"{USERS_URL}{self.staff.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assertTrue(User.objects.filter(username="lerato").exists())
