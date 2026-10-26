"""Parser for environment (.env) files preserving structure and comments."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple
from dotenv_doctor.models import EnvEntry, EnvFile, LineType


class EnvParser:
    """Robust parser for dotenv files supporting multiline values, comments, and quotes."""

    _EXPORT_PREFIX = re.compile(r"^\s*export\s+", re.IGNORECASE)

    @classmethod
    def parse(cls, content: str, file_path: Optional[str] = None) -> EnvFile:
        """Parse dotenv string content into an EnvFile structure."""
        entries: List[EnvEntry] = []
        raw_lines = content.splitlines()
        
        pending_comments: List[str] = []
        i = 0
        total_lines = len(raw_lines)

        while i < total_lines:
            raw_line = raw_lines[i]
            line_no = i + 1
            stripped = raw_line.strip()

            # Empty lines
            if not stripped:
                entries.append(
                    EnvEntry(
                        line_number=line_no,
                        raw_line=raw_line,
                        line_type=LineType.EMPTY,
                        associated_comments=list(pending_comments),
                    )
                )
                pending_comments.clear()
                i += 1
                continue

            # Full line comment
            if stripped.startswith("#"):
                entries.append(
                    EnvEntry(
                        line_number=line_no,
                        raw_line=raw_line,
                        line_type=LineType.COMMENT,
                    )
                )
                pending_comments.append(raw_line)
                i += 1
                continue

            # Check export prefix
            is_exported = False
            line_to_parse = raw_line
            export_match = cls._EXPORT_PREFIX.match(line_to_parse)
            if export_match:
                is_exported = True
                line_to_parse = line_to_parse[export_match.end():]

            # Look for '=' separator
            if "=" not in line_to_parse:
                entries.append(
                    EnvEntry(
                        line_number=line_no,
                        raw_line=raw_line,
                        line_type=LineType.SYNTAX_ERROR,
                        associated_comments=list(pending_comments),
                    )
                )
                pending_comments.clear()
                i += 1
                continue

            # Split key and value parts on first '='
            key_part, value_part = line_to_parse.split("=", 1)
            raw_key = key_part
            key = key_part.strip()

            # Check if there was whitespace around '='
            has_whitespace_around = (key_part != key) or (value_part and (value_part[0].isspace() or (len(value_part) > 0 and value_part.startswith(" "))))

            val_trimmed_left = value_part.lstrip()

            # Check for quotes
            quote_char = None
            if val_trimmed_left and val_trimmed_left[0] in ('"', "'", "`"):
                quote_char = val_trimmed_left[0]

            if quote_char:
                # Quoted value: could be multiline or single line
                parsed_value, raw_val, inline_comm, lines_consumed, unclosed = cls._parse_quoted(
                    quote_char, val_trimmed_left, raw_lines, i
                )
                
                full_raw = "\n".join(raw_lines[i : i + lines_consumed])
                if unclosed:
                    entries.append(
                        EnvEntry(
                            line_number=line_no,
                            raw_line=full_raw,
                            line_type=LineType.SYNTAX_ERROR,
                            key=key,
                            raw_value=raw_val,
                            quote_char=quote_char,
                            is_exported=is_exported,
                            associated_comments=list(pending_comments),
                        )
                    )
                else:
                    entries.append(
                        EnvEntry(
                            line_number=line_no,
                            raw_line=full_raw,
                            line_type=LineType.ENTRY,
                            key=key,
                            value=parsed_value,
                            raw_value=raw_val,
                            quote_char=quote_char,
                            is_exported=is_exported,
                            has_whitespace_around_equals=has_whitespace_around,
                            inline_comment=inline_comm,
                            associated_comments=list(pending_comments),
                        )
                    )
                pending_comments.clear()
                i += lines_consumed
            else:
                # Unquoted value
                parsed_value, inline_comm = cls._parse_unquoted(value_part)
                entries.append(
                    EnvEntry(
                        line_number=line_no,
                        raw_line=raw_line,
                        line_type=LineType.ENTRY,
                        key=key,
                        value=parsed_value,
                        raw_value=value_part,
                        quote_char=None,
                        is_exported=is_exported,
                        has_whitespace_around_equals=has_whitespace_around,
                        inline_comment=inline_comm,
                        associated_comments=list(pending_comments),
                    )
                )
                pending_comments.clear()
                i += 1

        env_file = EnvFile(file_path=file_path, entries=entries, raw_content=content)
        return env_file

    @classmethod
    def _parse_quoted(
        cls, quote_char: str, first_line_val: str, all_lines: List[str], current_index: int
    ) -> Tuple[str, str, Optional[str], int, bool]:
        """
        Parse quoted value which may span multiple lines.
        Returns (parsed_value, raw_value, inline_comment, lines_consumed, is_unclosed).
        """
        # first_line_val starts with quote_char
        # Search for closing quote
        content_after_start = first_line_val[1:]
        
        # Look for closing quote on first line
        end_idx, inline_comm = cls._find_closing_quote(quote_char, content_after_start)
        if end_idx is not None:
            # Single line quoted
            raw_inside = content_after_start[:end_idx]
            val = cls._unescape(raw_inside, quote_char)
            return val, raw_inside, inline_comm, 1, False

        # If not found on first line, multiline
        accumulated_chunks = [content_after_start]
        lines_consumed = 1
        unclosed = True
        final_inline_comm = None

        while current_index + lines_consumed < len(all_lines):
            next_line = all_lines[current_index + lines_consumed]
            lines_consumed += 1
            end_idx, inline_comm = cls._find_closing_quote(quote_char, next_line)
            if end_idx is not None:
                accumulated_chunks.append(next_line[:end_idx])
                final_inline_comm = inline_comm
                unclosed = False
                break
            else:
                accumulated_chunks.append(next_line)

        raw_inside = "\n".join(accumulated_chunks)
        val = cls._unescape(raw_inside, quote_char) if not unclosed else raw_inside
        return val, raw_inside, final_inline_comm, lines_consumed, unclosed

    @classmethod
    def _find_closing_quote(cls, quote_char: str, s: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Find closing quote in string s (taking backslash escaping into account for double quotes).
        Returns (index_of_closing_quote, inline_comment).
        """
        i = 0
        escaped = False
        while i < len(s):
            char = s[i]
            if quote_char == '"' and char == "\\" and not escaped:
                escaped = True
                i += 1
                continue
            if char == quote_char and not escaped:
                # Found closing quote!
                remainder = s[i + 1 :]
                inline_comm = None
                remainder_stripped = remainder.strip()
                if remainder_stripped.startswith("#"):
                    inline_comm = remainder_stripped[1:].strip()
                return i, inline_comm
            escaped = False
            i += 1
        return None, None

    @classmethod
    def _parse_unquoted(cls, val_str: str) -> Tuple[str, Optional[str]]:
        """
        Parse unquoted value string and extract any inline comment.
        Inline comment requires ' #' (whitespace followed by #).
        """
        inline_comment = None
        # Check for inline comment ' #'
        comment_idx = -1
        i = 0
        while i < len(val_str) - 1:
            if val_str[i].isspace() and val_str[i + 1] == "#":
                comment_idx = i
                break
            i += 1

        if comment_idx != -1:
            raw_val = val_str[:comment_idx].strip()
            inline_comment = val_str[comment_idx + 2 :].strip()
            return raw_val, inline_comment

        return val_str.strip(), None

    @classmethod
    def _unescape(cls, s: str, quote_char: str) -> str:
        """Unescape string for double quotes."""
        if quote_char != '"':
            return s
        # For double quotes, decode standard escapes
        return (
            s.replace(r"\n", "\n")
            .replace(r"\r", "\r")
            .replace(r"\t", "\t")
            .replace(r'\"', '"')
            .replace(r"\\", "\\")
        )
