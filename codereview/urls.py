from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from repos import views as repo_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("users.urls")),
    path("api/repos/", include("repos.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/notifications/", include("notifications.urls")),
    # Flat PR endpoints
    path("api/prs/<int:pk>/", repo_views.PRDetail.as_view(), name="pr-detail"),
    path("api/prs/<int:pk>/diff/", repo_views.PRDiffView.as_view(), name="pr-diff"),
    path("api/prs/<int:pk>/comments/", repo_views.PRCommentCreate.as_view(), name="pr-comment-create"),
    path("api/prs/<int:pk>/reviews/", repo_views.PRReviewSubmit.as_view(), name="pr-review-submit"),
    path("api/prs/<int:pk>/transition/", repo_views.PRTransitionView.as_view(), name="pr-transition"),
    path("api/prs/<int:pk>/history/", repo_views.PRTransitionHistoryView.as_view(), name="pr-history"),
]
