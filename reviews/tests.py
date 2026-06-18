import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from repos.factories import CommitFactory, DiffFileFactory, PullRequestFactory
from reviews.factories import ReviewCommentFactory, ReviewFactory
from reviews.models import Review, ReviewComment
from users.factories import AdminFactory, ReviewerFactory, UserFactory


def auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def reviewer():
    return ReviewerFactory()


@pytest.fixture
def author():
    return UserFactory()


@pytest.fixture
def admin_user():
    return AdminFactory()


# ── Submit review ─────────────────────────────────────────────


@pytest.mark.django_db
class TestSubmitReview:
    def test_submit_review_approved(self, reviewer):
        pr = PullRequestFactory()
        client = auth_client_for(reviewer)
        resp = client.post(f"/api/prs/{pr.pk}/reviews/", {"status": "approved"})
        assert resp.status_code == 200
        assert resp.data["status"] == "approved"
        assert resp.data["submitted_at"] is not None

    def test_submit_review_changes_requested(self, reviewer):
        pr = PullRequestFactory()
        client = auth_client_for(reviewer)
        resp = client.post(
            f"/api/prs/{pr.pk}/reviews/",
            {"status": "changes_requested"},
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "changes_requested"

    def test_author_cannot_submit_review(self, author):
        pr = PullRequestFactory(author=author, repo__owner=author)
        client = auth_client_for(author)
        resp = client.post(f"/api/prs/{pr.pk}/reviews/", {"status": "approved"})
        assert resp.status_code == 403

    def test_admin_can_submit_review(self, admin_user):
        pr = PullRequestFactory()
        client = auth_client_for(admin_user)
        resp = client.post(f"/api/prs/{pr.pk}/reviews/", {"status": "approved"})
        assert resp.status_code == 200

    def test_resubmit_updates_existing_review(self, reviewer):
        pr = PullRequestFactory()
        client = auth_client_for(reviewer)
        client.post(f"/api/prs/{pr.pk}/reviews/", {"status": "approved"})
        resp = client.post(
            f"/api/prs/{pr.pk}/reviews/",
            {"status": "changes_requested"},
        )
        assert resp.status_code == 200
        assert Review.objects.filter(pr=pr, reviewer=reviewer).count() == 1
        review = Review.objects.get(pr=pr, reviewer=reviewer)
        assert review.status == "changes_requested"

    def test_invalid_status(self, reviewer):
        pr = PullRequestFactory()
        client = auth_client_for(reviewer)
        resp = client.post(f"/api/prs/{pr.pk}/reviews/", {"status": "invalid"})
        assert resp.status_code == 400


# ── Inline comments ──────────────────────────────────────────


@pytest.mark.django_db
class TestInlineComments:
    def test_add_comment(self, reviewer):
        pr = PullRequestFactory()
        commit = CommitFactory(pr=pr)
        diff_file = DiffFileFactory(commit=commit)
        client = auth_client_for(reviewer)

        resp = client.post(f"/api/prs/{pr.pk}/comments/", {
            "diff_file": diff_file.pk,
            "commit_sha": commit.sha,
            "line_position": 10,
            "body": "This needs fixing",
        })
        assert resp.status_code == 201
        assert resp.data["body"] == "This needs fixing"
        assert resp.data["line_position"] == 10

    def test_comment_auto_creates_review(self, reviewer):
        pr = PullRequestFactory()
        commit = CommitFactory(pr=pr)
        diff_file = DiffFileFactory(commit=commit)
        client = auth_client_for(reviewer)

        assert not Review.objects.filter(pr=pr, reviewer=reviewer).exists()

        client.post(f"/api/prs/{pr.pk}/comments/", {
            "diff_file": diff_file.pk,
            "commit_sha": commit.sha,
            "line_position": 5,
            "body": "Comment",
        })

        assert Review.objects.filter(pr=pr, reviewer=reviewer).exists()

    def test_threaded_reply(self, reviewer):
        pr = PullRequestFactory()
        commit = CommitFactory(pr=pr)
        diff_file = DiffFileFactory(commit=commit)
        review = ReviewFactory(pr=pr, reviewer=reviewer)
        parent = ReviewCommentFactory(
            review=review, diff_file=diff_file,
            commit_sha=commit.sha,
        )
        client = auth_client_for(reviewer)

        resp = client.post(f"/api/prs/{pr.pk}/comments/", {
            "diff_file": diff_file.pk,
            "commit_sha": commit.sha,
            "line_position": parent.line_position,
            "body": "Reply to parent",
            "parent": parent.pk,
        })
        assert resp.status_code == 201
        assert resp.data["parent"] == parent.pk


# ── Comment resolve/unresolve ─────────────────────────────────


@pytest.mark.django_db
class TestCommentResolve:
    def test_resolve_comment(self, reviewer):
        comment = ReviewCommentFactory(review__reviewer=reviewer)
        client = auth_client_for(reviewer)
        resp = client.post(f"/api/reviews/comments/{comment.pk}/resolve/")
        assert resp.status_code == 200
        assert resp.data["is_resolved"] is True

    def test_unresolve_comment(self, reviewer):
        comment = ReviewCommentFactory(
            review__reviewer=reviewer, is_resolved=True,
        )
        client = auth_client_for(reviewer)
        resp = client.post(f"/api/reviews/comments/{comment.pk}/resolve/")
        assert resp.status_code == 200
        assert resp.data["is_resolved"] is False

    def test_toggle_resolve(self, reviewer):
        comment = ReviewCommentFactory(review__reviewer=reviewer)
        client = auth_client_for(reviewer)

        resp = client.post(f"/api/reviews/comments/{comment.pk}/resolve/")
        assert resp.data["is_resolved"] is True

        resp = client.post(f"/api/reviews/comments/{comment.pk}/resolve/")
        assert resp.data["is_resolved"] is False

    def test_resolve_nonexistent(self, reviewer):
        client = auth_client_for(reviewer)
        resp = client.post("/api/reviews/comments/99999/resolve/")
        assert resp.status_code == 404
