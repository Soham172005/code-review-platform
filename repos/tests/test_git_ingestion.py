import shutil
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from repos.factories import RepositoryFactory
from repos.git_ingestion import (
    AuthenticationError,
    BranchNotFoundError,
    CloneError,
    GitIngestionService,
)
from repos.models import Commit, DiffFile, PullRequest
from users.factories import UserFactory


def auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ── GitIngestionService unit tests ───────────────────────────


class TestBuildCloneUrl:
    def test_public_repo_no_token(self):
        service = GitIngestionService()
        url = service._build_clone_url("https://github.com/user/repo", None)
        assert url == "https://github.com/user/repo"

    def test_private_repo_with_token(self):
        service = GitIngestionService()
        url = service._build_clone_url("https://github.com/user/repo", "ghp_abc123")
        assert url == "https://ghp_abc123@github.com/user/repo"

    def test_non_github_url_ignores_token(self):
        service = GitIngestionService()
        url = service._build_clone_url("https://gitlab.com/user/repo", "token123")
        assert url == "https://gitlab.com/user/repo"


SAMPLE_DIFF = """\
diff --git a/hello.py b/hello.py
new file mode 100644
--- /dev/null
+++ b/hello.py
@@ -0,0 +1,3 @@
+def hello():
+    return "world"
+
"""


class TestImportPRFromBranches:
    @patch("repos.git_ingestion.Repo")
    def test_successful_import(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_repo.git.rev_parse.return_value = "abc123"
        mock_repo.git.diff.return_value = SAMPLE_DIFF
        mock_repo.git.log.return_value = (
            "abc1234567890123456789012345678901234567|||Add hello|||2025-01-01 12:00:00 +0000|||testuser"
        )

        service = GitIngestionService()
        result = service.import_pr_from_branches(
            "https://github.com/test/repo", "main", "feature"
        )

        assert result["base_branch"] == "main"
        assert result["head_branch"] == "feature"
        assert len(result["commits"]) == 1
        assert result["commits"][0]["message"] == "Add hello"
        assert len(result["diff_files"]) == 1
        assert result["diff_files"][0]["file_path"] == "hello.py"
        assert result["diff_files"][0]["change_type"] == "added"

    @patch("repos.git_ingestion.shutil.rmtree")
    @patch("repos.git_ingestion.Repo")
    def test_cleanup_on_success(self, mock_repo_class, mock_rmtree):
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_repo.git.rev_parse.return_value = "abc"
        mock_repo.git.diff.return_value = ""
        mock_repo.git.log.return_value = ""

        service = GitIngestionService()
        service.import_pr_from_branches(
            "https://github.com/test/repo", "main", "dev"
        )

        mock_rmtree.assert_called_once()

    @patch("repos.git_ingestion.shutil.rmtree")
    @patch("repos.git_ingestion.Repo")
    def test_cleanup_on_failure(self, mock_repo_class, mock_rmtree):
        from git import GitCommandError

        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_repo.git.rev_parse.side_effect = GitCommandError("rev-parse", "not found")

        service = GitIngestionService()
        with pytest.raises(BranchNotFoundError):
            service.import_pr_from_branches(
                "https://github.com/test/repo", "main", "nonexistent"
            )

        mock_rmtree.assert_called_once()

    @patch("repos.git_ingestion.Repo")
    def test_clone_failure_raises_clone_error(self, mock_repo_class):
        from git import GitCommandError

        mock_repo_class.clone_from.side_effect = GitCommandError("clone", "failed")

        service = GitIngestionService()
        with pytest.raises(CloneError):
            service.import_pr_from_branches(
                "https://github.com/test/repo", "main", "feature"
            )

    @patch("repos.git_ingestion.Repo")
    def test_auth_failure_raises_auth_error(self, mock_repo_class):
        from git import GitCommandError

        mock_repo_class.clone_from.side_effect = GitCommandError(
            "clone", "Authentication failed"
        )

        service = GitIngestionService()
        with pytest.raises(AuthenticationError):
            service.import_pr_from_branches(
                "https://github.com/test/repo", "main", "feature"
            )

    @patch("repos.git_ingestion.Repo")
    def test_base_branch_not_found(self, mock_repo_class):
        from git import GitCommandError

        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_repo.git.rev_parse.side_effect = GitCommandError("rev-parse", "not found")

        service = GitIngestionService()
        with pytest.raises(BranchNotFoundError, match="Base branch"):
            service.import_pr_from_branches(
                "https://github.com/test/repo", "nonexistent", "feature"
            )


# ── Import PR API endpoint tests ────────────────────────────


@pytest.mark.django_db
class TestImportPREndpoint:
    @patch("repos.git_ingestion.GitIngestionService.import_pr_from_branches")
    def test_import_creates_pr_and_diff_files(self, mock_import):
        mock_import.return_value = {
            "commits": [
                {
                    "sha": "a" * 40,
                    "message": "Add feature",
                    "committed_at": "2025-01-01 12:00:00 +0000",
                    "author_name": "test",
                }
            ],
            "diff_files": [
                {
                    "file_path": "app.py",
                    "change_type": "modified",
                    "hunks": [{"old_start": 1, "old_lines": 2, "new_start": 1, "new_lines": 3, "lines": []}],
                }
            ],
            "base_branch": "main",
            "head_branch": "feature",
            "raw_diff": SAMPLE_DIFF,
        }

        user = UserFactory()
        repo = RepositoryFactory(owner=user, github_url="https://github.com/test/repo")
        client = auth_client_for(user)

        resp = client.post(f"/api/repos/{repo.pk}/import-pr/", {
            "title": "Import test",
            "base_branch": "main",
            "head_branch": "feature",
        })

        assert resp.status_code == 201
        assert resp.data["title"] == "Import test"
        assert resp.data["status"] == "open"

        pr = PullRequest.objects.get(pk=resp.data["id"])
        assert pr.base_branch == "main"
        assert pr.head_branch == "feature"
        assert Commit.objects.filter(pr=pr).count() == 1
        assert DiffFile.objects.filter(commit__pr=pr).count() == 1

    @patch("repos.git_ingestion.GitIngestionService.import_pr_from_branches")
    def test_import_handles_ingestion_error(self, mock_import):
        from repos.git_ingestion import BranchNotFoundError

        mock_import.side_effect = BranchNotFoundError(
            "Branch 'nonexistent' not found"
        )

        user = UserFactory()
        repo = RepositoryFactory(owner=user, github_url="https://github.com/test/repo")
        client = auth_client_for(user)

        resp = client.post(f"/api/repos/{repo.pk}/import-pr/", {
            "title": "Bad import",
            "base_branch": "main",
            "head_branch": "nonexistent",
        })

        assert resp.status_code == 400

    def test_import_requires_auth(self):
        repo = RepositoryFactory()
        client = APIClient()
        resp = client.post(f"/api/repos/{repo.pk}/import-pr/", {
            "title": "test",
            "head_branch": "feature",
        })
        assert resp.status_code == 401

    def test_import_requires_head_branch(self):
        user = UserFactory()
        repo = RepositoryFactory(owner=user)
        client = auth_client_for(user)
        resp = client.post(f"/api/repos/{repo.pk}/import-pr/", {
            "title": "test",
        })
        assert resp.status_code == 400
