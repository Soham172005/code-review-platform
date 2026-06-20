import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from repos.factories import CommitFactory, DiffFileFactory, PullRequestFactory
from repos.tasks import run_ai_review
from reviews.models import Review, ReviewComment

User = get_user_model()


@pytest.mark.django_db
class TestAIReviewMockMode:
    def _create_pr_with_diff(self):
        pr = PullRequestFactory(status="open")
        commit = CommitFactory(pr=pr)
        df = DiffFileFactory(
            commit=commit,
            file_path="app/views.py",
            patch=[
                {
                    "old_start": 1,
                    "old_lines": 5,
                    "new_start": 1,
                    "new_lines": 7,
                    "lines": [
                        {"content": "def index():", "line_type": "context", "old_lineno": 1, "new_lineno": 1},
                        {"content": "    return None", "line_type": "removed", "old_lineno": 2, "new_lineno": None},
                        {"content": "    data = fetch()", "line_type": "added", "old_lineno": None, "new_lineno": 2},
                        {"content": "    return data", "line_type": "added", "old_lineno": None, "new_lineno": 3},
                    ],
                }
            ],
        )
        return pr, df

    @override_settings(AI_REVIEW_ENABLED=False, AI_REVIEW_MOCK=True, ANTHROPIC_API_KEY="")
    def test_mock_mode_creates_review_comments(self):
        pr, df = self._create_pr_with_diff()

        run_ai_review(pr.pk)

        bot = User.objects.get(username="ai-reviewer")
        assert bot.role == "reviewer"

        review = Review.objects.get(pr=pr, reviewer=bot)
        assert review.submitted_at is not None

        comments = ReviewComment.objects.filter(review=review)
        assert comments.count() == 3

        bodies = [c.body for c in comments]
        assert any("[WARNING]" in b for b in bodies)
        assert any("[INFO]" in b for b in bodies)
        assert any("[ERROR]" in b for b in bodies)

    @override_settings(AI_REVIEW_ENABLED=False, AI_REVIEW_MOCK=True, ANTHROPIC_API_KEY="")
    def test_mock_mode_sets_changes_requested_when_error_present(self):
        pr, _ = self._create_pr_with_diff()

        run_ai_review(pr.pk)

        review = Review.objects.get(pr=pr, reviewer__username="ai-reviewer")
        assert review.status == "changes_requested"

    @override_settings(AI_REVIEW_ENABLED=False, AI_REVIEW_MOCK=True, ANTHROPIC_API_KEY="")
    def test_mock_comments_reference_actual_diff_file(self):
        pr, df = self._create_pr_with_diff()

        run_ai_review(pr.pk)

        comments = ReviewComment.objects.filter(review__pr=pr)
        for comment in comments:
            assert comment.diff_file == df
            assert comment.commit_sha == df.commit.sha

    @override_settings(AI_REVIEW_ENABLED=False, AI_REVIEW_MOCK=False, ANTHROPIC_API_KEY="")
    def test_skips_when_disabled_and_not_mock(self):
        pr, _ = self._create_pr_with_diff()

        run_ai_review(pr.pk)

        assert Review.objects.count() == 0
        assert ReviewComment.objects.count() == 0

    @override_settings(AI_REVIEW_ENABLED=False, AI_REVIEW_MOCK=True, ANTHROPIC_API_KEY="")
    def test_mock_skips_when_no_diff_files(self):
        pr = PullRequestFactory(status="open")

        run_ai_review(pr.pk)

        assert Review.objects.count() == 0
