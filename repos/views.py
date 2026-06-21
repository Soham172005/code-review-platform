import json

from django.shortcuts import get_object_or_404
from django_fsm import TransitionNotAllowed
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reviews.models import Review, ReviewComment
from reviews.serializers import ReviewCommentSerializer, SubmitReviewSerializer
from users.permissions import IsReviewerOrAdmin

from .models import PRTransitionHistory, PullRequest, Repository
from .serializers import (
    CommitSerializer,
    ImportPRSerializer,
    PRTransitionHistorySerializer,
    PRTransitionSerializer,
    PullRequestSerializer,
    RepositorySerializer,
)
from .webhooks import verify_signature


class RepositoryListCreate(generics.ListCreateAPIView):
    serializer_class = RepositorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Repository.objects.select_related("owner").all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class RepositoryDetail(generics.RetrieveAPIView):
    queryset = Repository.objects.select_related("owner")
    serializer_class = RepositorySerializer
    permission_classes = [IsAuthenticated]


class PRListCreate(generics.ListCreateAPIView):
    serializer_class = PullRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PullRequest.objects.filter(
            repo_id=self.kwargs["repo_id"]
        ).select_related("author", "repo")

    def perform_create(self, serializer):
        repo = get_object_or_404(Repository, pk=self.kwargs["repo_id"])
        serializer.save(author=self.request.user, repo=repo)


class PRDetail(generics.RetrieveAPIView):
    queryset = PullRequest.objects.select_related("author", "repo")
    serializer_class = PullRequestSerializer
    permission_classes = [IsAuthenticated]


class PRDiffView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        pr = get_object_or_404(PullRequest, pk=pk)
        commits = pr.commits.prefetch_related("diff_files").order_by("committed_at")
        serializer = CommitSerializer(commits, many=True)
        return Response(serializer.data)


class PRCommentCreate(generics.CreateAPIView):
    serializer_class = ReviewCommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        pr = get_object_or_404(PullRequest, pk=self.kwargs["pk"])
        review, _ = Review.objects.get_or_create(
            pr=pr, reviewer=self.request.user
        )
        serializer.save(review=review)


class PRReviewSubmit(APIView):
    permission_classes = [IsAuthenticated, IsReviewerOrAdmin]

    def post(self, request, pk):
        pr = get_object_or_404(PullRequest, pk=pk)
        serializer = SubmitReviewSerializer(
            data=request.data,
            context={"request": request, "pr": pr},
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(
            {
                "id": review.id,
                "status": review.status,
                "submitted_at": review.submitted_at,
            },
            status=status.HTTP_200_OK,
        )


class PRTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        pr = get_object_or_404(PullRequest, pk=pk)
        serializer = PRTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transition_name = serializer.validated_data["transition"]
        method = getattr(pr, PullRequest.TRANSITION_MAP[transition_name])
        from_status = pr.status

        try:
            method()
        except TransitionNotAllowed:
            return Response(
                {"detail": f"Transition '{transition_name}' is not allowed from state '{pr.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pr.save()
        PRTransitionHistory.objects.create(
            pr=pr,
            from_status=from_status,
            to_status=pr.status,
            actor=request.user,
        )

        if pr.status == "open":
            from repos.tasks import run_ai_review

            run_ai_review.delay(pr.pk)

        return Response(PullRequestSerializer(pr).data)


class PRTransitionHistoryView(generics.ListAPIView):
    serializer_class = PRTransitionHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PRTransitionHistory.objects.filter(pr_id=self.kwargs["pk"])


class ImportPRView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, repo_id):
        from django.conf import settings

        from repos.git_ingestion import GitIngestionError
        from repos.tasks import import_real_pr

        repo = get_object_or_404(Repository, pk=repo_id)
        serializer = ImportPRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_kwargs = dict(
            repo_id=repo.pk,
            base_branch=serializer.validated_data["base_branch"],
            head_branch=serializer.validated_data["head_branch"],
            user_id=request.user.pk,
            pr_title=serializer.validated_data["title"],
            pr_description=serializer.validated_data.get("description", ""),
        )

        if settings.CELERY_TASK_ALWAYS_EAGER:
            try:
                pr_id = import_real_pr(**task_kwargs)
            except GitIngestionError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            pr = PullRequest.objects.get(pk=pr_id)
            return Response(
                PullRequestSerializer(pr).data,
                status=status.HTTP_201_CREATED,
            )

        task = import_real_pr.delay(**task_kwargs)
        return Response(
            {"task_id": task.id, "status": "processing"},
            status=status.HTTP_202_ACCEPTED,
        )


class GitHubWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.META.get("HTTP_X_HUB_SIGNATURE_256", "")
        raw_body = request.body

        if not signature:
            return Response(
                {"detail": "Missing X-Hub-Signature-256 header."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verify_signature(raw_body, signature):
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_403_FORBIDDEN,
            )

        event_type = request.META.get("HTTP_X_GITHUB_EVENT", "")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from repos.tasks import process_webhook_event

        process_webhook_event.delay(event_type, payload)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
