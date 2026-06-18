import pytest

from repos.utils import GitDiffParser


@pytest.fixture
def parser():
    return GitDiffParser()


# ---------------------------------------------------------------------------
# Fixtures — raw diff strings
# ---------------------------------------------------------------------------

SINGLE_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
index 0000001..0000002 100644
--- a/foo.py
+++ b/foo.py
@@ -1,4 +1,4 @@
 def greet(name):
-    print("hello " + name)
+    print(f"hello {name}")
     return True
"""

MULTI_FILE_DIFF = """\
diff --git a/a.py b/a.py
index 1111111..2222222 100644
--- a/a.py
+++ b/a.py
@@ -1,3 +1,4 @@
 x = 1
+y = 2
 z = 3
diff --git a/b.py b/b.py
index 3333333..4444444 100644
--- a/b.py
+++ b/b.py
@@ -1,2 +1,2 @@
-old = True
+new = False
"""

ADDED_FILE_DIFF = """\
diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..aaaaaaa
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,2 @@
+class Foo:
+    pass
"""

DELETED_FILE_DIFF = """\
diff --git a/gone.py b/gone.py
deleted file mode 100644
index bbbbbbb..0000000
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-class Bar:
-    pass
"""

MULTI_HUNK_DIFF = """\
diff --git a/big.py b/big.py
index ccccccc..ddddddd 100644
--- a/big.py
+++ b/big.py
@@ -1,4 +1,4 @@
 line1
-line2
+line2_changed
 line3
 line4
@@ -10,4 +10,4 @@
 line10
 line11
-line12
+line12_changed
 line13
"""


# ---------------------------------------------------------------------------
# Single-file parsing
# ---------------------------------------------------------------------------

class TestSingleFileDiff:
    def test_returns_one_file(self, parser):
        result = parser.parse_diff(SINGLE_FILE_DIFF)
        assert len(result) == 1

    def test_file_path(self, parser):
        result = parser.parse_diff(SINGLE_FILE_DIFF)
        assert result[0]["file_path"] == "foo.py"

    def test_change_type_modified(self, parser):
        result = parser.parse_diff(SINGLE_FILE_DIFF)
        assert result[0]["change_type"] == "modified"

    def test_one_hunk(self, parser):
        result = parser.parse_diff(SINGLE_FILE_DIFF)
        assert len(result[0]["hunks"]) == 1

    def test_hunk_header_values(self, parser):
        hunk = parser.parse_diff(SINGLE_FILE_DIFF)[0]["hunks"][0]
        assert hunk["old_start"] == 1
        assert hunk["new_start"] == 1

    def test_line_count_in_hunk(self, parser):
        lines = parser.parse_diff(SINGLE_FILE_DIFF)[0]["hunks"][0]["lines"]
        # 1 context + 1 removed + 1 added + 1 context
        assert len(lines) == 4

    def test_context_line(self, parser):
        lines = parser.parse_diff(SINGLE_FILE_DIFF)[0]["hunks"][0]["lines"]
        assert lines[0]["line_type"] == "context"
        assert lines[0]["content"] == 'def greet(name):'

    def test_removed_line(self, parser):
        lines = parser.parse_diff(SINGLE_FILE_DIFF)[0]["hunks"][0]["lines"]
        removed = [l for l in lines if l["line_type"] == "removed"]
        assert len(removed) == 1
        assert removed[0]["content"] == '    print("hello " + name)'
        assert removed[0]["new_lineno"] is None
        assert removed[0]["old_lineno"] == 2

    def test_added_line(self, parser):
        lines = parser.parse_diff(SINGLE_FILE_DIFF)[0]["hunks"][0]["lines"]
        added = [l for l in lines if l["line_type"] == "added"]
        assert len(added) == 1
        assert added[0]["content"] == '    print(f"hello {name}")'
        assert added[0]["old_lineno"] is None
        assert added[0]["new_lineno"] == 2


# ---------------------------------------------------------------------------
# Multi-file parsing
# ---------------------------------------------------------------------------

class TestMultiFileDiff:
    def test_returns_two_files(self, parser):
        result = parser.parse_diff(MULTI_FILE_DIFF)
        assert len(result) == 2

    def test_file_paths(self, parser):
        result = parser.parse_diff(MULTI_FILE_DIFF)
        paths = [f["file_path"] for f in result]
        assert "a.py" in paths
        assert "b.py" in paths

    def test_both_modified(self, parser):
        result = parser.parse_diff(MULTI_FILE_DIFF)
        assert all(f["change_type"] == "modified" for f in result)

    def test_added_line_in_first_file(self, parser):
        result = parser.parse_diff(MULTI_FILE_DIFF)
        a = next(f for f in result if f["file_path"] == "a.py")
        added = [l for l in a["hunks"][0]["lines"] if l["line_type"] == "added"]
        assert len(added) == 1
        assert added[0]["content"] == "y = 2"

    def test_removed_line_in_second_file(self, parser):
        result = parser.parse_diff(MULTI_FILE_DIFF)
        b = next(f for f in result if f["file_path"] == "b.py")
        removed = [l for l in b["hunks"][0]["lines"] if l["line_type"] == "removed"]
        assert len(removed) == 1
        assert removed[0]["content"] == "old = True"


# ---------------------------------------------------------------------------
# Added / deleted / modified detection
# ---------------------------------------------------------------------------

class TestChangeTypeDetection:
    def test_new_file_is_added(self, parser):
        result = parser.parse_diff(ADDED_FILE_DIFF)
        assert result[0]["change_type"] == "added"

    def test_deleted_file_is_deleted(self, parser):
        result = parser.parse_diff(DELETED_FILE_DIFF)
        assert result[0]["change_type"] == "deleted"

    def test_added_file_has_only_added_lines(self, parser):
        lines = parser.parse_diff(ADDED_FILE_DIFF)[0]["hunks"][0]["lines"]
        assert all(l["line_type"] == "added" for l in lines)

    def test_deleted_file_has_only_removed_lines(self, parser):
        lines = parser.parse_diff(DELETED_FILE_DIFF)[0]["hunks"][0]["lines"]
        assert all(l["line_type"] == "removed" for l in lines)

    def test_added_lines_have_no_old_lineno(self, parser):
        lines = parser.parse_diff(ADDED_FILE_DIFF)[0]["hunks"][0]["lines"]
        assert all(l["old_lineno"] is None for l in lines)

    def test_removed_lines_have_no_new_lineno(self, parser):
        lines = parser.parse_diff(DELETED_FILE_DIFF)[0]["hunks"][0]["lines"]
        assert all(l["new_lineno"] is None for l in lines)


# ---------------------------------------------------------------------------
# Multi-hunk parsing
# ---------------------------------------------------------------------------

class TestMultiHunkDiff:
    def test_two_hunks(self, parser):
        result = parser.parse_diff(MULTI_HUNK_DIFF)
        assert len(result[0]["hunks"]) == 2

    def test_second_hunk_start(self, parser):
        hunk2 = parser.parse_diff(MULTI_HUNK_DIFF)[0]["hunks"][1]
        assert hunk2["old_start"] == 10
        assert hunk2["new_start"] == 10


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string_returns_empty_list(self, parser):
        assert parser.parse_diff("") == []

    def test_whitespace_only_returns_empty_list(self, parser):
        assert parser.parse_diff("   \n  ") == []
