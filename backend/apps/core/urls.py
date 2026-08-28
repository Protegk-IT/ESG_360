from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityLogViewSet,
    NotificationListAPIView,
    NotificationReadAPIView,
    NotificationReadAllAPIView,
    NotificationUnreadCountAPIView,
    NotificationDetailAPIView,
)
router = DefaultRouter()
router.register("activity-logs", ActivityLogViewSet, basename="activity-log")

urlpatterns = [
    path("", include(router.urls)),
    path("notifications/",NotificationListAPIView.as_view(),name="notification-list",),
    path("notifications/<uuid:pk>/",NotificationDetailAPIView.as_view(),name="notification-detail",),
    path("notifications/<uuid:pk>/read/",NotificationReadAPIView.as_view(),name="notification-read",),
    path("notifications/unread-count/",NotificationUnreadCountAPIView.as_view(),name="notification-unread-count",),
    path("notifications/read-all/", NotificationReadAllAPIView.as_view(),name="notification-read-all",),
    ]