from django.urls import path

from .views import DashboardSummaryView, NotificationListView

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
]
