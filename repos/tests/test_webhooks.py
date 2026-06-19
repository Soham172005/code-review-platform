import hashlib
import hmac
import json

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from repos.factories import PullRequestFactory, RepositoryFactory
from repos.models import Commit, PullRequest
from users.factories import UserFactory


def sign_payload(payload_bytes):
    secret = settings.GITHUB_WEBHOOK_SECRET.encode()
    sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def post_webhook(client, event_type, payload, signature=None):
    body = json.dumps(payload).encode()
    if signature is None:
        signature = sign_payload(body)
    return client.post(
        "/api/webhooks/github/",
        data=body,
        content_type="application/json",
        HTTP_X_GITHUB_EVENT=event_type,
        HTTP_X_HUB_SIGNATURE_256=signature,
    )


@pytest.fixture
def client():
    return APIClient()


# ── HMAC verification ───────────────────────────────────────


@pytest.mark.django_db
class TestWebhookHMAC:
    def test_valid_signature_accepted(self, client):
        resp = post_webhook(client, "ping", {"zen": "test"})
        assert resp.status_code == 200

    def test_invalid_signature_rejected(self, client):
        body = json.dumps({"zen": "test"}).encode()
        resp = post_webhook(client, "ping", {"zen": "test"}, signature="sha256=bad")
        assert resp.status_code == 403

    def test_missing_signature_rejected(self, client):
        resp = client.post(
            "/api/webhooks/github/",
            data=json.dumps({"zen": "test"}),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="ping",
        )
        assert resp.status_code == 400


# ── Push event handler ──────────────────────────────────────


@pytest.mark.django_db
class TestWebhookPush:
    def test_push_creates_commits(self, client):
        user = UserFactory(github_username="ghuser")
        repo = RepositoryFactory(owner=user, github_url="https://github.com/test/repo")
        pr = PullRequestFactory(repo=repo, author=user, status="open")

        payload = {
            "repository": {"html_url": "https://github.com/test/repo"},
            "commits": [
                {
                    "id": "a" * 40,
                    "message": "Fix bug",
                    "author": {"username": "ghuser"},
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            ],
        }
        resp = post_webhook(client, "push", payload)
        assert resp.status_code == 200
        assert Commit.objects.filter(pr=pr, sha="a" * 40).exists()

    def test_push_unknown_repo_ignored(self, client):
        payload = {
            "repository": {"html_url": "https://github.com/unknown/repo"},
            "commits": [{"id": "b" * 40, "message": "test", "author": {"username": "x"}, "timestamp": "2025-01-01T00:00:00Z"}],
        }
        resp = post_webhook(client, "push", payload)
        assert resp.status_code == 200
        assert Commit.objects.count() == 0


# ── Pull request event handler ──────────────────────────────


@pytest.mark.django_db
class TestWebhookPullRequest:
    def test_opened_creates_pr(self, client):
        user = UserFactory(github_username="octocat")
        repo = RepositoryFactory(owner=user, github_url="https://github.com/test/repo2")

        payload = {
            "action": "opened",
            "pull_request": {
                "title": "New feature",
                "body": "Description",
                "user": {"login": "octocat"},
                "base": {"ref": "main"},
                "head": {"ref": "feature-branch"},
            },
            "repository": {"html_url": "https://github.com/test/repo2"},
        }
        resp = post_webhook(client, "pull_request", payload)
        assert resp.status_code == 200
        assert PullRequest.objects.filter(repo=repo, title="New feature").exists()

    def test_closed_updates_status(self, client):
        user = UserFactory(github_username="dev1")
        repo = RepositoryFactory(owner=user, github_url="https://github.com/test/repo3")
        pr = PullRequestFactory(
            repo=repo, author=user, title="Old PR",
            head_branch="fix-branch", status="open",
        )

        payload = {
            "action": "closed",
            "pull_request": {
                "title": "Old PR",
                "body": "",
                "user": {"login": "dev1"},
                "base": {"ref": "main"},
                "head": {"ref": "fix-branch"},
                "merged": False,
            },
            "repository": {"html_url": "https://github.com/test/repo3"},
        }
        resp = post_webhook(client, "pull_request", payload)
        assert resp.status_code == 200
        pr.refresh_from_db()
        assert pr.status == "closed"

    def test_merged_pr(self, client):
        user = UserFactory(github_username="dev2")
        repo = RepositoryFactory(owner=user, github_url="https://github.com/test/repo4")
        pr = PullRequestFactory(
            repo=repo, author=user, title="Merge PR",
            head_branch="merge-branch", status="open",
        )

        payload = {
            "action": "closed",
            "pull_request": {
                "title": "Merge PR",
                "body": "",
                "user": {"login": "dev2"},
                "base": {"ref": "main"},
                "head": {"ref": "merge-branch"},
                "merged": True,
            },
            "repository": {"html_url": "https://github.com/test/repo4"},
        }
        resp = post_webhook(client, "pull_request", payload)
        assert resp.status_code == 200
        pr.refresh_from_db()
        assert pr.status == "merged"


# ── Pull request review event handler ───────────────────────


@pytest.mark.django_db
class TestWebhookPullRequestReview:
    def test_review_creates_review(self, client):
        from reviews.models import Review

        reviewer = UserFactory(github_username="reviewer1")
        owner = UserFactory()
        repo = RepositoryFactory(owner=owner, github_url="https://github.com/test/repo5")
        pr = PullRequestFactory(repo=repo, author=owner, head_branch="rev-branch")

        payload = {
            "action": "submitted",
            "review": {
                "user": {"login": "reviewer1"},
                "state": "approved",
            },
            "pull_request": {
                "head": {"ref": "rev-branch"},
            },
            "repository": {"html_url": "https://github.com/test/repo5"},
        }
        resp = post_webhook(client, "pull_request_review", payload)
        assert resp.status_code == 200
        review = Review.objects.get(pr=pr, reviewer=reviewer)
        assert review.status == "approved"
        assert review.submitted_at is not None
