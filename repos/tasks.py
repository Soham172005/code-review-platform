import structlog
from celery import shared_task

log = structlog.get_logger()


@shared_task
def parse_pr_diff(pr_id):
    from repos.models import DiffFile, PullRequest
    from repos.utils import GitDiffParser

    log.info("task_started", task="parse_pr_diff", pr_id=pr_id)
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
    log.info("task_completed", task="parse_pr_diff", pr_id=pr_id)


@shared_task
def process_webhook_event(event_type, payload):
    from repos.webhooks import handle_pull_request, handle_pull_request_review, handle_push

    log.info("webhook_processing", event_type=event_type)
    handlers = {
        "push": handle_push,
        "pull_request": handle_pull_request,
        "pull_request_review": handle_pull_request_review,
    }
    handler = handlers.get(event_type)
    if handler:
        handler(payload)
    log.info("webhook_processed", event_type=event_type)


@shared_task
def run_ai_review(pr_id):
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from repos.models import DiffFile, PullRequest
    from reviews.models import Review, ReviewComment

    log.info("task_started", task="run_ai_review", pr_id=pr_id)

    if not settings.AI_REVIEW_ENABLED and not settings.AI_REVIEW_MOCK:
        log.info("ai_review_skipped", reason="no_api_key", pr_id=pr_id)
        return

    pr = PullRequest.objects.select_related("author").get(pk=pr_id)
    diff_files = DiffFile.objects.filter(commit__pr=pr)
    if not diff_files.exists():
        log.info("ai_review_skipped", reason="no_diff_files", pr_id=pr_id)
        return

    if settings.AI_REVIEW_MOCK:
        from repos.ai_reviewer import MockAIReviewer

        log.info("ai_review_using_mock", pr_id=pr_id)
        reviewer = MockAIReviewer()
    else:
        from repos.ai_reviewer import AIReviewer

        reviewer = AIReviewer()

    comments = reviewer.review_diff(pr.title, pr.description, list(diff_files))

    if not comments:
        log.info("ai_review_completed", pr_id=pr_id, comment_count=0)
        return

    User = get_user_model()
    bot_user, _ = User.objects.get_or_create(
        username="ai-reviewer",
        defaults={"role": "reviewer", "email": "ai-reviewer@codereview.local"},
    )

    review, _ = Review.objects.get_or_create(pr=pr, reviewer=bot_user)
    review.status = "changes_requested" if any(
        c.get("severity") == "error" for c in comments
    ) else "approved"
    review.submitted_at = timezone.now()
    review.save()

    diff_file_map = {df.file_path: df for df in diff_files}
    for comment in comments:
        df = diff_file_map.get(comment.get("file_path"))
        if not df:
            continue
        severity = comment.get("severity", "info")
        body = f"[{severity.upper()}] {comment.get('body', '')}"
        ReviewComment.objects.create(
            review=review,
            diff_file=df,
            commit_sha=df.commit.sha,
            line_position=comment.get("line_position", 1),
            body=body,
        )

    log.info("ai_review_completed", pr_id=pr_id, comment_count=len(comments))
