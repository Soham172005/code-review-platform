import json

import structlog
from django.conf import settings

log = structlog.get_logger()

SYSTEM_PROMPT = (
    "You are an expert code reviewer. Analyze the provided diff and "
    "return a JSON array of review comments. Each comment must have: "
    "file_path (string), line_position (integer), body (the review comment), "
    "severity (info/warning/error). Focus on: bugs, security issues, "
    "performance problems, and code quality. Return ONLY valid JSON, "
    "no markdown, no explanation."
)

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "comments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "line_position": {"type": "integer"},
                    "body": {"type": "string"},
                    "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                },
                "required": ["file_path", "line_position", "body", "severity"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["comments"],
    "additionalProperties": False,
}


class AIReviewer:
    def __init__(self):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def review_diff(self, pr_title, pr_description, diff_files):
        diff_text = self._format_diff_for_prompt(diff_files)
        if not diff_text.strip():
            return []

        user_message = (
            f"PR Title: {pr_title}\n"
            f"PR Description: {pr_description or 'No description'}\n\n"
            f"Diff:\n{diff_text}"
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": REVIEW_SCHEMA,
                    }
                },
                messages=[{"role": "user", "content": user_message}],
            )
            return self._parse_review_response(response)
        except Exception:
            log.exception("ai_review_failed", exc_info=True)
            return []

    def _format_diff_for_prompt(self, diff_files):
        parts = []
        for df in diff_files:
            header = f"--- {df.change_type}: {df.file_path} ---"
            lines = []
            for hunk in df.patch or []:
                for line in hunk.get("lines", []):
                    prefix = {"added": "+", "removed": "-", "context": " "}.get(
                        line.get("line_type", "context"), " "
                    )
                    lines.append(f"{prefix}{line.get('content', '')}")
            parts.append(header + "\n" + "\n".join(lines))
        return "\n\n".join(parts)

    def _parse_review_response(self, response):
        text = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
        if not text:
            return []
        try:
            data = json.loads(text)
            return data.get("comments", [])
        except (json.JSONDecodeError, AttributeError):
            log.warning("ai_review_parse_failed")
            return []


class MockAIReviewer:
    def review_diff(self, pr_title, pr_description, diff_files):
        file_paths = [df.file_path for df in diff_files]
        target = file_paths[0] if file_paths else "unknown.py"
        return [
            {
                "file_path": target,
                "line_position": 3,
                "body": "Consider adding input validation here to guard against unexpected values.",
                "severity": "warning",
            },
            {
                "file_path": target,
                "line_position": 10,
                "body": "This variable is unused and can be removed.",
                "severity": "info",
            },
            {
                "file_path": target,
                "line_position": 17,
                "body": "Potential null reference — this value can be None when the queryset is empty.",
                "severity": "error",
            },
        ]
