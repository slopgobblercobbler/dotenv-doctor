"""Rule definitions and detectors for dotenv linting and security scanning."""
from __future__ import annotations

import re
from typing import List, Set
from dotenv_doctor.models import EnvEntry, EnvFile, Issue, LineType, Severity

VALID_KEY_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

SECRET_KEY_KEYWORDS = {
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "PASS",
    "TOKEN",
    "API_KEY",
    "APIKEY",
    "AUTH",
    "PRIVATE_KEY",
    "CREDENTIAL",
    "CREDENTIALS",
    "CERTIFICATE",
    "CLIENT_SECRET",
    "ACCESS_TOKEN",
    "ENCRYPTION_KEY",
    "SIGNING_KEY",
}

DEFAULT_WEAK_SECRETS = {
    "123456",
    "12345678",
    "123456789",
    "password",
    "p@ssword",
    "passwd",
    "admin",
    "root",
    "secret",
    "mysecret",
    "mysecretkey",
    "changeme",
    "change_me",
    "change-me",
    "replace_me",
    "replace-me",
    "todo",
    "your_key_here",
    "your-key-here",
    "your_secret_here",
    "your-api-key",
    "your-api-key-here",
    "dummy",
    "test",
    "testing",
    "dev",
    "development",
    "example",
    "sample",
    "xxx",
    "foobar",
    "qwerty",
}


def rule_syntax_error(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for syntax errors such as lines without '=' or unclosed quotes."""
    if "syntax-error" in ignored and "unclosed-quote" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if entry.line_type == LineType.SYNTAX_ERROR:
            if entry.quote_char:
                if "unclosed-quote" not in ignored:
                    issues.append(
                        Issue(
                            rule_id="unclosed-quote",
                            message=f"Unclosed {entry.quote_char} quote starting on line {entry.line_number}",
                            severity=Severity.ERROR,
                            file_path=env.file_path,
                            line_number=entry.line_number,
                            key=entry.key,
                            suggestion="Close the quote or escape internal quote characters.",
                        )
                    )
            else:
                if "syntax-error" not in ignored:
                    issues.append(
                        Issue(
                            rule_id="syntax-error",
                            message=f"Syntax error: line is not a comment and missing '=' separator: {entry.raw_line.strip()}",
                            severity=Severity.ERROR,
                            file_path=env.file_path,
                            line_number=entry.line_number,
                            suggestion="Ensure line is in format KEY=value or starts with '#' for comments.",
                        )
                    )
    return issues


def rule_invalid_key_name(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check that key names follow standard identifier conventions."""
    if "invalid-key-name" in ignored and "lowercase-key" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if not entry.is_variable or not entry.key:
            continue

        key = entry.key
        if "invalid-key-name" not in ignored and not VALID_KEY_REGEX.match(key):
            issues.append(
                Issue(
                    rule_id="invalid-key-name",
                    message=f"Invalid variable name '{key}'. Keys must start with a letter or underscore and contain only alphanumeric characters and underscores.",
                    severity=Severity.ERROR,
                    file_path=env.file_path,
                    line_number=entry.line_number,
                    key=key,
                    suggestion=f"Rename '{key}' to valid identifier, e.g., '{re.sub(r'[^a-zA-Z0-9_]', '_', key).upper()}'.",
                )
            )

        if "lowercase-key" not in ignored and any(c.islower() for c in key):
            issues.append(
                Issue(
                    rule_id="lowercase-key",
                    message=f"Variable name '{key}' contains lowercase characters. Convention is UPPERCASE_WITH_UNDERSCORES.",
                    severity=Severity.INFO,
                    file_path=env.file_path,
                    line_number=entry.line_number,
                    key=key,
                    suggestion=f"Convert '{key}' to uppercase: '{key.upper()}'.",
                )
            )

    return issues


def rule_whitespace_around_equals(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for illegal whitespace around '=' sign."""
    if "whitespace-around-equals" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if entry.is_variable and entry.has_whitespace_around_equals:
            val_display = entry.value or ""
            issues.append(
                Issue(
                    rule_id="whitespace-around-equals",
                    message=f"Stray whitespace around '=' in '{entry.key}'. Dotenv loaders may parse spaces as part of the key or value.",
                    severity=Severity.WARNING,
                    file_path=env.file_path,
                    line_number=entry.line_number,
                    key=entry.key,
                    suggestion=f"Remove spaces around '=': '{entry.key}={val_display}'.",
                )
            )
    return issues


def rule_duplicate_keys(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for duplicate keys in the same file."""
    if "duplicate-key" in ignored:
        return []

    issues: List[Issue] = []
    for key in env.keys:
        entries = env.get_entries(key)
        if len(entries) > 1:
            values = [e.value for e in entries]
            lines = [str(e.line_number) for e in entries]
            all_same = len(set(values)) == 1
            diff_msg = "with identical values" if all_same else "with differing values"
            issues.append(
                Issue(
                    rule_id="duplicate-key",
                    message=f"Duplicate key '{key}' defined {len(entries)} times (lines {', '.join(lines)}) {diff_msg}.",
                    severity=Severity.WARNING if not all_same else Severity.INFO,
                    file_path=env.file_path,
                    line_number=entries[-1].line_number,
                    key=key,
                    suggestion="Keep only the intended definition and remove duplicates.",
                )
            )
    return issues


def rule_unescaped_values(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for unquoted values containing spaces or ambiguous characters."""
    if "unescaped-value" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if not entry.is_variable or entry.quote_char is not None or not entry.value:
            continue

        # If unquoted and contains whitespace inside
        val = entry.value
        if " " in val or "\t" in val:
            issues.append(
                Issue(
                    rule_id="unescaped-value",
                    message=f"Unquoted value for '{entry.key}' contains whitespace: '{val}'.",
                    severity=Severity.WARNING,
                    file_path=env.file_path,
                    line_number=entry.line_number,
                    key=entry.key,
                    suggestion=f'Wrap value in quotes: {entry.key}="{val}"',
                )
            )
    return issues


def rule_trailing_whitespace(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for trailing whitespace on lines."""
    if "trailing-whitespace" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if entry.raw_line != entry.raw_line.rstrip(" \t"):
            issues.append(
                Issue(
                    rule_id="trailing-whitespace",
                    message=f"Line {entry.line_number} has trailing whitespace.",
                    severity=Severity.INFO,
                    file_path=env.file_path,
                    line_number=entry.line_number,
                    suggestion="Remove trailing spaces/tabs from line.",
                )
            )
    return issues


def rule_weak_default_secrets(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for weak or default placeholder secrets."""
    if "weak-default-secret" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if not entry.is_variable or not entry.key or not entry.value:
            continue

        key_upper = entry.key.upper()
        # Check if key implies a secret
        is_secret_key = any(kw in key_upper for kw in SECRET_KEY_KEYWORDS)
        val_clean = entry.value.strip().strip("'\"`").lower()

        if is_secret_key:
            if val_clean in DEFAULT_WEAK_SECRETS or any(
                ph in val_clean for ph in ("changeme", "todo", "replace_me", "placeholder", "your-key", "your_secret")
            ):
                issues.append(
                    Issue(
                        rule_id="weak-default-secret",
                        message=f"Variable '{entry.key}' appears to contain a default or weak secret: '{entry.value}'.",
                        severity=Severity.WARNING,
                        file_path=env.file_path,
                        line_number=entry.line_number,
                        key=entry.key,
                        suggestion="Generate and configure a strong, random production secret.",
                    )
                )

    return issues


def rule_insecure_urls(env: EnvFile, ignored: Set[str]) -> List[Issue]:
    """Check for sensitive URLs using insecure http:// instead of https://."""
    if "insecure-url" in ignored:
        return []

    issues: List[Issue] = []
    for entry in env.entries:
        if not entry.is_variable or not entry.key or not entry.value:
            continue

        val = entry.value.strip()
        if val.startswith("http://") and not (
            "localhost" in val or "127.0.0.1" in val or "0.0.0.0" in val
        ):
            key_upper = entry.key.upper()
            if any(k in key_upper for k in ("API", "URL", "ENDPOINT", "AUTH", "OIDC", "HOST", "SERVER")):
                issues.append(
                    Issue(
                        rule_id="insecure-url",
                        message=f"Variable '{entry.key}' points to unencrypted HTTP endpoint: '{val}'.",
                        severity=Severity.WARNING,
                        file_path=env.file_path,
                        line_number=entry.line_number,
                        key=entry.key,
                        suggestion="Use HTTPS (https://) for external production endpoints.",
                    )
                )
    return issues


ALL_RULES = [
    rule_syntax_error,
    rule_invalid_key_name,
    rule_whitespace_around_equals,
    rule_duplicate_keys,
    rule_unescaped_values,
    rule_trailing_whitespace,
    rule_weak_default_secrets,
    rule_insecure_urls,
]
