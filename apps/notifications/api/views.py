from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.services.notification_service import notification_payload
from core.models import UserNotification


class MobileNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = UserNotification.objects.filter(
            user=request.user,
            is_read=False,
        ).order_by("-created_at")
        notifications = queryset[:20]
        return Response(
            {
                "count": queryset.count(),
                "notifications": [
                    notification_payload(notification)
                    for notification in notifications
                ],
            }
        )


class MobileNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        UserNotification.objects.filter(id=pk, user=request.user).update(
            is_read=True
        )
        return Response({"status": "success"})
