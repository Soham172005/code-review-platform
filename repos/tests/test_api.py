import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from repos.factories import (
    CommitFactory,
    DiffFileFactory,
    PullRequestFactory,
    RepositoryFactory,
)
from repos.models import PRTransitionHistory, PullRequest
from users.factories import AdminFactory, ReviewerFactory, UserFactory


def auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def admin_user():
    return AdminFactory()


@pytest.fixture
def reviewer_user():
    return ReviewerFactory()


@pytest.fixture
def auth_client(user):
    return auth_client_for(user)


# ── Repository endpoints ─────────────────────────────────────


@pytest.mark.django_db
class TestRepositoryAPI:
    def test_create_repo(self, auth_client):
        resp = auth_client.post("/api/repos/", {
            "name": "my-repo",
            "github_url": "https://github.com/test/my-repo",
        })
        assert resp.status_code == 201
        assert resp.data["name"] == "my-repo"

    def test_list_repos(self, auth_client, user):
        RepositoryFactory(owner=user)
        RepositoryFactory(owner=user)
        resp = auth_client.get("/api/repos/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_repo_detail(self, auth_client, user):
        repo = RepositoryFactory(owner=user)
        resp = auth_client.get(f"/api/repos/{repo.pk}/")
        assert resp.status_code == 200
        assert resp.data["name"] == repo.name

    def test_unauthenticated_create_fails(self):
        client = APIClient()
        resp = client.post("/api/repos/", {"name": "fail"})
        assert resp.status_code == 401

    def test_duplicate_repo_name_same_owner(self, auth_client, user):
        RepositoryFactory(owner=user, name="dup")
        resp = auth_client.post("/api/repos/", {"name": "dup"})
        assert resp.status_code == 400


# ── Pull Request endpoints ───────────────────────────────────


@pytest.mark.django_db
class TestPullRequestAPI:
    def test_create_pr(self, auth_client, user):
        repo = RepositoryFactory(owner=user)
        resp = auth_client.post(f"/api/repos/{repo.pk}/prs/", {
            "title": "Add feature",
            "description": "New feature",
            "base_branch": "main",
            "head_branch": "feature-x",
        })
        assert resp.status_code == 201
        assert resp.data["title"] == "Add feature"
        assert resp.data["status"] == "draft"

    def test_list_prs(self, auth_client, user):
        repo = RepositoryFactory(owner=user)
        PullRequestFactory(repo=repo, author=user)
        PullRequestFactory(repo=repo, author=user)
        resp = auth_client.get(f"/api/repos/{repo.pk}/prs/")
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_pr_detail(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user)
        resp = auth_client.get(f"/api/prs/{pr.pk}/")
        assert resp.status_code == 200
        assert resp.data["title"] == pr.title


# ── PR Diff endpoint ─────────────────────────────────────────


@pytest.mark.django_db
class TestPRDiff:
    def test_diff_returns_commits_and_files(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user)
        commit = CommitFactory(pr=pr, author=user)
        DiffFileFactory(commit=commit, file_path="main.py", change_type="modified")
        resp = auth_client.get(f"/api/prs/{pr.pk}/diff/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["sha"] == commit.sha
        assert len(resp.data[0]["diff_files"]) == 1
        assert resp.data[0]["diff_files"][0]["file_path"] == "main.py"

    def test_diff_empty_pr(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user)
        resp = auth_client.get(f"/api/prs/{pr.pk}/diff/")
        assert resp.status_code == 200
        assert resp.data == []


# ── PR State Machine ─────────────────────────────────────────


@pytest.mark.django_db
class TestPRTransition:
    def test_draft_to_open(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")
        resp = auth_client.post(
            f"/api/prs/{pr.pk}/transition/",
            {"transition": "open_pr"},
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "open"

    def test_full_lifecycle(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")

        resp = auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "open_pr"})
        assert resp.data["status"] == "open"

        resp = auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "submit_for_review"})
        assert resp.data["status"] == "in_review"

        resp = auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "approve"})
        assert resp.data["status"] == "approved"

        resp = auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "merge"})
        assert resp.data["status"] == "merged"

    def test_invalid_transition(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")
        resp = auth_client.post(
            f"/api/prs/{pr.pk}/transition/",
            {"transition": "merge"},
        )
        assert resp.status_code == 400

    def test_close_from_open(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="open")
        resp = auth_client.post(
            f"/api/prs/{pr.pk}/transition/",
            {"transition": "close"},
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "closed"

    def test_reopen(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="closed")
        resp = auth_client.post(
            f"/api/prs/{pr.pk}/transition/",
            {"transition": "reopen"},
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "open"

    def test_transition_history_recorded(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")
        auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "open_pr"})
        auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "submit_for_review"})

        history = PRTransitionHistory.objects.filter(pr=pr).order_by("timestamp")
        assert history.count() == 2
        assert history[0].from_status == "draft"
        assert history[0].to_status == "open"
        assert history[0].actor == user
        assert history[1].from_status == "open"
        assert history[1].to_status == "in_review"

    def test_transition_history_endpoint(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")
        auth_client.post(f"/api/prs/{pr.pk}/transition/", {"transition": "open_pr"})
        resp = auth_client.get(f"/api/prs/{pr.pk}/history/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_cannot_transition_merged(self, auth_client, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="merged")
        resp = auth_client.post(
            f"/api/prs/{pr.pk}/transition/",
            {"transition": "close"},
        )
        assert resp.status_code == 400


# ── FSM model-level tests ────────────────────────────────────


@pytest.mark.django_db
class TestFSMModel:
    def test_direct_status_change_blocked_by_fsm(self, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")
        from django_fsm import TransitionNotAllowed
        with pytest.raises(TransitionNotAllowed):
            pr.merge()

    def test_valid_transition_changes_status(self, user):
        pr = PullRequestFactory(author=user, repo__owner=user, status="draft")
        pr.open_pr()
        assert pr.status == "open"
