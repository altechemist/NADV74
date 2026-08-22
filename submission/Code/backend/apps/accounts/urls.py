from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    StaffDirectoryView,
    UserViewSet,
)

user_detail = UserViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("users/", UserViewSet.as_view({"get": "list", "post": "create"}), name="user-list"),
    # declared before the pk route so "staff" is never read as an id
    path("users/staff/", StaffDirectoryView.as_view(), name="user-staff"),
    path("users/<int:pk>/", user_detail, name="user-detail"),
]
