"""
Workflow helpers shared by the request endpoints and the telemetry service.

All status changes go through apply_status() and all assignments through
assign_request(), so the transition rules, history entries and notifications
behave identically no matter which endpoint triggered them.
"""

from django.db import transaction

from apps.core.permissions import ADMIN, STAFF

from .models import Notification, RequestHistory, ServiceRequest


class WorkflowError(Exception):
    """Raised when an action would break the PENDING → ... → RESOLVED flow."""


# Which statuses a request may move to from its current one. Cancelling is
# allowed while work has not finished; resolved and cancelled are terminal.
ALLOWED_TRANSITIONS = {
    ServiceRequest.Status.PENDING: {
        ServiceRequest.Status.ASSIGNED,
        ServiceRequest.Status.CANCELLED,
    },
    ServiceRequest.Status.ASSIGNED: {
        ServiceRequest.Status.IN_PROGRESS,
        ServiceRequest.Status.CANCELLED,
    },
    ServiceRequest.Status.IN_PROGRESS: {
        ServiceRequest.Status.RESOLVED,
        ServiceRequest.Status.CANCELLED,
    },
    ServiceRequest.Status.RESOLVED: set(),
    ServiceRequest.Status.CANCELLED: set(),
}


def log_entry(request_obj, entry_type, changed_by=None, from_status="", to_status="", comment=""):
    """Append one line to the request's timeline."""
    return RequestHistory.objects.create(
        request=request_obj,
        entry_type=entry_type,
        changed_by=changed_by,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
    )


def notify_users(users, title, message, request_obj=None):
    """Create a notification for each user, ignoring duplicates in the list."""
    seen = set()
    for user in users:
        if user is None or user.pk in seen:
            continue
        seen.add(user.pk)
        Notification.objects.create(user=user, title=title, message=message, request=request_obj)


def apply_status(request_obj, new_status, actor=None, comment=""):
    """
    Move a request to new_status after checking the transition is legal.
    Raises WorkflowError with a readable message when it is not.
    """
    current = request_obj.status
    if new_status == current:
        raise WorkflowError(f"The request is already {current}.")
    if new_status not in ALLOWED_TRANSITIONS[current]:
        allowed = ", ".join(sorted(ALLOWED_TRANSITIONS[current])) or "none"
        raise WorkflowError(f"A request cannot move from {current} to {new_status} (allowed: {allowed}).")

    request_obj.status = new_status
    request_obj.save(update_fields=["status", "updated_at"])
    log_entry(
        request_obj,
        RequestHistory.EntryType.STATUS,
        changed_by=actor,
        from_status=current,
        to_status=new_status,
        comment=comment,
    )

    watchers = [request_obj.created_by, request_obj.assigned_to]
    label = request_obj.get_status_display()
    notify_users(
        watchers,
        f"{request_obj.reference} is now {label}",
        comment or f"Status changed from {current} to {new_status}.",
        request_obj=request_obj,
    )
    return request_obj


def assign_request(request_obj, target_user, actor=None):
    """
    Give a request to a staff member or admin. A pending request moves to
    ASSIGNED as part of the assignment; later statuses stay untouched so a
    reassignment does not rewind progress.
    """
    if target_user.role not in (STAFF, ADMIN) and not target_user.is_superuser:
        raise WorkflowError("Requests can only be assigned to staff or admin accounts.")

    previous = request_obj.assigned_to
    from_status = request_obj.status
    if request_obj.status == ServiceRequest.Status.PENDING:
        request_obj.status = ServiceRequest.Status.ASSIGNED

    request_obj.assigned_to = target_user
    request_obj.save(update_fields=["assigned_to", "status", "updated_at"])

    action = "Assigned" if previous is None else "Reassigned"
    log_entry(
        request_obj,
        RequestHistory.EntryType.ASSIGN,
        changed_by=actor,
        from_status=from_status,
        to_status=request_obj.status,
        comment=f"{action} to {target_user.get_full_name() or target_user.username}.",
    )

    notify_users(
        [target_user],
        f"{request_obj.reference} assigned to you",
        f"{request_obj.title} at {request_obj.location}.",
        request_obj=request_obj,
    )
    if request_obj.created_by and request_obj.created_by != target_user:
        notify_users(
            [request_obj.created_by],
            f"{request_obj.reference} has been taken on",
            f"{action} to {target_user.get_full_name() or target_user.username}.",
            request_obj=request_obj,
        )
    return request_obj


@transaction.atomic
def cancel(request_obj, actor=None, comment=""):
    """Cancel a request that has not been resolved yet."""
    return apply_status(
        request_obj,
        ServiceRequest.Status.CANCELLED,
        actor=actor,
        comment=comment or "Request cancelled.",
    )
