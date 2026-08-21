"""
Core domain models: service categories, service requests, the audit trail
attached to every request, and user notifications.
"""
from django.conf import settings
from django.db import models


class Category(models.Model):
    """A campus service area a request can be filed under."""

    name = models.CharField(max_length=120, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    """One reportable campus issue and where it sits in the workflow."""

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        RESOLVED = "RESOLVED", "Resolved"
        CANCELLED = "CANCELLED", "Cancelled"

    class Source(models.TextChoices):
        USER = "USER", "User"
        SYSTEM = "SYSTEM", "System"

    # Statuses that still need someone to act on them. Used to make sure an
    # ongoing problem does not spawn duplicate SYSTEM requests.
    OPEN_STATUSES = [Status.PENDING, Status.ASSIGNED, Status.IN_PROGRESS]

    reference = models.CharField(max_length=24, unique=True, blank=True)
    title = models.CharField(max_length=180)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="requests")
    location = models.CharField(max_length=180)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.USER)
    # SYSTEM requests have no human author, so the field is nullable.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_requests",
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_requests",
        null=True,
        blank=True,
    )
    # Identifies recurring problems (e.g. "fire:server-room") so repeated
    # sensor breaches update one open ticket instead of flooding the queue.
    dedupe_key = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # The public reference needs the primary key, so it is filled in
        # right after the first save.
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = f"CSR-{1000 + self.pk}"
            self.save(update_fields=["reference"])
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} · {self.title}"


class RequestHistory(models.Model):
    """
    Append-only timeline for a request. Every creation, assignment, status
    change and comment lands here, which gives students full visibility of
    progress and gives administrators an audit trail.
    """

    class EntryType(models.TextChoices):
        CREATED = "CREATED", "Created"
        STATUS = "STATUS", "Status change"
        ASSIGN = "ASSIGN", "Assignment"
        COMMENT = "COMMENT", "Comment"

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="history")
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    # Null when the system itself produced the entry (IoT auto-creation).
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="request_history_entries",
        null=True,
        blank=True,
    )
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.request.reference} · {self.entry_type} · {self.created_at:%Y-%m-%d %H:%M}"


class Notification(models.Model):
    """A short message shown to one user on their dashboard."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=160)
    message = models.TextField()
    request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.user.username}: {self.title}"
