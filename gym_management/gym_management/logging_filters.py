"""
Structured logging utilities:
- SensitiveDataFilter: redacts passwords, tokens, secrets from log records.
- JSONFormatter: outputs log records as single-line JSON for machine ingestion.
"""
import json
import logging
import re
from datetime import datetime, timezone


# Patterns that indicate sensitive data in log messages or record attributes
SENSITIVE_PATTERNS = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|api_key|access_token|refresh_token"
    r"|mfa_token|encrypted_secret|backup_codes?|client_secret|private_key)"
    r"\s*[=:]\s*\S+",
    re.IGNORECASE,
)

# Keys to redact when they appear in structured log data
SENSITIVE_KEYS = frozenset({
    "password", "new_password", "old_password", "confirm_password",
    "token", "access_token", "refresh_token", "mfa_token",
    "secret", "client_secret", "api_key", "authorization",
    "encrypted_secret", "backup_codes",
})

REDACTED = "***REDACTED***"


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that scrubs sensitive data from log messages and record args.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact message string
        if record.msg and isinstance(record.msg, str):
            record.msg = SENSITIVE_PATTERNS.sub(self._redact_match, record.msg)

        # Redact args if they are dicts (structured logging)
        if isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)

        return True

    @staticmethod
    def _redact_match(match: re.Match) -> str:
        key_part = match.group(0).split("=")[0].split(":")[0]
        return f"{key_part.strip()}={REDACTED}"

    @staticmethod
    def _redact_dict(data: dict) -> dict:
        cleaned = {}
        for key, value in data.items():
            if key.lower() in SENSITIVE_KEYS:
                cleaned[key] = REDACTED
            elif isinstance(value, dict):
                cleaned[key] = SensitiveDataFilter._redact_dict(value)
            else:
                cleaned[key] = value
        return cleaned


class JSONFormatter(logging.Formatter):
    """
    Outputs log records as single-line JSON objects suitable for
    structured log aggregation (CloudWatch, ELK, Datadog, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include extra fields passed via `extra={}` in logging calls
        for key in ("user_id", "ip", "event", "request_id", "status_code"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry, default=str)
