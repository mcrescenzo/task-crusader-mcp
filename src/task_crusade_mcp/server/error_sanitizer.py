"""
Error Sanitization Utility for MCP Server.

Sanitizes error messages by removing sensitive information such as database
connection strings, file paths, and authentication tokens.
"""

import re
from typing import Any, Dict

# Regex patterns for sensitive data detection
PATTERNS = {
    "db_connection": [
        r"sqlite:///[^\s\"']+",
        r"postgresql://[^\s\"']+",
        r"mysql://[^\s\"']+",
        r"mongodb://[^\s\"']+",
        r"redis://[^\s\"']+",
    ],
    "file_paths": [
        r"/[\w\-./]+/[\w\-./]+",
        r"[A-Z]:\\[\w\-\\./]+",
        r"\./[\w\-./]+",
        r"\.\./[\w\-./]+",
    ],
    "auth_tokens": [
        r"token[=:]\s*['\"]?[\w\-._]+['\"]?",
        r"api[_-]?key[=:]\s*['\"]?[\w\-._]+['\"]?",
        r"password[=:]\s*['\"]?[^\s\"']+['\"]?",
        r"secret[=:]\s*['\"]?[\w\-._]+['\"]?",
        r"bearer\s+[\w\-._]+",
    ],
}

REPLACEMENTS = {
    "db_connection": "[REDACTED_DB_CONNECTION]",
    "file_paths": "[REDACTED_PATH]",
    "auth_tokens": "[REDACTED_CREDENTIAL]",
}


def sanitize_error_message(message: str) -> str:
    """Sanitize an error message by removing sensitive information."""
    sanitized = message
    for category, patterns in PATTERNS.items():
        replacement = REPLACEMENTS[category]
        for pattern in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize a dictionary by removing sensitive information from values."""
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_error_message(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                (
                    sanitize_error_message(item)
                    if isinstance(item, str)
                    else sanitize_dict(item) if isinstance(item, dict) else item
                )
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def sanitize_exception(exception: Exception) -> str:
    """Sanitize an exception by removing sensitive information from its message."""
    exception_type = type(exception).__name__
    exception_message = str(exception)
    sanitized_message = sanitize_error_message(exception_message)
    return f"{exception_type}: {sanitized_message}"
