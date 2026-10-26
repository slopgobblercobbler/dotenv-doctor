"""Terminal and JSON formatters for diagnostics output."""
from __future__ import annotations

import json
import os
import sys
from typing import Any, List, Optional

from dotenv_doctor.checker import CheckResult
from dotenv_doctor.fixer import FixResult
from dotenv_doctor.models import Issue, Severity
from dotenv_doctor.syncer import SyncResult


class Color:
    """ANSI color codes with automatic detection and suppression."""
    ENABLED = True

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    DIM = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def set_color(cls, enabled: bool) -> None:
        cls.ENABLED = enabled

    @classmethod
    def paint(cls, text: str, code: str) -> str:
        if not cls.ENABLED or "NO_COLOR" in os.environ:
            return text
        return f"{code}{text}{cls.RESET}"

    @classmethod
    def red(cls, text: str) -> str:
        return cls.paint(text, cls.RED)

    @classmethod
    def green(cls, text: str) -> str:
        return cls.paint(text, cls.GREEN)

    @classmethod
    def yellow(cls, text: str) -> str:
        return cls.paint(text, cls.YELLOW)

    @classmethod
    def cyan(cls, text: str) -> str:
        return cls.paint(text, cls.CYAN)

    @classmethod
    def dim(cls, text: str) -> str:
        return cls.paint(text, cls.DIM)

    @classmethod
    def bold(cls, text: str) -> str:
        return cls.paint(text, cls.BOLD)


def format_issues(issues: List[Issue], output_format: str = "pretty") -> str:
    """Format a list of linting issues."""
    if output_format == "json":
        return json.dumps([i.to_dict() for i in issues], indent=2)

    if not issues:
        return Color.green("✓ No issues found! All checks passed.")

    lines = []
    if output_format == "simple":
        for issue in issues:
            pos = f"{issue.file_path or '<input>'}:{issue.line_number or 1}"
            sev = issue.severity.value.upper()
            lines.append(f"{pos}: [{sev}] ({issue.rule_id}) {issue.message}")
        return "\n".join(lines)

    # Pretty output format
    current_file = None
    for issue in issues:
        if issue.file_path != current_file:
            current_file = issue.file_path
            lines.append(f"\n{Color.bold(Color.cyan(current_file or '<unknown>'))}:")

        if issue.severity == Severity.ERROR:
            tag = Color.bold(Color.red("✖ ERROR  "))
        elif issue.severity == Severity.WARNING:
            tag = Color.bold(Color.yellow("⚠ WARNING"))
        else:
            tag = Color.bold(Color.dim("ℹ INFO   "))

        loc = f"Line {issue.line_number:3d}:" if issue.line_number is not None else "        :"
        lines.append(f"  {Color.dim(loc)} {tag} {issue.message} {Color.dim(f'[{issue.rule_id}]')}")
        if issue.suggestion:
            lines.append(f"            {Color.dim('↳ Suggestion: ' + issue.suggestion)}")

    # Summary
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)
    parts = []
    if errors:
        parts.append(Color.red(f"{errors} error(s)"))
    if warnings:
        parts.append(Color.yellow(f"{warnings} warning(s)"))
    if infos:
        parts.append(Color.dim(f"{infos} info"))

    lines.append(f"\n{Color.bold('Found: ' + ', '.join(parts))}")
    return "\n".join(lines)


def format_check_result(result: CheckResult, output_format: str = "pretty") -> str:
    """Format result from environment comparison check."""
    if output_format == "json":
        return json.dumps(result.to_dict(), indent=2)

    if result.is_clean:
        return Color.green(
            f"✓ Environment '{result.target_path}' is in sync with '{result.reference_path}'! No missing variables."
        )

    lines = []
    lines.append(Color.bold(f"Comparing '{result.target_path}' with template '{result.reference_path}':\n"))

    if result.missing_keys:
        lines.append(Color.bold(Color.red(f"  ✖ Missing variables ({len(result.missing_keys)}):")))
        for k in result.missing_keys:
            lines.append(f"    - {Color.red(k)}")

    if result.extra_keys:
        lines.append(Color.bold(Color.yellow(f"  ⚠ Extra undocumented variables ({len(result.extra_keys)}):")))
        for k in result.extra_keys:
            lines.append(f"    - {Color.yellow(k)}")

    if result.empty_keys:
        lines.append(Color.bold(Color.yellow(f"  ⚠ Variables with empty values ({len(result.empty_keys)}):")))
        for k in result.empty_keys:
            lines.append(f"    - {Color.yellow(k)}")

    if result.unmodified_defaults:
        lines.append(Color.bold(Color.yellow(f"  ⚠ Unmodified example placeholders ({len(result.unmodified_defaults)}):")))
        for k in result.unmodified_defaults:
            lines.append(f"    - {Color.yellow(k)}")

    # Add any syntax errors
    syntax_issues = [i for i in result.issues if i.rule_id in ("syntax-error", "unclosed-quote", "missing-target", "missing-reference")]
    if syntax_issues:
        lines.append(Color.bold(Color.red("\n  ✖ Syntax or File Errors:")))
        for i in syntax_issues:
            lines.append(f"    - {i.message}")

    lines.append("")
    if result.has_errors:
        lines.append(Color.bold(Color.red("FAILED: Target environment has missing or invalid variables.")))
        lines.append(Color.dim(f"Run 'dotenv-doctor sync {result.target_path} {result.reference_path}' to synchronize."))
    else:
        lines.append(Color.bold(Color.yellow("WARNINGS: All required variables are present, but discrepancies were noted.")))

    return "\n".join(lines)


def format_sync_result(result: SyncResult, output_format: str = "pretty") -> str:
    """Format result from sync operation."""
    if output_format == "json":
        return json.dumps(result.to_dict(), indent=2)

    if not result.modified:
        return Color.green(f"✓ '{result.target_path}' is already fully synchronized with '{result.reference_path}'.")

    lines = []
    if result.created_new:
        lines.append(Color.green(f"✓ Created new environment file '{result.target_path}' from '{result.reference_path}'."))
    else:
        lines.append(Color.green(f"✓ Updated '{result.target_path}'."))

    if result.added_keys:
        lines.append(Color.bold(f"  Added ({len(result.added_keys)}): {', '.join(result.added_keys)}"))

    if result.pruned_keys:
        lines.append(Color.bold(f"  Pruned ({len(result.pruned_keys)}): {', '.join(result.pruned_keys)}"))

    if result.backup_path:
        lines.append(Color.dim(f"  Backup created: {result.backup_path}"))

    if result.diff:
        lines.append(Color.dim("\nChanges:"))
        for dline in result.diff.splitlines():
            if dline.startswith("+"):
                lines.append(Color.green(dline))
            elif dline.startswith("-"):
                lines.append(Color.red(dline))
            else:
                lines.append(Color.dim(dline))

    return "\n".join(lines)


def format_fix_result(result: FixResult, output_format: str = "pretty") -> str:
    """Format result from automated fix operation."""
    if output_format == "json":
        return json.dumps(result.to_dict(), indent=2)

    if not result.modified:
        return Color.green(f"✓ No issues to fix in '{result.file_path}'. File is already clean.")

    lines = []
    lines.append(Color.green(f"✓ Fixed {result.fixed_issues_count} issue(s) in '{result.file_path}':"))
    for desc in result.descriptions:
        lines.append(f"  - {desc}")

    if result.backup_path:
        lines.append(Color.dim(f"  Backup created: {result.backup_path}"))

    if result.diff:
        lines.append(Color.dim("\nDiff:"))
        for dline in result.diff.splitlines():
            if dline.startswith("+"):
                lines.append(Color.green(dline))
            elif dline.startswith("-"):
                lines.append(Color.red(dline))
            else:
                lines.append(Color.dim(dline))

    return "\n".join(lines)
