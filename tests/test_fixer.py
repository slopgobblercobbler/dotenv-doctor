"""Tests for automated issue repair engine."""
from pathlib import Path
from dotenv_doctor.fixer import EnvFixer, fix
from dotenv_doctor.parser import EnvParser


def test_fix_whitespace_around_equals(tmp_path: Path):
    target = tmp_path / ".env"
    target.write_text("FOO = bar\nBAZ= qux\n", encoding="utf-8")

    result = fix(target, backup=False)
    assert result.modified is True
    assert result.fixed_issues_count >= 2

    fixed_text = target.read_text(encoding="utf-8")
    assert "FOO=bar" in fixed_text
    assert "BAZ=qux" in fixed_text


def test_fix_unquoted_whitespace_values(tmp_path: Path):
    target = tmp_path / ".env"
    target.write_text("MESSAGE=hello world from test\n", encoding="utf-8")

    result = fix(target, backup=False)
    assert result.modified is True
    fixed_text = target.read_text(encoding="utf-8")
    assert 'MESSAGE="hello world from test"' in fixed_text


def test_fix_duplicate_keys(tmp_path: Path):
    target = tmp_path / ".env"
    content = "PORT=3000\nDEBUG=false\nPORT=8080\n"
    target.write_text(content, encoding="utf-8")

    result = fix(target, backup=False)
    assert result.modified is True
    fixed_text = target.read_text(encoding="utf-8")
    env = EnvParser.parse(fixed_text)
    assert len(env.get_entries("PORT")) == 1
    assert env.get("PORT") == "8080"


def test_fix_dry_run(tmp_path: Path):
    target = tmp_path / ".env"
    original = "KEY = value\n"
    target.write_text(original, encoding="utf-8")

    result = fix(target, dry_run=True)
    assert result.modified is True
    assert target.read_text(encoding="utf-8") == original
