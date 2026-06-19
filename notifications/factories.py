import factory

from users.factories import UserFactory

from .models import Notification


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    actor = factory.SubFactory(UserFactory)
    event_type = Notification.EventType.COMMENT_ADDED
    message = "Test notification"
    is_read = False
