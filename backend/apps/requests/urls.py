from django.urls import path

from .views import (
    CategoryListCreateView,
    RequestAssignView,
    RequestDetailView,
    RequestHistoryView,
    RequestListCreateView,
    RequestStatusView,
    RequestUpdatesView,
)

urlpatterns = [
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("requests/", RequestListCreateView.as_view(), name="request-list"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request-detail"),
    path("requests/<int:pk>/status/", RequestStatusView.as_view(), name="request-status"),
    path("requests/<int:pk>/assign/", RequestAssignView.as_view(), name="request-assign"),
    path("requests/<int:pk>/updates/", RequestUpdatesView.as_view(), name="request-updates"),
    path("requests/<int:pk>/history/", RequestHistoryView.as_view(), name="request-history"),
]
