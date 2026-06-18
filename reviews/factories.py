import factory

from repos.factories import DiffFileFactory, PullRequestFactory
from users.factories import ReviewerFactory

from .models import Review, ReviewComment


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    pr = factory.SubFactory(PullRequestFactory)
    reviewer = factory.SubFactory(ReviewerFactory)
    status = Review.Status.PENDING


class ReviewCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReviewComment

    review = factory.SubFactory(ReviewFactory)
    diff_file = factory.SubFactory(DiffFileFactory)
    commit_sha = factory.LazyAttribute(lambda o: o.diff_file.commit.sha)
    line_position = 1
    body = "Test comment"
