"""Campus user model. The role field drives every permission decision."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A student, staff member or administrator of the service desk."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        STAFF = "STAFF", "Staff"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)

    class Meta:
        ordering = ["username"]

    @property
    def effective_role(self):
        # Superusers created with createsuperuser are administrators even
        # before their role field is updated.
        if self.is_superuser:
            return self.Role.ADMIN
        return self.role

    def __str__(self):
        return f"{self.username} ({self.effective_role})"
