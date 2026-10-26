"""Synchronization engine to align local environment files with reference templates."""
from __future__ import annotations

import difflib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

from dotenv_doctor.models import EnvEntry, EnvFile, LineType
from dotenv_doctor.parser import EnvParser


@dataclass
class SyncResult:
    """Result of a sync operation."""
    target_path: str
    reference_path: str
    added_keys: List[str] = field(default_factory=list)
    pruned_keys: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    diff: str = ""
    modified: bool = False
    created_new: bool = False

    def to_dict(self) -> dict:
        """Convert sync result to dictionary."""
        return {
            "target_path": self.target_path,
            "reference_path": self.reference_path,
            "added_keys": self.added_keys,
            "pruned_keys": self.pruned_keys,
            "backup_path": self.backup_path,
            "modified": self.modified,
            "created_new": self.created_new,
            "diff": self.diff,
        }


class EnvSyncer:
    """Synchronizes target .env with reference .env.example."""

    def __init__(
        self,
        fill_mode: str = "example",  # "example" or "empty"
        prune: bool = False,
        preserve_comments: bool = True,
        backup: bool = True,
        dry_run: bool = False,
    ) -> None:
        self.fill_mode = fill_mode
        self.prune = prune
        self.preserve_comments = preserve_comments
        self.backup = backup
        self.dry_run = dry_run

    def sync(
        self,
        target_path: Union[str, Path],
        reference_path: Union[str, Path],
    ) -> SyncResult:
        """Synchronize target file with reference template."""
        target_str = str(target_path)
        ref_str = str(reference_path)

        if not os.path.exists(ref_str):
            raise FileNotFoundError(f"Reference environment file not found: {ref_str}")

        with open(ref_str, "r", encoding="utf-8", errors="replace") as f:
            ref_content = f.read()
        ref_env = EnvParser.parse(ref_content, file_path=ref_str)

        result = SyncResult(target_path=target_str, reference_path=ref_str)

        if not os.path.exists(target_str):
            # Target does not exist: create from scratch
            result.created_new = True
            new_content = self._build_from_scratch(ref_env)
            result.added_keys = list(ref_env.keys)
            result.diff = "\n".join(
                difflib.unified_diff(
                    [],
                    new_content.splitlines(),
                    fromfile="<empty>",
                    tofile=target_str,
                    lineterm="",
                )
            )
            result.modified = True

            if not self.dry_run:
                # Ensure directory exists
                parent = os.path.dirname(target_str)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(target_str, "w", encoding="utf-8") as f:
                    f.write(new_content)
            return result

        # Target exists: read and update
        with open(target_str, "r", encoding="utf-8", errors="replace") as f:
            old_content = f.read()

        target_env = EnvParser.parse(old_content, file_path=target_str)
        target_keys = set(target_env.keys)
        ref_keys = set(ref_env.keys)

        # Keys to add
        missing_keys = [k for k in ref_env.keys if k not in target_keys]
        result.added_keys = missing_keys

        # Keys to prune
        if self.prune:
            pruned = [k for k in target_env.keys if k not in ref_keys]
            result.pruned_keys = pruned

        if not missing_keys and not result.pruned_keys:
            # Nothing to change
            result.modified = False
            return result

        new_content = self._merge_envs(target_env, ref_env, missing_keys, result.pruned_keys)
        result.diff = "\n".join(
            difflib.unified_diff(
                old_content.splitlines(),
                new_content.splitlines(),
                fromfile=target_str,
                tofile=target_str,
                lineterm="",
            )
        )
        result.modified = True

        if not self.dry_run:
            if self.backup:
                backup_file = f"{target_str}.bak"
                shutil.copy2(target_str, backup_file)
                result.backup_path = backup_file

            with open(target_str, "w", encoding="utf-8") as f:
                f.write(new_content)

        return result

    def _build_from_scratch(self, ref_env: EnvFile) -> str:
        """Build initial target file from reference template."""
        if self.fill_mode == "example":
            return ref_env.to_string()

        # If fill_mode == "empty", preserve comments and structure but clear values
        new_entries: List[EnvEntry] = []
        for entry in ref_env.entries:
            if entry.is_variable:
                new_entries.append(
                    EnvEntry(
                        line_number=entry.line_number,
                        raw_line=f"{entry.key}=",
                        line_type=LineType.ENTRY,
                        key=entry.key,
                        value="",
                        raw_value="",
                        is_exported=entry.is_exported,
                        inline_comment=entry.inline_comment,
                    )
                )
            else:
                new_entries.append(entry)

        empty_env = EnvFile(entries=new_entries)
        return empty_env.to_string()

    def _merge_envs(
        self,
        target_env: EnvFile,
        ref_env: EnvFile,
        missing_keys: List[str],
        prune_keys: List[str],
    ) -> str:
        """Merge missing keys into target, optionally pruning unwanted keys."""
        prune_set = set(prune_keys)
        output_lines: List[str] = []

        # Iterate target entries, dropping pruned keys
        for entry in target_env.entries:
            if entry.is_variable and entry.key in prune_set:
                continue
            output_lines.append(entry.raw_line)

        # Append missing keys with section header if any
        if missing_keys:
            if output_lines and output_lines[-1].strip() != "":
                output_lines.append("")
            output_lines.append("# --- Added by dotenv-doctor sync ---")

            for k in missing_keys:
                ref_entries = ref_env.get_entries(k)
                if not ref_entries:
                    continue
                ref_entry = ref_entries[-1]

                # Include comments from reference if requested
                if self.preserve_comments and ref_entry.associated_comments:
                    for c in ref_entry.associated_comments:
                        output_lines.append(c)

                prefix = "export " if ref_entry.is_exported else ""
                val = ref_entry.value if self.fill_mode == "example" else ""
                quote = ref_entry.quote_char or ""
                comment = f" #{ref_entry.inline_comment}" if ref_entry.inline_comment else ""

                if val is not None and quote:
                    val_formatted = f"{quote}{val}{quote}"
                else:
                    val_formatted = val or ""

                output_lines.append(f"{prefix}{k}={val_formatted}{comment}")

        return "\n".join(output_lines) + ("\n" if output_lines else "")


def sync(
    target_path: Union[str, Path],
    reference_path: Union[str, Path] = ".env.example",
    fill_mode: str = "example",
    prune: bool = False,
    preserve_comments: bool = True,
    backup: bool = True,
    dry_run: bool = False,
) -> SyncResult:
    """Convenience function to synchronize environment files."""
    syncer = EnvSyncer(
        fill_mode=fill_mode,
        prune=prune,
        preserve_comments=preserve_comments,
        backup=backup,
        dry_run=dry_run,
    )
    return syncer.sync(target_path, reference_path)
