from rest_framework import viewsets,status,generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from rest_framework.response import Response

from apps.accounts.permissions import HasRolePermission
from .models import ActivityLog,Notification
from .serializers import ActivityLogSerializer,NotificationSerializer
from rest_framework.views import APIView

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for audit logs.
    No create, update or delete operations are allowed.
    """

    queryset = ActivityLog.objects.select_related("user").order_by("-created_at")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated,HasRolePermission]

class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated,HasRolePermission]

    def get_queryset(self):
        return (
            Notification.objects
            .filter(recipient=self.request.user)
            .order_by("-created_at")
        )

class NotificationReadAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):

        try:
            notification = Notification.objects.get(
                id=pk,
                recipient=request.user
            )

        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        return Response(
            {
                "message": "Notification marked as read"
            },
            status=status.HTTP_200_OK
        )

    
class NotificationUnreadCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()

        return Response(
            {
                "count": count
            }
        )