from django.contrib import admin

from .models import Review, ReviewComment


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["pr", "reviewer", "status", "submitted_at"]
    list_filter = ["status"]


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ["diff_file", "line_position", "body", "is_resolved", "created_at"]
    list_filter = ["is_resolved"]
