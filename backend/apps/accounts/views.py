"""Authentication and user-management endpoints."""
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import IsAdmin

from .models import User
from .serializers import (
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserManageSerializer,
    UserSerializer,
)


class LoginSerializer(TokenObtainPairSerializer):
    """Standard JWT pair plus the profile so the frontend can greet the user."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_scope = "auth"
    permission_classes = [AllowAny]


class RegisterView(generics.CreateAPIView):
    """Public sign-up. Always produces a STUDENT account."""

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_scope = "auth"


class LogoutView(APIView):
    """Blacklist the supplied refresh token so it can no longer be exchanged."""

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "A refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response(
                {"detail": "The refresh token is invalid or already used."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Logged out."})


class MeView(APIView):
    """Read and update the logged-in user's own profile."""

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        return self.put(request)


class UserViewSet(viewsets.ModelViewSet):
    """
    Admin management of accounts. Deleting a user deactivates the account
    rather than removing it, which keeps the audit trail on old requests
    intact.
    """

    queryset = User.objects.all().order_by("username")
    serializer_class = UserManageSerializer
    permission_classes = [IsAdmin]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
