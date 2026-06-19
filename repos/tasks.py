from celery import shared_task
from django.utils import timezone


@shared_task
def parse_pr_diff(pr_id):
    from repos.models import Commit, DiffFile, PullRequest
    from repos.utils import GitDiffParser

    pr = PullRequest.objects.get(pk=pr_id)
    parser = GitDiffParser()

    for commit in pr.commits.all():
        if commit.diff_files.exists():
            continue
        raw_diff = getattr(commit, "_raw_diff", None)
        if not raw_diff:
            continue
        parsed_files = parser.parse_diff(raw_diff)
        for f in parsed_files:
            DiffFile.objects.create(
                commit=commit,
                file_path=f["file_path"],
                change_type=f["change_type"],
                patch=f["hunks"],
            )


@shared_task
def process_webhook_event(event_type, payload):
    from repos.webhooks import handle_pull_request, handle_pull_request_review, handle_push

    handlers = {
        "push": handle_push,
        "pull_request": handle_pull_request,
        "pull_request_review": handle_pull_request_review,
    }
    handler = handlers.get(event_type)
    if handler:
        handler(payload)
