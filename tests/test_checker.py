"""Tests for the dotenv environment comparison checker."""
import os
from pathlib import Path
from dotenv_doctor.checker import EnvChecker, check


def test_checker_all_in_sync(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    ref.write_text("DATABASE_URL=sqlite:///db.sqlite\nPORT=3000\n", encoding="utf-8")
    target.write_text("DATABASE_URL=postgres://user:pass@host/db\nPORT=8080\n", encoding="utf-8")

    checker = EnvChecker()
    res = checker.check(target, ref)
    assert res.is_clean
    assert not res.has_errors
    assert res.missing_keys == []
    assert res.extra_keys == []


def test_checker_missing_and_extra_keys(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    ref.write_text("PORT=3000\nDATABASE_URL=postgres://...\nJWT_SECRET=secret\n", encoding="utf-8")
    target.write_text("PORT=3000\nEXTRA_VAR=123\n", encoding="utf-8")

    checker = EnvChecker()
    res = checker.check(target, ref)
    assert not res.is_clean
    assert res.has_errors
    assert "DATABASE_URL" in res.missing_keys
    assert "JWT_SECRET" in res.missing_keys
    assert "EXTRA_VAR" in res.extra_keys


def test_checker_ignore_extra(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    ref.write_text("PORT=3000\n", encoding="utf-8")
    target.write_text("PORT=3000\nEXTRA_VAR=123\n", encoding="utf-8")

    checker = EnvChecker(ignore_extra=True)
    res = checker.check(target, ref)
    assert res.is_clean
    assert res.extra_keys == []


def test_checker_empty_and_unmodified_placeholder(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    ref.write_text("EMPTY_VAL=\nSECRET_KEY=replace_with_your_key\n", encoding="utf-8")
    target.write_text("EMPTY_VAL=\nSECRET_KEY=replace_with_your_key\n", encoding="utf-8")

    checker = EnvChecker()
    res = checker.check(target, ref)
    assert "EMPTY_VAL" in res.empty_keys
    assert "SECRET_KEY" in res.unmodified_defaults


def test_checker_target_missing(tmp_path: Path):
    target = tmp_path / ".env.nonexistent"
    ref = tmp_path / ".env.example"
    ref.write_text("FOO=1\nBAR=2\n", encoding="utf-8")

    res = check(target, ref)
    assert res.has_errors
    assert "FOO" in res.missing_keys
    assert "BAR" in res.missing_keys


def test_checker_reference_missing(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.nonexistent"
    target.write_text("FOO=1\n", encoding="utf-8")

    res = check(target, ref)
    assert res.has_errors
    assert any(i.rule_id == "missing-reference" for i in res.issues)
