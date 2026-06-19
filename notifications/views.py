import json
import time

from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(
            recipient=self.request.user
        ).select_related("actor")
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        return qs


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk, recipient=request.user
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({"marked": count})


class NotificationStreamView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token_str = request.query_params.get("token", "")
        if not token_str:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            access_token = AccessToken(token_str)
            user_id = access_token["user_id"]
        except Exception:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        def event_stream():
            last_check = time.time()
            heartbeat_interval = 15
            poll_interval = 2

            while True:
                notifications = Notification.objects.filter(
                    recipient_id=user_id, is_read=False
                ).select_related("actor").order_by("-created_at")[:20]

                for n in notifications:
                    data = json.dumps({
                        "id": n.id,
                        "event_type": n.event_type,
                        "message": n.message,
                        "actor": n.actor.username,
                        "created_at": n.created_at.isoformat(),
                    })
                    yield f"data: {data}\n\n"
                    n.is_read = True
                    n.save(update_fields=["is_read"])

                now = time.time()
                if now - last_check >= heartbeat_interval:
                    yield ": heartbeat\n\n"
                    last_check = now

                time.sleep(poll_interval)

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["Access-Control-Allow-Origin"] = "http://localhost:5173"
        return response
