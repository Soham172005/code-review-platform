from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ReviewComment


class CommentResolveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            comment = ReviewComment.objects.get(pk=pk)
        except ReviewComment.DoesNotExist:
            return Response(
                {"detail": "Comment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        comment.is_resolved = not comment.is_resolved
        comment.save(update_fields=["is_resolved"])
        return Response({
            "id": comment.id,
            "is_resolved": comment.is_resolved,
        })
