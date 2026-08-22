"""Shared permission classes used across the CSRMS services.

Roles are stored on the user record (see accounts.User). The strings below
mirror accounts.User.Role; keeping the checks here means every service
enforces access in exactly the same way.
"""

from rest_framework.permissions import BasePermission

STUDENT = "STUDENT"
STAFF = "STAFF"
ADMIN = "ADMIN"


def has_role(user, *roles):
    """True when the requester is authenticated and holds one of the roles."""
    if user is None or not user.is_authenticated:
        return False
    # Superusers are Django-level admins and always pass an admin check.
    if user.is_superuser:
        return True
    return getattr(user, "role", "") in roles


class IsAdmin(BasePermission):
    """Allows access only to ADMIN accounts."""

    def has_permission(self, request, view):
        return has_role(request.user, ADMIN)


class IsStaffOrAdmin(BasePermission):
    """Allows STAFF and ADMIN accounts through."""

    def has_permission(self, request, view):
        return has_role(request.user, STAFF, ADMIN)


class IsOwnerOrStaffOrAdmin(BasePermission):
    """
    Object-level guard for requests and their timelines: the student who
    logged the issue always sees their own ticket, while staff and admins
    can work with anything. This is what stops a student reading someone
    else's request by guessing its id.
    """

    def has_object_permission(self, request, view, obj):
        if has_role(request.user, STAFF, ADMIN):
            return True
        owner = getattr(obj, "created_by", None)
        return owner is not None and owner == request.user
