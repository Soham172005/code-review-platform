from django.conf import settings
from django.db import models
from django_fsm import FSMField, transition


class Repository(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="repositories",
    )
    github_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "repositories"
        unique_together = [("owner", "name")]

    def __str__(self):
        return f"{self.owner.username}/{self.name}"


class PullRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        MERGED = "merged", "Merged"
        CLOSED = "closed", "Closed"

    TRANSITION_MAP = {
        "open_pr": "open_pr",
        "submit_for_review": "submit_for_review",
        "approve": "approve",
        "merge": "merge",
        "close": "close",
        "reopen": "reopen",
    }

    repo = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="pull_requests",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pull_requests",
    )
    base_branch = models.CharField(max_length=255)
    head_branch = models.CharField(max_length=255)
    status = FSMField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PR #{self.pk}: {self.title}"

    @transition(field=status, source=Status.DRAFT, target=Status.OPEN)
    def open_pr(self):
        pass

    @transition(field=status, source=Status.OPEN, target=Status.IN_REVIEW)
    def submit_for_review(self):
        pass

    @transition(field=status, source=Status.IN_REVIEW, target=Status.APPROVED)
    def approve(self):
        pass

    @transition(field=status, source=Status.APPROVED, target=Status.MERGED)
    def merge(self):
        pass

    @transition(
        field=status,
        source=[Status.DRAFT, Status.OPEN, Status.IN_REVIEW, Status.APPROVED],
        target=Status.CLOSED,
    )
    def close(self):
        pass

    @transition(field=status, source=Status.CLOSED, target=Status.OPEN)
    def reopen(self):
        pass


class PRTransitionHistory(models.Model):
    pr = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="transition_history",
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pr_transitions",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"PR #{self.pr_id}: {self.from_status} → {self.to_status}"


class Commit(models.Model):
    pr = models.ForeignKey(
        PullRequest,
        on_delete=models.CASCADE,
        related_name="commits",
    )
    sha = models.CharField(max_length=40)
    message = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commits",
    )
    committed_at = models.DateTimeField()

    class Meta:
        unique_together = [("pr", "sha")]

    def __str__(self):
        return f"{self.sha[:7]} — {self.message[:60]}"


class DiffFile(models.Model):
    class ChangeType(models.TextChoices):
        ADDED = "added", "Added"
        MODIFIED = "modified", "Modified"
        DELETED = "deleted", "Deleted"

    commit = models.ForeignKey(
        Commit,
        on_delete=models.CASCADE,
        related_name="diff_files",
    )
    file_path = models.CharField(max_length=1024)
    change_type = models.CharField(max_length=10, choices=ChangeType.choices)
    patch = models.JSONField(default=list)

    def __str__(self):
        return f"{self.change_type} {self.file_path}"
