from rest_framework import viewsets, status, generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasRolePermission
from .models import ActivityLog,Notification
from .serializers import ActivityLogSerializer,NotificationSerializer
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for audit logs.
    No create, update or delete operations are allowed.
    """

    queryset = ActivityLog.objects.select_related("user").order_by("-created_at")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated,HasRolePermission]
    permission_code = "activity_log.view"

class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Notification.objects
            .filter(recipient=self.request.user)
            .order_by("-created_at")
        )

        is_read = self.request.query_params.get("is_read")
        priority = self.request.query_params.get("priority")
        notification_type = self.request.query_params.get(
            "notification_type"
        )

        if is_read is not None:
            if is_read.lower() not in {"true", "false"}:
                return Notification.objects.none()

            queryset = queryset.filter(
                is_read=is_read.lower() == "true"
            )

        if priority:
            queryset = queryset.filter(priority=priority)

        if notification_type:
            queryset = queryset.filter(
                notification_type=notification_type
            )

        return queryset


class NotificationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        )


class NotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user,
            )
        except Notification.DoesNotExist as exc:
            raise NotFound("Notification not found.") from exc

        notification.mark_as_read()

        return Response(
            {
                "message": "Notification marked as read",
            },
            status=status.HTTP_200_OK,
        )


class NotificationReadAllAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request):
        now = timezone.now()

        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(
            is_read=True,
            read_at=now,
            updated_at=now,
        )

        return Response(
            {
                "message": "All notifications marked as read",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class NotificationUnreadCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        return Response(
            {
                "count": count,
            },
            status=status.HTTP_200_OK,
        )
