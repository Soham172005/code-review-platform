from django.urls import path

from . import views

urlpatterns = [
    path("", views.RepositoryListCreate.as_view(), name="repo-list-create"),
    path("<int:pk>/", views.RepositoryDetail.as_view(), name="repo-detail"),
    path("<int:repo_id>/prs/", views.PRListCreate.as_view(), name="pr-list-create"),
]
