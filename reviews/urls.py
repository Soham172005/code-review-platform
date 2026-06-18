from django.urls import path

from . import views

urlpatterns = [
    path(
        "comments/<int:pk>/resolve/",
        views.CommentResolveView.as_view(),
        name="comment-resolve",
    ),
]
