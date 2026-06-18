from django.utils import timezone
from rest_framework import serializers

from .models import Review, ReviewComment


class ReviewCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewComment
        fields = [
            "id", "review", "diff_file", "commit_sha",
            "line_position", "body", "created_at",
            "is_resolved", "parent",
        ]
        read_only_fields = ["id", "review", "created_at", "is_resolved"]


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = serializers.ReadOnlyField(source="reviewer.username")
    comments = ReviewCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = ["id", "pr", "reviewer", "status", "submitted_at", "comments"]
        read_only_fields = ["id", "pr", "reviewer", "submitted_at", "comments"]


class SubmitReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[Review.Status.APPROVED, Review.Status.CHANGES_REQUESTED]
    )

    def create(self, validated_data):
        pr = self.context["pr"]
        user = self.context["request"].user
        review, _ = Review.objects.get_or_create(pr=pr, reviewer=user)
        review.status = validated_data["status"]
        review.submitted_at = timezone.now()
        review.save()
        return review
