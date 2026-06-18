import json

from django.core.management.base import BaseCommand

from repos.utils import GitDiffParser

SAMPLE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
index 1a2b3c4..5d6e7f8 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,7 +1,10 @@
 import hashlib
+import secrets

 def authenticate(username, password):
-    hashed = hashlib.md5(password.encode()).hexdigest()
+    # Use a timing-safe comparison
+    hashed = hashlib.sha256(password.encode()).hexdigest()
+    return secrets.compare_digest(hashed, get_stored_hash(username))
-    return hashed == get_stored_hash(username)

 def get_stored_hash(username):
     return DB.get(username, {}).get("password_hash", "")
diff --git a/src/models.py b/src/models.py
new file mode 100644
index 0000000..abcdef1
--- /dev/null
+++ b/src/models.py
@@ -0,0 +1,5 @@
+class User:
+    def __init__(self, username, email):
+        self.username = username
+        self.email = email
+
diff --git a/src/legacy.py b/src/legacy.py
deleted file mode 100644
index abcdef1..0000000
--- a/src/legacy.py
+++ /dev/null
@@ -1,3 +0,0 @@
-# This module is no longer used
-def old_function():
-    pass
"""


class Command(BaseCommand):
    help = "Parse a hardcoded sample diff and print the structured output as JSON"

    def handle(self, *args, **options):
        parser = GitDiffParser()
        result = parser.parse_diff(SAMPLE_DIFF)
        self.stdout.write(json.dumps(result, indent=2))
