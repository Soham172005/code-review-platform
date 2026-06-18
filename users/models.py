from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        REVIEWER = "reviewer", "Reviewer"
        AUTHOR = "author", "Author"

    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    github_username = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.AUTHOR,
    )

    class Meta:
        db_table = "users"
