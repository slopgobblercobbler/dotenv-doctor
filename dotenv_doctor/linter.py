"""Linter engine for analyzing environment files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Sequence, Set, Union

from dotenv_doctor.models import EnvFile, Issue, Severity
from dotenv_doctor.parser import EnvParser
from dotenv_doctor.rules import ALL_RULES


class EnvLinter:
    """Linter for checking environment files for syntax errors, conventions, and security risks."""

    def __init__(self, ignore_rules: Optional[Sequence[str]] = None) -> None:
        self.ignore_rules: Set[str] = set(r.strip() for r in (ignore_rules or []))

    def lint_file(self, file_path: Union[str, Path]) -> List[Issue]:
        """Lint an environment file on disk."""
        path_str = str(file_path)
        if not os.path.exists(path_str):
            return [
                Issue(
                    rule_id="file-not-found",
                    message=f"Environment file not found: {path_str}",
                    severity=Severity.ERROR,
                    file_path=path_str,
                )
            ]

        try:
            with open(path_str, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(path_str, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                return [
                    Issue(
                        rule_id="read-error",
                        message=f"Failed to read file {path_str}: {e}",
                        severity=Severity.ERROR,
                        file_path=path_str,
                    )
                ]
        except Exception as e:
            return [
                Issue(
                    rule_id="read-error",
                    message=f"Failed to read file {path_str}: {e}",
                    severity=Severity.ERROR,
                    file_path=path_str,
                )
            ]

        return self.lint_content(content, file_path=path_str)

    def lint_content(self, content: str, file_path: Optional[str] = None) -> List[Issue]:
        """Lint raw string content as an environment file."""
        env_file = EnvParser.parse(content, file_path=file_path)
        return self.lint_env(env_file)

    def lint_env(self, env: EnvFile) -> List[Issue]:
        """Run all active lint rules against a parsed EnvFile."""
        issues: List[Issue] = []
        for rule in ALL_RULES:
            issues.extend(rule(env, self.ignore_rules))

        # Sort issues by line number (placing None line numbers at the end)
        issues.sort(key=lambda i: (i.line_number if i.line_number is not None else 999999, i.rule_id))
        return issues


def lint(
    file_path: Union[str, Path],
    ignore_rules: Optional[Sequence[str]] = None,
) -> List[Issue]:
    """Convenience function to lint a single file."""
    linter = EnvLinter(ignore_rules=ignore_rules)
    return linter.lint_file(file_path)
