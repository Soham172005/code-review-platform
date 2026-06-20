import structlog
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

log = structlog.get_logger()


@shared_task
def send_comment_notification(comment_id):
    from notifications.models import Notification
    from reviews.models import ReviewComment

    log.info("task_started", task="send_comment_notification", comment_id=comment_id)
    comment = ReviewComment.objects.select_related(
        "review__pr__author", "review__reviewer"
    ).get(pk=comment_id)
    pr = comment.review.pr
    actor = comment.review.reviewer
    recipient = pr.author

    if actor == recipient:
        return

    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        event_type=Notification.EventType.COMMENT_ADDED,
        message=f"{actor.username} commented on PR #{pr.pk}: {pr.title}",
    )
    log.info("task_completed", task="send_comment_notification", comment_id=comment_id)


@shared_task
def send_review_notification(review_id):
    from notifications.models import Notification
    from reviews.models import Review

    log.info("task_started", task="send_review_notification", review_id=review_id)
    review = Review.objects.select_related("pr__author", "reviewer").get(pk=review_id)
    pr = review.pr
    actor = review.reviewer
    recipient = pr.author

    if actor == recipient:
        return

    status_label = "approved" if review.status == "approved" else "requested changes on"
    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        event_type=Notification.EventType.REVIEW_SUBMITTED,
        message=f"{actor.username} {status_label} PR #{pr.pk}: {pr.title}",
    )
    log.info("task_completed", task="send_review_notification", review_id=review_id)


@shared_task
def send_pr_state_notification(pr_id, from_status, to_status, actor_id):
    from django.contrib.auth import get_user_model

    from notifications.models import Notification
    from repos.models import PullRequest
    from reviews.models import Review

    log.info(
        "task_started",
        task="send_pr_state_notification",
        pr_id=pr_id,
        from_status=from_status,
        to_status=to_status,
    )
    User = get_user_model()
    pr = PullRequest.objects.select_related("author").get(pk=pr_id)
    actor = User.objects.get(pk=actor_id)

    recipients = set()
    recipients.add(pr.author)
    reviewer_ids = Review.objects.filter(pr=pr).values_list("reviewer_id", flat=True)
    for reviewer in User.objects.filter(pk__in=reviewer_ids):
        recipients.add(reviewer)

    recipients.discard(actor)

    for recipient in recipients:
        Notification.objects.create(
            recipient=recipient,
            actor=actor,
            event_type=Notification.EventType.PR_STATE_CHANGED,
            message=f"{actor.username} changed PR #{pr.pk} from {from_status} to {to_status}",
        )
    log.info("task_completed", task="send_pr_state_notification", pr_id=pr_id)


@shared_task
def send_email_notification(user_id, subject, body):
    from django.contrib.auth import get_user_model

    log.info("task_started", task="send_email_notification", user_id=user_id)
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    if not user.email:
        log.warning("email_skipped", reason="no_email", user_id=user_id)
        return
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    log.info("task_completed", task="send_email_notification", user_id=user_id)
