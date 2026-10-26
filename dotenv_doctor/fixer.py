"""Automated issue repair engine for environment files."""
from __future__ import annotations

import difflib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Union

from dotenv_doctor.models import EnvEntry, EnvFile, LineType
from dotenv_doctor.parser import EnvParser


@dataclass
class FixResult:
    """Result of an automated fix operation."""
    file_path: str
    fixed_issues_count: int = 0
    descriptions: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    diff: str = ""
    modified: bool = False

    def to_dict(self) -> dict:
        """Convert fix result to dictionary."""
        return {
            "file_path": self.file_path,
            "fixed_issues_count": self.fixed_issues_count,
            "descriptions": self.descriptions,
            "backup_path": self.backup_path,
            "modified": self.modified,
            "diff": self.diff,
        }


class EnvFixer:
    """Repairs syntax and formatting issues in .env files safely."""

    def __init__(
        self,
        fix_whitespace: bool = True,
        fix_quoting: bool = True,
        fix_duplicates: bool = True,
        backup: bool = True,
        dry_run: bool = False,
    ) -> None:
        self.fix_whitespace = fix_whitespace
        self.fix_quoting = fix_quoting
        self.fix_duplicates = fix_duplicates
        self.backup = backup
        self.dry_run = dry_run

    def fix_file(self, file_path: Union[str, Path]) -> FixResult:
        """Fix formatting and syntax issues in a file."""
        path_str = str(file_path)
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"File not found: {path_str}")

        with open(path_str, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

        return self.fix_content(original_content, file_path=path_str)

    def fix_content(self, content: str, file_path: Optional[str] = None) -> FixResult:
        """Fix formatting and syntax issues in string content."""
        path_str = file_path or "<memory>"
        result = FixResult(file_path=path_str)
        env = EnvParser.parse(content, file_path=path_str)

        # Identify duplicate entries if deduplication is enabled
        duplicate_entries_to_remove: Set[int] = set()
        if self.fix_duplicates:
            for key in env.keys:
                entries = env.get_entries(key)
                if len(entries) > 1:
                    # Keep the last entry, remove earlier ones
                    for e in entries[:-1]:
                        duplicate_entries_to_remove.add(e.line_number)
                        result.descriptions.append(
                            f"Removed earlier duplicate definition of '{key}' on line {e.line_number}"
                        )
                        result.fixed_issues_count += 1

        new_lines: List[str] = []

        for entry in env.entries:
            if entry.line_number in duplicate_entries_to_remove:
                continue

            if entry.line_type == LineType.EMPTY:
                new_lines.append("")
                continue

            if entry.line_type == LineType.COMMENT:
                cleaned = entry.raw_line.rstrip() if self.fix_whitespace else entry.raw_line
                new_lines.append(cleaned)
                continue

            if entry.line_type == LineType.ENTRY and entry.key is not None:
                # Check whitespace around equals
                changed_line = False
                val = entry.value if entry.value is not None else ""
                quote = entry.quote_char

                # Auto-quote unquoted strings with whitespace
                if self.fix_quoting and quote is None and (" " in val or "\t" in val):
                    quote = '"'
                    # Escape internal double quotes if any
                    val_escaped = val.replace('"', r'\"')
                    val_formatted = f'"{val_escaped}"'
                    result.descriptions.append(
                        f"Quoted value with whitespace for '{entry.key}' on line {entry.line_number}"
                    )
                    result.fixed_issues_count += 1
                    changed_line = True
                elif quote:
                    val_formatted = f"{quote}{val}{quote}"
                else:
                    val_formatted = val

                if entry.has_whitespace_around_equals and self.fix_whitespace:
                    result.descriptions.append(
                        f"Stripped whitespace around '=' for '{entry.key}' on line {entry.line_number}"
                    )
                    result.fixed_issues_count += 1
                    changed_line = True

                prefix = "export " if entry.is_exported else ""
                comment = f" #{entry.inline_comment}" if entry.inline_comment is not None else ""
                line_str = f"{prefix}{entry.key}={val_formatted}{comment}"

                if self.fix_whitespace:
                    stripped = line_str.rstrip()
                    if stripped != line_str:
                        result.descriptions.append(
                            f"Removed trailing whitespace on line {entry.line_number}"
                        )
                        result.fixed_issues_count += 1
                    line_str = stripped

                new_lines.append(line_str)
            else:
                cleaned = entry.raw_line.rstrip() if self.fix_whitespace else entry.raw_line
                new_lines.append(cleaned)

        fixed_content = "\n".join(new_lines) + ("\n" if new_lines else "")

        if fixed_content != content:
            result.modified = True
            result.diff = "\n".join(
                difflib.unified_diff(
                    content.splitlines(),
                    fixed_content.splitlines(),
                    fromfile=path_str,
                    tofile=path_str,
                    lineterm="",
                )
            )

            if file_path and os.path.exists(file_path) and not self.dry_run:
                if self.backup:
                    backup_path = f"{path_str}.bak"
                    shutil.copy2(path_str, backup_path)
                    result.backup_path = backup_path

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

        return result


def fix(
    file_path: Union[str, Path],
    fix_whitespace: bool = True,
    fix_quoting: bool = True,
    fix_duplicates: bool = True,
    backup: bool = True,
    dry_run: bool = False,
) -> FixResult:
    """Convenience function to fix issues in a file."""
    fixer = EnvFixer(
        fix_whitespace=fix_whitespace,
        fix_quoting=fix_quoting,
        fix_duplicates=fix_duplicates,
        backup=backup,
        dry_run=dry_run,
    )
    return fixer.fix_file(file_path)
