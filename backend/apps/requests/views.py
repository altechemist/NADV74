"""
Request endpoints: listing/creation, detail, status changes, assignment,
comments and the full history timeline.
"""
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin, IsOwnerOrStaffOrAdmin, IsStaffOrAdmin, has_role

from .models import Category, RequestHistory, ServiceRequest
from .serializers import (
    AssignRequestSerializer,
    CategorySerializer,
    CommentSerializer,
    RequestHistorySerializer,
    RequestStatusSerializer,
    ServiceRequestSerializer,
)
from .services import WorkflowError, apply_status, assign_request, cancel, log_entry

User = get_user_model()


def _workflow_error_response(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class CategoryListCreateView(generics.ListCreateAPIView):
    """Any signed-in user can list categories; only admins may add new ones."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return super().get_permissions()


class RequestListCreateView(generics.ListCreateAPIView):
    """
    Students see and create their own requests; staff and admins see the
    whole queue. Staff can narrow the list with ?status=, ?priority= and
    ?category= (category id).
    """

    serializer_class = ServiceRequestSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = ServiceRequest.objects.select_related("category", "created_by", "assigned_to")
        if not has_role(user, "STAFF", "ADMIN"):
            queryset = queryset.filter(created_by=user)

        params = self.request.query_params
        if status_filter := params.get("status"):
            queryset = queryset.filter(status=status_filter.upper())
        if priority := params.get("priority"):
            queryset = queryset.filter(priority=priority.upper())
        if category := params.get("category"):
            queryset = queryset.filter(category_id=category)
        return queryset

    def perform_create(self, serializer):
        request_obj = serializer.save(created_by=self.request.user, source=ServiceRequest.Source.USER)
        # The creation itself is the first line of the audit trail.
        log_entry(
            request_obj,
            RequestHistory.EntryType.CREATED,
            changed_by=self.request.user,
            to_status=request_obj.status,
            comment="Request logged.",
        )


class RequestDetailView(APIView):
    """
    Retrieve, edit or cancel one request. Students may only touch their own
    tickets and only while they are still PENDING; staff and admins have no
    such limits. Deleting is implemented as cancelling so the record stays
    available for reporting.
    """

    permission_classes = [IsOwnerOrStaffOrAdmin]

    def get_object(self, pk):
        obj = get_object_or_404(ServiceRequest.objects.select_related("category", "created_by", "assigned_to"), pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, pk):
        return Response(ServiceRequestSerializer(self.get_object(pk)).data)

    def put(self, request, pk):
        return self._update(request, pk)

    def patch(self, request, pk):
        return self._update(request, pk)

    def _update(self, request, pk):
        request_obj = self.get_object(pk)
        if not has_role(request.user, "STAFF", "ADMIN") and request_obj.status != ServiceRequest.Status.PENDING:
            return Response(
                {"detail": "Only pending requests can be edited. Ask the service desk instead."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ServiceRequestSerializer(request_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        request_obj = self.get_object(pk)
        try:
            cancel(request_obj, actor=request.user)
        except WorkflowError as exc:
            return _workflow_error_response(exc)
        return Response(ServiceRequestSerializer(request_obj).data)


class RequestStatusView(APIView):
    """Staff/admin move a request along its workflow; every move is logged."""

    permission_classes = [IsStaffOrAdmin]

    def patch(self, request, pk):
        request_obj = get_object_or_404(ServiceRequest, pk=pk)
        serializer = RequestStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            apply_status(
                request_obj,
                serializer.validated_data["status"],
                actor=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except WorkflowError as exc:
            return _workflow_error_response(exc)
        return Response(ServiceRequestSerializer(request_obj).data)


class RequestAssignView(APIView):
    """Staff/admin hand a request to a colleague or themselves."""

    permission_classes = [IsStaffOrAdmin]

    def post(self, request, pk):
        request_obj = get_object_or_404(ServiceRequest, pk=pk)
        serializer = AssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = get_object_or_404(User, pk=serializer.validated_data["assigned_to"])
        try:
            assign_request(request_obj, target, actor=request.user)
        except WorkflowError as exc:
            return _workflow_error_response(exc)
        return Response(ServiceRequestSerializer(request_obj).data)


class RequestUpdatesView(APIView):
    """Anyone who can see a request may comment on it."""

    permission_classes = [IsOwnerOrStaffOrAdmin]

    def post(self, request, pk):
        request_obj = get_object_or_404(ServiceRequest, pk=pk)
        self.check_object_permissions(request, request_obj)
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = log_entry(
            request_obj,
            RequestHistory.EntryType.COMMENT,
            changed_by=request.user,
            comment=serializer.validated_data["comment"],
        )
        return Response(RequestHistorySerializer(entry).data, status=status.HTTP_201_CREATED)


class RequestHistoryView(APIView):
    """Full timeline: creation, assignments, status changes and comments."""

    permission_classes = [IsOwnerOrStaffOrAdmin]

    def get(self, request, pk):
        request_obj = get_object_or_404(ServiceRequest, pk=pk)
        self.check_object_permissions(request, request_obj)
        entries = request_obj.history.select_related("changed_by")
        return Response(RequestHistorySerializer(entries, many=True).data)
