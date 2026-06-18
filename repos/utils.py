import re
from typing import Any

# Matches: @@ -old_start,old_lines +new_start,new_lines @@
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# Matches: diff --git a/<path> b/<path>
_DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")


def _detect_change_type(header_lines: list[str]) -> str:
    for line in header_lines:
        if line.startswith("new file mode"):
            return "added"
        if line.startswith("deleted file mode"):
            return "deleted"
    return "modified"


class GitDiffParser:
    """Parse unified git diff text into structured hunk data."""

    def parse_diff(self, raw_diff_text: str) -> list[dict[str, Any]]:
        """Return one dict per changed file with its parsed hunks."""
        files: list[dict[str, Any]] = []
        if not raw_diff_text or not raw_diff_text.strip():
            return files

        # Split into per-file blocks on the "diff --git" boundary.
        blocks = re.split(r"(?=^diff --git )", raw_diff_text, flags=re.MULTILINE)
        for block in blocks:
            if not block.strip():
                continue
            parsed = self._parse_file_block(block)
            if parsed is not None:
                files.append(parsed)
        return files

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_file_block(self, block: str) -> dict[str, Any] | None:
        lines = block.splitlines()
        if not lines:
            return None

        match = _DIFF_HEADER.match(lines[0])
        if not match:
            return None

        file_path = match.group(2)  # use the "b/" side (destination)

        # Collect header metadata lines (before the first hunk).
        header_lines: list[str] = []
        hunk_start_idx = len(lines)
        for i, line in enumerate(lines[1:], start=1):
            if line.startswith("@@"):
                hunk_start_idx = i
                break
            header_lines.append(line)

        change_type = _detect_change_type(header_lines)
        hunks = self._parse_hunks(lines[hunk_start_idx:])

        return {
            "file_path": file_path,
            "change_type": change_type,
            "hunks": hunks,
        }

    def _parse_hunks(self, lines: list[str]) -> list[dict[str, Any]]:
        hunks: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        old_lineno = 0
        new_lineno = 0

        for line in lines:
            hunk_match = _HUNK_HEADER.match(line)
            if hunk_match:
                if current is not None:
                    hunks.append(current)
                old_start = int(hunk_match.group(1))
                old_lines = int(hunk_match.group(2) or 1)
                new_start = int(hunk_match.group(3))
                new_lines = int(hunk_match.group(4) or 1)
                old_lineno = old_start
                new_lineno = new_start
                current = {
                    "old_start": old_start,
                    "old_lines": old_lines,
                    "new_start": new_start,
                    "new_lines": new_lines,
                    "lines": [],
                }
                continue

            if current is None:
                continue

            if line.startswith("+") and not line.startswith("+++"):
                current["lines"].append({
                    "content": line[1:],
                    "line_type": "added",
                    "old_lineno": None,
                    "new_lineno": new_lineno,
                })
                new_lineno += 1
            elif line.startswith("-") and not line.startswith("---"):
                current["lines"].append({
                    "content": line[1:],
                    "line_type": "removed",
                    "old_lineno": old_lineno,
                    "new_lineno": None,
                })
                old_lineno += 1
            elif line.startswith(" ") or line == "":
                current["lines"].append({
                    "content": line[1:] if line.startswith(" ") else "",
                    "line_type": "context",
                    "old_lineno": old_lineno,
                    "new_lineno": new_lineno,
                })
                old_lineno += 1
                new_lineno += 1
            # Lines starting with \ (e.g. "\ No newline at end of file") are skipped.

        if current is not None:
            hunks.append(current)

        return hunks
