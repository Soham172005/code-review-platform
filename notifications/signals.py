from django.db.models.signals import post_save
from django.dispatch import receiver

from repos.models import PRTransitionHistory
from reviews.models import Review, ReviewComment


@receiver(post_save, sender=ReviewComment)
def on_comment_created(sender, instance, created, **kwargs):
    if created:
        from notifications.tasks import send_comment_notification

        send_comment_notification.delay(instance.pk)


@receiver(post_save, sender=Review)
def on_review_submitted(sender, instance, **kwargs):
    if instance.submitted_at is not None:
        from notifications.tasks import send_review_notification

        send_review_notification.delay(instance.pk)


@receiver(post_save, sender=PRTransitionHistory)
def on_pr_transition(sender, instance, created, **kwargs):
    if created:
        from notifications.tasks import send_pr_state_notification

        send_pr_state_notification.delay(
            instance.pr_id,
            instance.from_status,
            instance.to_status,
            instance.actor_id,
        )
