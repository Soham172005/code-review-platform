from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from repos.models import Commit, DiffFile, PullRequest, Repository

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for the code review platform"

    def handle(self, *args, **options):
        demo_user, created = User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@codereview.local",
                "role": "author",
            },
        )
        if created:
            demo_user.set_password("demopass123")
            demo_user.save()
            self.stdout.write(self.style.SUCCESS("Created user: demo"))
        else:
            self.stdout.write("User 'demo' already exists")

        reviewer_user, created = User.objects.get_or_create(
            username="reviewer1",
            defaults={
                "email": "reviewer1@codereview.local",
                "role": "reviewer",
            },
        )
        if created:
            reviewer_user.set_password("reviewpass123")
            reviewer_user.save()
            self.stdout.write(self.style.SUCCESS("Created user: reviewer1"))
        else:
            self.stdout.write("User 'reviewer1' already exists")

        bot_user, created = User.objects.get_or_create(
            username="ai-reviewer",
            defaults={
                "email": "ai-reviewer@codereview.local",
                "role": "reviewer",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created user: ai-reviewer"))
        else:
            self.stdout.write("User 'ai-reviewer' already exists")

        repo, created = Repository.objects.get_or_create(
            owner=demo_user,
            name="demo-project",
            defaults={"github_url": "https://github.com/demo/demo-project"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created repository: {repo}"))
        else:
            self.stdout.write(f"Repository '{repo}' already exists")

        pr, created = PullRequest.objects.get_or_create(
            repo=repo,
            head_branch="feature/validation",
            defaults={
                "title": "Add input validation to login flow",
                "description": (
                    "This PR adds server-side input validation to the login endpoint.\n\n"
                    "Changes:\n"
                    "- Added null/empty check in login view before hitting the database\n"
                    "- Created a dedicated validators module with email and password rules\n"
                    "- Added test coverage for the new validation paths\n\n"
                    "Resolves #42"
                ),
                "base_branch": "main",
                "author": demo_user,
                "status": "draft",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created PR #{pr.pk}: {pr.title}"))
        else:
            self.stdout.write(f"PR #{pr.pk} already exists")

        commit_sha = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        commit, created = Commit.objects.get_or_create(
            pr=pr,
            sha=commit_sha,
            defaults={
                "message": "feat: add input validation to login view and new validator module",
                "author": demo_user,
                "committed_at": timezone.now(),
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created commit: {commit_sha[:7]}"))
        else:
            self.stdout.write(f"Commit {commit_sha[:7]} already exists")

        df1, created = DiffFile.objects.get_or_create(
            commit=commit,
            file_path="auth/views.py",
            defaults={
                "change_type": "modified",
                "patch": [
                    {
                        "old_start": 12,
                        "old_lines": 8,
                        "new_start": 12,
                        "new_lines": 14,
                        "lines": [
                            {"content": "from django.contrib.auth import authenticate", "line_type": "context", "old_lineno": 12, "new_lineno": 12},
                            {"content": "from django.http import JsonResponse", "line_type": "context", "old_lineno": 13, "new_lineno": 13},
                            {"content": "", "line_type": "context", "old_lineno": 14, "new_lineno": 14},
                            {"content": "", "line_type": "context", "old_lineno": 15, "new_lineno": 15},
                            {"content": "def login_view(request):", "line_type": "context", "old_lineno": 16, "new_lineno": 16},
                            {"content": "    username = request.POST.get('username')", "line_type": "removed", "old_lineno": 17, "new_lineno": None},
                            {"content": "    password = request.POST.get('password')", "line_type": "removed", "old_lineno": 18, "new_lineno": None},
                            {"content": "    user = authenticate(username=username, password=password)", "line_type": "removed", "old_lineno": 19, "new_lineno": None},
                            {"content": "    username = request.POST.get('username', '').strip()", "line_type": "added", "old_lineno": None, "new_lineno": 17},
                            {"content": "    password = request.POST.get('password', '')", "line_type": "added", "old_lineno": None, "new_lineno": 18},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 19},
                            {"content": "    if not username or not password:", "line_type": "added", "old_lineno": None, "new_lineno": 20},
                            {"content": "        return JsonResponse({'error': 'Username and password are required.'}, status=400)", "line_type": "added", "old_lineno": None, "new_lineno": 21},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 22},
                            {"content": "    user = authenticate(username=username, password=password)", "line_type": "added", "old_lineno": None, "new_lineno": 23},
                            {"content": "    if user is not None:", "line_type": "context", "old_lineno": 20, "new_lineno": 24},
                            {"content": "        login(request, user)", "line_type": "context", "old_lineno": 21, "new_lineno": 25},
                        ],
                    }
                ],
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("  Created diff: auth/views.py (modified)"))

        df2, created = DiffFile.objects.get_or_create(
            commit=commit,
            file_path="auth/validators.py",
            defaults={
                "change_type": "added",
                "patch": [
                    {
                        "old_start": 0,
                        "old_lines": 0,
                        "new_start": 1,
                        "new_lines": 18,
                        "lines": [
                            {"content": "import re", "line_type": "added", "old_lineno": None, "new_lineno": 1},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 2},
                            {"content": "EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$')", "line_type": "added", "old_lineno": None, "new_lineno": 3},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 4},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 5},
                            {"content": "def validate_email(email):", "line_type": "added", "old_lineno": None, "new_lineno": 6},
                            {"content": "    if not email or not isinstance(email, str):", "line_type": "added", "old_lineno": None, "new_lineno": 7},
                            {"content": "        return False", "line_type": "added", "old_lineno": None, "new_lineno": 8},
                            {"content": "    return bool(EMAIL_REGEX.match(email))", "line_type": "added", "old_lineno": None, "new_lineno": 9},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 10},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 11},
                            {"content": "def validate_password(password, min_length=8):", "line_type": "added", "old_lineno": None, "new_lineno": 12},
                            {"content": "    if not password or len(password) < min_length:", "line_type": "added", "old_lineno": None, "new_lineno": 13},
                            {"content": "        return False", "line_type": "added", "old_lineno": None, "new_lineno": 14},
                            {"content": "    if not re.search(r'[A-Z]', password):", "line_type": "added", "old_lineno": None, "new_lineno": 15},
                            {"content": "        return False", "line_type": "added", "old_lineno": None, "new_lineno": 16},
                            {"content": "    if not re.search(r'[0-9]', password):", "line_type": "added", "old_lineno": None, "new_lineno": 17},
                            {"content": "        return False", "line_type": "added", "old_lineno": None, "new_lineno": 18},
                            {"content": "    return True", "line_type": "added", "old_lineno": None, "new_lineno": 19},
                        ],
                    }
                ],
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("  Created diff: auth/validators.py (added)"))

        df3, created = DiffFile.objects.get_or_create(
            commit=commit,
            file_path="auth/tests.py",
            defaults={
                "change_type": "modified",
                "patch": [
                    {
                        "old_start": 45,
                        "old_lines": 4,
                        "new_start": 45,
                        "new_lines": 20,
                        "lines": [
                            {"content": "class TestLoginView(TestCase):", "line_type": "context", "old_lineno": 45, "new_lineno": 45},
                            {"content": "    def test_valid_login(self):", "line_type": "context", "old_lineno": 46, "new_lineno": 46},
                            {"content": "        response = self.client.post('/login/', {'username': 'alice', 'password': 'Secret1'})", "line_type": "context", "old_lineno": 47, "new_lineno": 47},
                            {"content": "        self.assertEqual(response.status_code, 200)", "line_type": "context", "old_lineno": 48, "new_lineno": 48},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 49},
                            {"content": "    def test_empty_username_rejected(self):", "line_type": "added", "old_lineno": None, "new_lineno": 50},
                            {"content": "        response = self.client.post('/login/', {'username': '', 'password': 'Secret1'})", "line_type": "added", "old_lineno": None, "new_lineno": 51},
                            {"content": "        self.assertEqual(response.status_code, 400)", "line_type": "added", "old_lineno": None, "new_lineno": 52},
                            {"content": "        self.assertIn('error', response.json())", "line_type": "added", "old_lineno": None, "new_lineno": 53},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 54},
                            {"content": "    def test_empty_password_rejected(self):", "line_type": "added", "old_lineno": None, "new_lineno": 55},
                            {"content": "        response = self.client.post('/login/', {'username': 'alice', 'password': ''})", "line_type": "added", "old_lineno": None, "new_lineno": 56},
                            {"content": "        self.assertEqual(response.status_code, 400)", "line_type": "added", "old_lineno": None, "new_lineno": 57},
                            {"content": "", "line_type": "added", "old_lineno": None, "new_lineno": 58},
                            {"content": "    def test_missing_fields_rejected(self):", "line_type": "added", "old_lineno": None, "new_lineno": 59},
                            {"content": "        response = self.client.post('/login/', {})", "line_type": "added", "old_lineno": None, "new_lineno": 60},
                            {"content": "        self.assertEqual(response.status_code, 400)", "line_type": "added", "old_lineno": None, "new_lineno": 61},
                        ],
                    }
                ],
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("  Created diff: auth/tests.py (modified)"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Repository:  {repo.owner.username}/{repo.name} (id={repo.pk})")
        self.stdout.write(f"  PR:          #{pr.pk} — {pr.title} (status={pr.status})")
        self.stdout.write(f"  Commit:      {commit_sha[:7]} with 3 diff files")
        self.stdout.write(f"  Diff files:  auth/views.py, auth/validators.py, auth/tests.py")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Login credentials:"))
        self.stdout.write(f"  Demo user:     username=demo       password=demopass123")
        self.stdout.write(f"  Reviewer user: username=reviewer1  password=reviewpass123")
        self.stdout.write(f"  AI bot:        username=ai-reviewer (no password, system account)")
