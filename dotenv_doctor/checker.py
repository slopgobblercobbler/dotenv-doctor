"""Checker for comparing target environment (.env) against reference (.env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from dotenv_doctor.linter import EnvLinter
from dotenv_doctor.models import EnvFile, Issue, Severity
from dotenv_doctor.parser import EnvParser


@dataclass
class CheckResult:
    """Summary of environment comparison between target and reference."""
    target_path: str
    reference_path: str
    missing_keys: List[str] = field(default_factory=list)
    extra_keys: List[str] = field(default_factory=list)
    empty_keys: List[str] = field(default_factory=list)
    unmodified_defaults: List[str] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if any critical errors exist (e.g. missing required keys or syntax errors)."""
        return bool(self.missing_keys) or any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def is_clean(self) -> bool:
        """Check if environment matches reference with zero discrepancies."""
        return not self.missing_keys and not self.extra_keys and not self.empty_keys and not self.unmodified_defaults and not self.issues

    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON output."""
        return {
            "target_path": self.target_path,
            "reference_path": self.reference_path,
            "missing_keys": self.missing_keys,
            "extra_keys": self.extra_keys,
            "empty_keys": self.empty_keys,
            "unmodified_defaults": self.unmodified_defaults,
            "issues": [i.to_dict() for i in self.issues],
            "is_clean": self.is_clean,
            "has_errors": self.has_errors,
        }


class EnvChecker:
    """Compares environment files and verifies required keys and values."""

    def __init__(
        self,
        ignore_extra: bool = False,
        check_syntax: bool = True,
        strict: bool = False,
    ) -> None:
        self.ignore_extra = ignore_extra
        self.check_syntax = check_syntax
        self.strict = strict

    def check(
        self,
        target_path: Union[str, Path],
        reference_path: Union[str, Path],
    ) -> CheckResult:
        """Compare target env file against reference env file."""
        target_str = str(target_path)
        ref_str = str(reference_path)
        result = CheckResult(target_path=target_str, reference_path=ref_str)

        if not os.path.exists(ref_str):
            result.issues.append(
                Issue(
                    rule_id="missing-reference",
                    message=f"Reference file not found: {ref_str}",
                    severity=Severity.ERROR,
                    file_path=ref_str,
                )
            )
            return result

        if not os.path.exists(target_str):
            result.issues.append(
                Issue(
                    rule_id="missing-target",
                    message=f"Target environment file not found: {target_str}",
                    severity=Severity.ERROR,
                    file_path=target_str,
                    suggestion=f"Run 'dotenv-doctor sync {target_str} {ref_str}' to generate it.",
                )
            )
            # All reference keys are missing
            try:
                with open(ref_str, "r", encoding="utf-8") as f:
                    ref_env = EnvParser.parse(f.read(), file_path=ref_str)
                result.missing_keys = ref_env.keys
            except Exception:
                pass
            return result

        # Load both files
        with open(target_str, "r", encoding="utf-8", errors="replace") as f:
            target_env = EnvParser.parse(f.read(), file_path=target_str)

        with open(ref_str, "r", encoding="utf-8", errors="replace") as f:
            ref_env = EnvParser.parse(f.read(), file_path=ref_str)

        # Lint target syntax if enabled
        if self.check_syntax:
            linter = EnvLinter()
            syntax_issues = [
                i for i in linter.lint_env(target_env) if i.rule_id in ("syntax-error", "unclosed-quote")
            ]
            result.issues.extend(syntax_issues)

        target_keys = set(target_env.keys)
        ref_keys = set(ref_env.keys)

        # 1. Missing keys in target (in reference order)
        for k in ref_env.keys:
            if k not in target_keys:
                result.missing_keys.append(k)
                result.issues.append(
                    Issue(
                        rule_id="missing-key",
                        message=f"Key '{k}' defined in '{ref_str}' is missing from '{target_str}'.",
                        severity=Severity.ERROR,
                        file_path=target_str,
                        key=k,
                        suggestion=f"Add '{k}' to '{target_str}'.",
                    )
                )

        # 2. Extra keys in target
        if not self.ignore_extra:
            for k in target_env.keys:
                if k not in ref_keys:
                    result.extra_keys.append(k)
                    result.issues.append(
                        Issue(
                            rule_id="extra-key",
                            message=f"Key '{k}' in '{target_str}' is not documented in '{ref_str}'.",
                            severity=Severity.WARNING if self.strict else Severity.INFO,
                            file_path=target_str,
                            key=k,
                            suggestion=f"Document '{k}' in '{ref_str}' or prune it.",
                        )
                    )

        # 3. Empty keys in target
        for k in target_env.keys:
            if k in ref_keys:
                val = target_env.get(k)
                if val == "":
                    result.empty_keys.append(k)
                    entry = target_env.get_entries(k)[-1]
                    result.issues.append(
                        Issue(
                            rule_id="empty-key",
                            message=f"Key '{k}' is empty in '{target_str}'.",
                            severity=Severity.WARNING,
                            file_path=target_str,
                            line_number=entry.line_number,
                            key=k,
                            suggestion=f"Provide a value for '{k}'.",
                        )
                    )

        # 4. Unmodified default placeholder values
        for k in target_env.keys:
            if k in ref_keys:
                t_val = target_env.get(k)
                r_val = ref_env.get(k)
                if t_val and r_val and t_val == r_val:
                    # If reference value looks like a placeholder, e.g., sk_..., your_..., changeme, etc.
                    r_val_lower = r_val.lower()
                    if any(
                        ph in r_val_lower
                        for ph in (
                            "your",
                            "replace",
                            "secret",
                            "placeholder",
                            "todo",
                            "changeme",
                            "xxx",
                            "dummy",
                        )
                    ):
                        result.unmodified_defaults.append(k)
                        entry = target_env.get_entries(k)[-1]
                        result.issues.append(
                            Issue(
                                rule_id="unmodified-example-value",
                                message=f"Key '{k}' still uses example placeholder value '{t_val}'.",
                                severity=Severity.WARNING,
                                file_path=target_str,
                                line_number=entry.line_number,
                                key=k,
                                suggestion="Replace example placeholder with actual environment-specific configuration.",
                            )
                        )

        return result


def check(
    target_path: Union[str, Path],
    reference_path: Union[str, Path] = ".env.example",
    ignore_extra: bool = False,
    strict: bool = False,
) -> CheckResult:
    """Convenience function to compare environment files."""
    checker = EnvChecker(ignore_extra=ignore_extra, strict=strict)
    return checker.check(target_path, reference_path)
