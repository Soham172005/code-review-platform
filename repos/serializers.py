from rest_framework import serializers

from .models import Commit, DiffFile, PRTransitionHistory, PullRequest, Repository


class RepositorySerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Repository
        fields = ["id", "name", "owner", "github_url", "created_at"]
        read_only_fields = ["id", "owner", "created_at"]

    def validate_name(self, value):
        request = self.context.get("request")
        if request and Repository.objects.filter(owner=request.user, name=value).exists():
            raise serializers.ValidationError("You already have a repository with this name.")
        return value


class PullRequestSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    repo_name = serializers.ReadOnlyField(source="repo.name")

    class Meta:
        model = PullRequest
        fields = [
            "id", "repo", "repo_name", "title", "description",
            "author", "base_branch", "head_branch", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "repo", "author", "status", "created_at", "updated_at"]


class PRTransitionSerializer(serializers.Serializer):
    transition = serializers.ChoiceField(
        choices=list(PullRequest.TRANSITION_MAP.keys())
    )


class PRTransitionHistorySerializer(serializers.ModelSerializer):
    actor = serializers.ReadOnlyField(source="actor.username")

    class Meta:
        model = PRTransitionHistory
        fields = ["id", "from_status", "to_status", "actor", "timestamp"]


class DiffFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiffFile
        fields = ["id", "file_path", "change_type", "patch"]


class CommitSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    diff_files = DiffFileSerializer(many=True, read_only=True)

    class Meta:
        model = Commit
        fields = ["id", "sha", "message", "author", "committed_at", "diff_files"]
