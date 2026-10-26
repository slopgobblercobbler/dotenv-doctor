"""Tests for the command line interface."""
import json
from pathlib import Path
import pytest
from dotenv_doctor.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "dotenv-doctor" in captured.out


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "dotenv-doctor" in captured.out
    assert "check" in captured.out
    assert "lint" in captured.out
    assert "sync" in captured.out
    assert "fix" in captured.out


def test_cli_no_args(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "dotenv-doctor" in captured.out
    assert "Available subcommands" in captured.out or "positional arguments" in captured.out or "check" in captured.out


def test_cli_check_clean(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"
    ref.write_text("PORT=3000\n", encoding="utf-8")
    target.write_text("PORT=8080\n", encoding="utf-8")

    ret = main(["check", str(target), str(ref), "--no-color"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "is in sync" in captured.out


def test_cli_check_missing_returns_1(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"
    ref.write_text("PORT=3000\nSECRET_KEY=123\n", encoding="utf-8")
    target.write_text("PORT=8080\n", encoding="utf-8")

    ret = main(["check", str(target), str(ref), "--no-color"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Missing variables" in captured.out
    assert "SECRET_KEY" in captured.out


def test_cli_check_strict_on_extra_keys(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"
    ref.write_text("PORT=3000\n", encoding="utf-8")
    target.write_text("PORT=3000\nEXTRA_VAR=123\n", encoding="utf-8")

    # Without strict: exit 0 because only extra undocumented key exists
    ret_normal = main(["check", str(target), str(ref), "--no-color"])
    assert ret_normal == 0

    # With strict: exit 1 because not is_clean
    ret_strict = main(["check", str(target), str(ref), "--strict", "--no-color"])
    assert ret_strict == 1


def test_cli_check_json_format(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"
    ref.write_text("VAR1=1\nVAR2=2\n", encoding="utf-8")
    target.write_text("VAR1=1\n", encoding="utf-8")

    ret = main(["check", str(target), str(ref), "--format", "json"])
    assert ret == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["missing_keys"] == ["VAR2"]
    assert data["has_errors"] is True


def test_cli_lint_clean(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    target.write_text('APP_NAME="Clean App"\nPORT=3000\n', encoding="utf-8")

    ret = main(["lint", str(target), "--no-color"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "No issues found" in captured.out


def test_cli_lint_error(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    target.write_text('INVALID LINE WITHOUT EQUALS\n', encoding="utf-8")

    ret = main(["lint", str(target), "--no-color"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.out


def test_cli_lint_strict_and_ignore(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    # lowercase-key is INFO, weak-default-secret is WARNING
    target.write_text('API_KEY=123456\n', encoding="utf-8")

    # Non-strict with warning exits 0
    ret_non_strict = main(["lint", str(target), "--no-color"])
    assert ret_non_strict == 0

    # Strict with warning exits 1
    ret_strict = main(["lint", str(target), "--strict", "--no-color"])
    assert ret_strict == 1

    # Ignoring the rule exits 0 even in strict mode
    ret_ignored = main(["lint", str(target), "--strict", "--ignore-rule", "weak-default-secret", "--no-color"])
    assert ret_ignored == 0


def test_cli_sync(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"
    ref.write_text("PORT=3000\nAPI_KEY=test\n", encoding="utf-8")
    target.write_text("PORT=8080\n", encoding="utf-8")

    ret = main(["sync", str(target), str(ref), "--no-color", "--no-backup"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Added (1): API_KEY" in captured.out
    assert "API_KEY=test" in target.read_text(encoding="utf-8")


def test_cli_sync_dry_run(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"
    ref.write_text("PORT=3000\nAPI_KEY=test\n", encoding="utf-8")
    target.write_text("PORT=8080\n", encoding="utf-8")

    ret = main(["sync", str(target), str(ref), "--dry-run", "--no-color"])
    assert ret == 0
    # Target file should not have been modified
    assert "API_KEY" not in target.read_text(encoding="utf-8")


def test_cli_sync_error(tmp_path: Path, capsys):
    ret = main(["sync", str(tmp_path / "nonexistent1"), str(tmp_path / "nonexistent2")])
    assert ret == 1


def test_cli_fix(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    target.write_text("FOO = bar\nMSG=hello world\n", encoding="utf-8")

    ret = main(["fix", str(target), "--no-color", "--no-backup"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Fixed" in captured.out
    fixed = target.read_text(encoding="utf-8")
    assert "FOO=bar" in fixed
    assert 'MSG="hello world"' in fixed


def test_cli_fix_dry_run(tmp_path: Path, capsys):
    target = tmp_path / ".env"
    initial_content = "FOO = bar\n"
    target.write_text(initial_content, encoding="utf-8")

    ret = main(["fix", str(target), "--dry-run", "--no-color"])
    assert ret == 0
    assert target.read_text(encoding="utf-8") == initial_content


def test_cli_fix_error(capsys):
    ret = main(["fix", "/path/that/definitely/does/not/exist/or/invalid/.env"])
    assert ret == 1
