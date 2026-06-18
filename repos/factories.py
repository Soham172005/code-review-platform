import factory
from django.utils import timezone

from users.factories import UserFactory

from .models import Commit, DiffFile, PullRequest, Repository


class RepositoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Repository

    name = factory.Sequence(lambda n: f"repo-{n}")
    owner = factory.SubFactory(UserFactory)
    github_url = factory.LazyAttribute(lambda o: f"https://github.com/{o.owner.username}/{o.name}")


class PullRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PullRequest

    repo = factory.SubFactory(RepositoryFactory)
    title = factory.Sequence(lambda n: f"Pull Request {n}")
    description = "Test PR description"
    author = factory.LazyAttribute(lambda o: o.repo.owner)
    base_branch = "main"
    head_branch = factory.Sequence(lambda n: f"feature-{n}")
    status = PullRequest.Status.DRAFT


class CommitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Commit

    pr = factory.SubFactory(PullRequestFactory)
    sha = factory.Sequence(lambda n: f"{n:040d}")
    message = factory.Sequence(lambda n: f"Commit message {n}")
    author = factory.LazyAttribute(lambda o: o.pr.author)
    committed_at = factory.LazyFunction(timezone.now)


class DiffFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiffFile

    commit = factory.SubFactory(CommitFactory)
    file_path = factory.Sequence(lambda n: f"file_{n}.py")
    change_type = DiffFile.ChangeType.MODIFIED
    patch = factory.LazyFunction(lambda: [{"old_start": 1, "old_lines": 3, "new_start": 1, "new_lines": 3, "lines": []}])
