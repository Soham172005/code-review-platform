import re
import shutil
import tempfile
from urllib.parse import urlparse

import structlog
from git import GitCommandError, InvalidGitRepositoryError, Repo

from repos.utils import GitDiffParser

log = structlog.get_logger()


class GitIngestionError(Exception):
    pass


class CloneError(GitIngestionError):
    pass


class BranchNotFoundError(GitIngestionError):
    pass


class AuthenticationError(GitIngestionError):
    pass


class GitIngestionService:
    def import_pr_from_branches(self, repo_url, base_branch, head_branch, github_token=None):
        clone_url = self._build_clone_url(repo_url, github_token)
        tmp_dir = tempfile.mkdtemp(prefix="cr-clone-")

        try:
            log.info("git_clone_start", repo_url=repo_url, base=base_branch, head=head_branch)
            try:
                repo = Repo.clone_from(
                    clone_url,
                    tmp_dir,
                    depth=50,
                    no_single_branch=True,
                )
            except GitCommandError as exc:
                err_msg = str(exc)
                if "Authentication" in err_msg or "could not read" in err_msg or "403" in err_msg:
                    raise AuthenticationError(
                        f"Authentication failed for {repo_url}. A GitHub token may be required."
                    ) from exc
                raise CloneError(f"Failed to clone repository: {err_msg}") from exc
            except InvalidGitRepositoryError as exc:
                raise CloneError(f"Invalid repository URL: {repo_url}") from exc

            try:
                repo.git.rev_parse("--verify", f"origin/{base_branch}")
            except GitCommandError:
                raise BranchNotFoundError(f"Base branch '{base_branch}' not found in repository.")

            try:
                repo.git.rev_parse("--verify", f"origin/{head_branch}")
            except GitCommandError:
                raise BranchNotFoundError(f"Head branch '{head_branch}' not found in repository.")

            raw_diff = repo.git.diff(f"origin/{base_branch}...origin/{head_branch}")

            try:
                commit_log = repo.git.log(
                    f"origin/{base_branch}..origin/{head_branch}",
                    "--format=%H|||%s|||%ai|||%an",
                )
            except GitCommandError:
                commit_log = ""

            commits = []
            if commit_log.strip():
                for line in commit_log.strip().split("\n"):
                    parts = line.split("|||")
                    if len(parts) == 4:
                        commits.append({
                            "sha": parts[0],
                            "message": parts[1],
                            "committed_at": parts[2],
                            "author_name": parts[3],
                        })

            parser = GitDiffParser()
            diff_files = parser.parse_diff(raw_diff)

            log.info(
                "git_clone_success",
                repo_url=repo_url,
                commits=len(commits),
                diff_files=len(diff_files),
            )

            return {
                "commits": commits,
                "diff_files": diff_files,
                "base_branch": base_branch,
                "head_branch": head_branch,
                "raw_diff": raw_diff,
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            log.info("git_clone_cleanup", tmp_dir=tmp_dir)

    def _build_clone_url(self, repo_url, github_token=None):
        if not github_token:
            return repo_url

        parsed = urlparse(repo_url)
        if parsed.hostname not in ("github.com", "www.github.com"):
            return repo_url

        return f"https://{github_token}@github.com{parsed.path}"
