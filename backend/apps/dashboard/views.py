"""Dashboard summary counts and the user's notification feed."""
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import has_role
from apps.requests.models import Notification, ServiceRequest
from apps.requests.serializers import NotificationSerializer


class DashboardSummaryView(APIView):
    """
    Status counts for the dashboard cards. Students get counts over their
    own requests; staff and admins see the whole campus.
    """

    def get(self, request):
        queryset = ServiceRequest.objects.all()
        if not has_role(request.user, "STAFF", "ADMIN"):
            queryset = queryset.filter(created_by=request.user)

        return Response(
            {
                "pending": queryset.filter(status=ServiceRequest.Status.PENDING).count(),
                "assigned": queryset.filter(status=ServiceRequest.Status.ASSIGNED).count(),
                "in_progress": queryset.filter(status=ServiceRequest.Status.IN_PROGRESS).count(),
                "resolved": queryset.filter(status=ServiceRequest.Status.RESOLVED).count(),
            }
        )


class NotificationListView(generics.ListAPIView):
    """The signed-in user's notifications, newest first."""

    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
