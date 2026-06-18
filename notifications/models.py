from django.conf import settings
from django.db import models


class Notification(models.Model):
    class EventType(models.TextChoices):
        REVIEW_SUBMITTED = "review_submitted", "Review Submitted"
        COMMENT_ADDED = "comment_added", "Comment Added"
        PR_STATE_CHANGED = "pr_state_changed", "PR State Changed"
        COMMENT_RESOLVED = "comment_resolved", "Comment Resolved"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="triggered_notifications",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} → {self.recipient.username}"
