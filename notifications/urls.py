from django.urls import path

from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/read/", views.NotificationMarkReadView.as_view(), name="notification-read"),
    path("mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("stream/", views.NotificationStreamView.as_view(), name="notification-stream"),
]
