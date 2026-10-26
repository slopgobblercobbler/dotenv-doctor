"""Tests for output formatters and terminal color handling."""
import os
import json
from dotenv_doctor.formatter import (
    Color,
    format_issues,
    format_check_result,
    format_sync_result,
    format_fix_result,
)
from dotenv_doctor.models import Issue, Severity
from dotenv_doctor.checker import CheckResult
from dotenv_doctor.syncer import SyncResult
from dotenv_doctor.fixer import FixResult


def test_color_toggle():
    Color.set_color(True)
    res = Color.paint("hello", Color.RED)
    assert "\033[91m" in res

    Color.set_color(False)
    assert Color.paint("hello", Color.RED) == "hello"
    assert Color.red("test") == "test"
    assert Color.green("test") == "test"
    assert Color.yellow("test") == "test"
    assert Color.cyan("test") == "test"
    assert Color.dim("test") == "test"
    assert Color.bold("test") == "test"

    # Restore color
    Color.set_color(True)


def test_color_no_color_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    Color.set_color(True)
    assert Color.paint("hello", Color.RED) == "hello"


def test_format_issues_empty():
    res = format_issues([], output_format="pretty")
    assert "No issues found" in res

    json_res = format_issues([], output_format="json")
    assert json.loads(json_res) == []


def test_format_issues_simple_and_pretty():
    issues = [
        Issue(
            rule_id="weak-default-secret",
            message="Weak secret detected",
            severity=Severity.WARNING,
            file_path=".env",
            line_number=2,
            key="SECRET_KEY",
            suggestion="Use random secret",
        ),
        Issue(
            rule_id="syntax-error",
            message="No equals sign",
            severity=Severity.ERROR,
            file_path=".env",
            line_number=5,
        ),
        Issue(
            rule_id="lowercase-key",
            message="Lowercase variable name",
            severity=Severity.INFO,
            file_path=".env",
            line_number=7,
            key="foo",
        ),
    ]

    simple_out = format_issues(issues, output_format="simple")
    assert ".env:2: [WARNING] (weak-default-secret)" in simple_out
    assert ".env:5: [ERROR] (syntax-error)" in simple_out
    assert ".env:7: [INFO] (lowercase-key)" in simple_out

    pretty_out = format_issues(issues, output_format="pretty")
    assert "Line   2:" in pretty_out
    assert "WARNING" in pretty_out
    assert "Suggestion: Use random secret" in pretty_out
    assert "Found:" in pretty_out
    assert "1 error(s)" in pretty_out
    assert "1 warning(s)" in pretty_out
    assert "1 info" in pretty_out

    json_out = format_issues(issues, output_format="json")
    data = json.loads(json_out)
    assert len(data) == 3
    assert data[0]["rule_id"] == "weak-default-secret"


def test_format_check_result_clean():
    res = CheckResult(
        target_path=".env",
        reference_path=".env.example",
    )
    assert res.is_clean is True
    formatted = format_check_result(res, output_format="pretty")
    assert "is in sync with" in formatted

    json_out = format_check_result(res, output_format="json")
    data = json.loads(json_out)
    assert data["is_clean"] is True


def test_format_check_result_discrepancies():
    issues = [
        Issue(
            rule_id="syntax-error",
            message="Corrupted line in .env",
            severity=Severity.ERROR,
            file_path=".env",
            line_number=1,
        )
    ]
    res = CheckResult(
        target_path=".env",
        reference_path=".env.example",
        missing_keys=["DATABASE_URL"],
        extra_keys=["EXTRA_DEBUG"],
        empty_keys=["CACHE_URL"],
        unmodified_defaults=["API_TOKEN"],
        issues=issues,
    )
    pretty = format_check_result(res, output_format="pretty")
    assert "Missing variables (1):" in pretty
    assert "DATABASE_URL" in pretty
    assert "Extra undocumented variables (1):" in pretty
    assert "EXTRA_DEBUG" in pretty
    assert "Variables with empty values (1):" in pretty
    assert "CACHE_URL" in pretty
    assert "Unmodified example placeholders (1):" in pretty
    assert "API_TOKEN" in pretty
    assert "Syntax or File Errors:" in pretty
    assert "FAILED:" in pretty

    # Warning only check
    res_warn = CheckResult(
        target_path=".env",
        reference_path=".env.example",
        extra_keys=["EXTRA_DEBUG"],
    )
    warn_pretty = format_check_result(res_warn, output_format="pretty")
    assert "WARNINGS:" in warn_pretty


def test_format_sync_result():
    res_unmod = SyncResult(
        target_path=".env",
        reference_path=".env.example",
        modified=False,
    )
    assert "already fully synchronized" in format_sync_result(res_unmod, output_format="pretty")
    json_data = json.loads(format_sync_result(res_unmod, output_format="json"))
    assert json_data["modified"] is False

    res_mod = SyncResult(
        target_path=".env",
        reference_path=".env.example",
        modified=True,
        created_new=True,
        added_keys=["A", "B"],
        pruned_keys=["C"],
        backup_path=".env.bak",
        diff="+A=1\n-C=2\n D=3",
    )
    mod_pretty = format_sync_result(res_mod, output_format="pretty")
    assert "Created new environment file" in mod_pretty
    assert "Added (2): A, B" in mod_pretty
    assert "Pruned (1): C" in mod_pretty
    assert "Backup created: .env.bak" in mod_pretty
    assert "+A=1" in mod_pretty

    # Updated existing file
    res_mod.created_new = False
    assert "Updated '.env'." in format_sync_result(res_mod, output_format="pretty")


def test_format_fix_result():
    res_clean = FixResult(
        file_path=".env",
        modified=False,
    )
    assert "No issues to fix" in format_fix_result(res_clean, output_format="pretty")
    assert json.loads(format_fix_result(res_clean, output_format="json"))["modified"] is False

    res_fixed = FixResult(
        file_path=".env",
        modified=True,
        fixed_issues_count=2,
        descriptions=["Fixed whitespace around '='", "Auto-quoted unquoted value"],
        backup_path=".env.bak",
        diff="-FOO = bar\n+FOO=bar\n",
    )
    fixed_pretty = format_fix_result(res_fixed, output_format="pretty")
    assert "Fixed 2 issue(s)" in fixed_pretty
    assert "Fixed whitespace around '='" in fixed_pretty
    assert "Backup created: .env.bak" in fixed_pretty
    assert "-FOO = bar" in fixed_pretty
