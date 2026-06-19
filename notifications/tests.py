import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.factories import NotificationFactory
from notifications.models import Notification
from users.factories import UserFactory


def auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def auth_client(user):
    return auth_client_for(user)


# ── List notifications ──────────────────────────────────────


@pytest.mark.django_db
class TestNotificationList:
    def test_list_own_notifications(self, auth_client, user):
        NotificationFactory(recipient=user)
        NotificationFactory(recipient=user)
        NotificationFactory()  # someone else's
        resp = auth_client.get("/api/notifications/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_filter_unread(self, auth_client, user):
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=True)
        resp = auth_client.get("/api/notifications/?unread=true")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_unauthenticated_list(self):
        client = APIClient()
        resp = client.get("/api/notifications/")
        assert resp.status_code == 401


# ── Mark read ───────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationMarkRead:
    def test_mark_read(self, auth_client, user):
        n = NotificationFactory(recipient=user, is_read=False)
        resp = auth_client.patch(f"/api/notifications/{n.pk}/read/")
        assert resp.status_code == 200
        assert resp.data["is_read"] is True
        n.refresh_from_db()
        assert n.is_read is True

    def test_cannot_mark_others_notification(self, auth_client, user):
        other = UserFactory()
        n = NotificationFactory(recipient=other)
        resp = auth_client.patch(f"/api/notifications/{n.pk}/read/")
        assert resp.status_code == 404

    def test_mark_nonexistent(self, auth_client):
        resp = auth_client.patch("/api/notifications/99999/read/")
        assert resp.status_code == 404


# ── Mark all read ───────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationMarkAllRead:
    def test_mark_all_read(self, auth_client, user):
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=True)
        resp = auth_client.post("/api/notifications/mark-all-read/")
        assert resp.status_code == 200
        assert resp.data["marked"] == 2
        assert Notification.objects.filter(recipient=user, is_read=False).count() == 0


# ── SSE stream ──────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationStream:
    def test_stream_requires_token(self):
        client = APIClient()
        resp = client.get("/api/notifications/stream/")
        assert resp.status_code == 401

    def test_stream_invalid_token(self):
        client = APIClient()
        resp = client.get("/api/notifications/stream/?token=invalid")
        assert resp.status_code == 401

    def test_stream_returns_event_stream(self, user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)
        resp = client.get(f"/api/notifications/stream/?token={token}")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/event-stream"


# ── Signals fire tasks ──────────────────────────────────────


@pytest.mark.django_db
class TestNotificationSignals:
    def test_comment_creates_notification(self, user):
        from repos.factories import CommitFactory, DiffFileFactory, PullRequestFactory
        from reviews.models import ReviewComment, Review
        from users.factories import ReviewerFactory

        reviewer = ReviewerFactory()
        pr = PullRequestFactory(author=user)
        commit = CommitFactory(pr=pr, author=user)
        diff_file = DiffFileFactory(commit=commit)
        review = Review.objects.create(pr=pr, reviewer=reviewer)

        ReviewComment.objects.create(
            review=review,
            diff_file=diff_file,
            commit_sha=commit.sha,
            line_position=1,
            body="Test comment",
        )

        assert Notification.objects.filter(
            recipient=user,
            event_type="comment_added",
        ).exists()

    def test_review_creates_notification(self, user):
        from repos.factories import PullRequestFactory
        from reviews.models import Review
        from users.factories import ReviewerFactory
        from django.utils import timezone

        reviewer = ReviewerFactory()
        pr = PullRequestFactory(author=user)
        review = Review.objects.create(pr=pr, reviewer=reviewer)
        review.status = "approved"
        review.submitted_at = timezone.now()
        review.save()

        assert Notification.objects.filter(
            recipient=user,
            event_type="review_submitted",
        ).exists()

    def test_transition_creates_notification(self, user):
        from repos.factories import PullRequestFactory
        from repos.models import PRTransitionHistory
        from users.factories import ReviewerFactory

        other_user = ReviewerFactory()
        pr = PullRequestFactory(author=user)

        PRTransitionHistory.objects.create(
            pr=pr,
            from_status="draft",
            to_status="open",
            actor=other_user,
        )

        assert Notification.objects.filter(
            recipient=user,
            event_type="pr_state_changed",
        ).exists()

    def test_no_self_notification(self):
        from repos.factories import CommitFactory, DiffFileFactory, PullRequestFactory
        from reviews.models import ReviewComment, Review
        from users.factories import ReviewerFactory

        author = ReviewerFactory()
        pr = PullRequestFactory(author=author)
        commit = CommitFactory(pr=pr, author=author)
        diff_file = DiffFileFactory(commit=commit)
        review = Review.objects.create(pr=pr, reviewer=author)

        ReviewComment.objects.create(
            review=review,
            diff_file=diff_file,
            commit_sha=commit.sha,
            line_position=1,
            body="Self comment",
        )

        assert not Notification.objects.filter(recipient=author).exists()
