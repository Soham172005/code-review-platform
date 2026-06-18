from django.conf import settings
from django.db import models

from repos.models import DiffFile, PullRequest


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"

    pr = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("pr", "reviewer")]

    def __str__(self):
        return f"Review by {self.reviewer} on PR #{self.pr_id} — {self.status}"


class ReviewComment(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    diff_file = models.ForeignKey(
        DiffFile,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    commit_sha = models.CharField(max_length=40)
    line_position = models.IntegerField()
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    def __str__(self):
        return f"Comment on {self.diff_file.file_path}:{self.line_position}"
