import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

PR_ACTION_STATUS_MAP = {
    "opened": "open",
    "closed": "closed",
    "reopened": "open",
}


def verify_signature(payload_body, signature_header):
    if not signature_header:
        return False
    secret = settings.GITHUB_WEBHOOK_SECRET.encode()
    expected = "sha256=" + hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def handle_push(payload):
    from repos.models import Commit, Repository
    from users.models import User

    repo_url = payload.get("repository", {}).get("html_url", "")
    try:
        repo = Repository.objects.get(github_url=repo_url)
    except Repository.DoesNotExist:
        logger.warning("Webhook push: no matching repo for %s", repo_url)
        return

    commits_data = payload.get("commits", [])
    for c in commits_data:
        author_username = c.get("author", {}).get("username", "")
        author = User.objects.filter(github_username=author_username).first()
        if not author:
            author = repo.owner

        prs = repo.pull_requests.exclude(status__in=["merged", "closed"])
        for pr in prs:
            Commit.objects.get_or_create(
                pr=pr,
                sha=c["id"],
                defaults={
                    "message": c.get("message", ""),
                    "author": author,
                    "committed_at": c.get("timestamp", timezone.now().isoformat()),
                },
            )


def handle_pull_request(payload):
    from repos.models import PullRequest, Repository
    from users.models import User

    action = payload.get("action", "")
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    repo_url = repo_data.get("html_url", "")
    try:
        repo = Repository.objects.get(github_url=repo_url)
    except Repository.DoesNotExist:
        logger.warning("Webhook PR: no matching repo for %s", repo_url)
        return

    sender_username = pr_data.get("user", {}).get("login", "")
    author = User.objects.filter(github_username=sender_username).first()
    if not author:
        author = repo.owner

    github_pr_title = pr_data.get("title", "Untitled PR")
    base_branch = pr_data.get("base", {}).get("ref", "main")
    head_branch = pr_data.get("head", {}).get("ref", "feature")

    if action == "opened":
        PullRequest.objects.create(
            repo=repo,
            title=github_pr_title,
            description=pr_data.get("body", "") or "",
            author=author,
            base_branch=base_branch,
            head_branch=head_branch,
            status="open",
        )
    elif action in ("closed", "reopened"):
        existing = repo.pull_requests.filter(
            title=github_pr_title,
            head_branch=head_branch,
        ).first()
        if existing:
            new_status = PR_ACTION_STATUS_MAP.get(action)
            if action == "closed" and pr_data.get("merged", False):
                new_status = "merged"
            if new_status:
                existing.status = new_status
                existing.save(update_fields=["status"])


def handle_pull_request_review(payload):
    from reviews.models import Review
    from repos.models import PullRequest, Repository
    from users.models import User

    review_data = payload.get("review", {})
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    repo_url = repo_data.get("html_url", "")
    try:
        repo = Repository.objects.get(github_url=repo_url)
    except Repository.DoesNotExist:
        return

    head_branch = pr_data.get("head", {}).get("ref", "")
    pr = repo.pull_requests.filter(head_branch=head_branch).first()
    if not pr:
        return

    reviewer_login = review_data.get("user", {}).get("login", "")
    reviewer = User.objects.filter(github_username=reviewer_login).first()
    if not reviewer:
        return

    gh_state = review_data.get("state", "").lower()
    status_map = {
        "approved": "approved",
        "changes_requested": "changes_requested",
    }
    status = status_map.get(gh_state, "pending")

    review, _ = Review.objects.get_or_create(pr=pr, reviewer=reviewer)
    review.status = status
    if status != "pending":
        review.submitted_at = timezone.now()
    review.save()
