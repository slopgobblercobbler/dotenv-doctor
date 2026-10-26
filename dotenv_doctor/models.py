"""Data models and enums for dotenv-doctor."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Severity(str, Enum):
    """Issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LineType(str, Enum):
    """Type of line in an env file."""
    ENTRY = "entry"
    COMMENT = "comment"
    EMPTY = "empty"
    SYNTAX_ERROR = "syntax_error"


@dataclass
class Issue:
    """Represents a diagnostic issue found during check or lint."""
    rule_id: str
    message: str
    severity: Severity = Severity.WARNING
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    key: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert issue to JSON-serializable dictionary."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "key": self.key,
            "suggestion": self.suggestion,
        }


@dataclass
class EnvEntry:
    """Represents a single parsed line or element in an environment file."""
    line_number: int
    raw_line: str
    line_type: LineType = LineType.ENTRY
    key: Optional[str] = None
    value: Optional[str] = None
    raw_value: Optional[str] = None
    quote_char: Optional[str] = None
    is_exported: bool = False
    has_whitespace_around_equals: bool = False
    inline_comment: Optional[str] = None
    associated_comments: List[str] = field(default_factory=list)

    @property
    def is_variable(self) -> bool:
        """Return True if this entry represents a variable declaration."""
        return self.line_type == LineType.ENTRY and self.key is not None


@dataclass
class EnvFile:
    """Represents a parsed environment file preserving AST and comment order."""
    file_path: Optional[str] = None
    entries: List[EnvEntry] = field(default_factory=list)
    raw_content: str = ""

    def __post_init__(self) -> None:
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild index mapping keys to their entry objects."""
        self._index: Dict[str, List[EnvEntry]] = {}
        for entry in self.entries:
            if entry.is_variable and entry.key:
                if entry.key not in self._index:
                    self._index[entry.key] = []
                self._index[entry.key].append(entry)

    @property
    def keys(self) -> List[str]:
        """Return list of distinct variable keys in declaration order."""
        seen = set()
        result = []
        for entry in self.entries:
            if entry.is_variable and entry.key and entry.key not in seen:
                seen.add(entry.key)
                result.append(entry.key)
        return result

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Return the value for key (last entry wins, following dotenv semantics)."""
        entries = self._index.get(key)
        if entries:
            return entries[-1].value
        return default

    def get_entries(self, key: str) -> List[EnvEntry]:
        """Return all entries for key."""
        return self._index.get(key, [])

    def has_key(self, key: str) -> bool:
        """Check if a variable key is present."""
        return key in self._index

    def to_string(self) -> str:
        """Serialize entries back to string preserving original or updated structure."""
        lines = []
        for entry in self.entries:
            if entry.line_type == LineType.EMPTY:
                lines.append("")
            elif entry.line_type == LineType.COMMENT:
                lines.append(entry.raw_line)
            elif entry.line_type == LineType.SYNTAX_ERROR:
                lines.append(entry.raw_line)
            elif entry.line_type == LineType.ENTRY and entry.key is not None:
                prefix = "export " if entry.is_exported else ""
                val = entry.value if entry.value is not None else ""
                if entry.quote_char:
                    val_str = f"{entry.quote_char}{val}{entry.quote_char}"
                else:
                    val_str = val
                comment = f" # {entry.inline_comment}" if entry.inline_comment is not None else ""
                lines.append(f"{prefix}{entry.key}={val_str}{comment}")
            else:
                lines.append(entry.raw_line)
        return "\n".join(lines) + ("\n" if lines else "")
