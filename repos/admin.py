from django.contrib import admin

from .models import Commit, DiffFile, PRTransitionHistory, PullRequest, Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "owner__username"]


@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ["title", "repo", "author", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["title"]


@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ["sha", "message", "author", "committed_at"]


@admin.register(DiffFile)
class DiffFileAdmin(admin.ModelAdmin):
    list_display = ["file_path", "change_type", "commit"]


@admin.register(PRTransitionHistory)
class PRTransitionHistoryAdmin(admin.ModelAdmin):
    list_display = ["pr", "from_status", "to_status", "actor", "timestamp"]
    list_filter = ["from_status", "to_status"]
