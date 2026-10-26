"""Tests for synchronization engine."""
import os
from pathlib import Path
from dotenv_doctor.parser import EnvParser
from dotenv_doctor.syncer import EnvSyncer, sync


def test_sync_create_from_scratch(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    ref_content = "# App Settings\nPORT=3000\nDATABASE_URL=sqlite:///db.sqlite\n"
    ref.write_text(ref_content, encoding="utf-8")

    result = sync(target, ref)
    assert result.created_new is True
    assert result.modified is True
    assert target.exists()

    env = EnvParser.parse(target.read_text(encoding="utf-8"))
    assert env.get("PORT") == "3000"
    assert env.get("DATABASE_URL") == "sqlite:///db.sqlite"


def test_sync_add_missing_variables_preserving_comments(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    target.write_text("PORT=8000\n", encoding="utf-8")
    ref.write_text(
        "PORT=3000\n\n# Database connection string\nDATABASE_URL=postgres://...\n",
        encoding="utf-8",
    )

    result = sync(target, ref, fill_mode="example", backup=True)
    assert result.modified is True
    assert "DATABASE_URL" in result.added_keys
    assert result.backup_path is not None
    assert os.path.exists(result.backup_path)

    new_content = target.read_text(encoding="utf-8")
    env = EnvParser.parse(new_content)
    assert env.get("PORT") == "8000"  # Target value kept
    assert env.get("DATABASE_URL") == "postgres://..."
    assert "Database connection string" in new_content


def test_sync_fill_mode_empty(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    target.write_text("PORT=8000\n", encoding="utf-8")
    ref.write_text("PORT=3000\nNEW_KEY=some_val\n", encoding="utf-8")

    result = sync(target, ref, fill_mode="empty", backup=False)
    assert result.modified is True
    env = EnvParser.parse(target.read_text(encoding="utf-8"))
    assert env.get("NEW_KEY") == ""


def test_sync_prune(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    target.write_text("PORT=8000\nDEPRECATED_VAR=123\n", encoding="utf-8")
    ref.write_text("PORT=3000\n", encoding="utf-8")

    result = sync(target, ref, prune=True, backup=False)
    assert "DEPRECATED_VAR" in result.pruned_keys
    env = EnvParser.parse(target.read_text(encoding="utf-8"))
    assert not env.has_key("DEPRECATED_VAR")
    assert env.has_key("PORT")


def test_sync_dry_run(tmp_path: Path):
    target = tmp_path / ".env"
    ref = tmp_path / ".env.example"

    target.write_text("PORT=8000\n", encoding="utf-8")
    ref.write_text("PORT=3000\nNEW_VAR=abc\n", encoding="utf-8")

    result = sync(target, ref, dry_run=True)
    assert result.modified is True
    assert "+NEW_VAR=abc" in result.diff

    # Verify file was NOT modified
    assert target.read_text(encoding="utf-8") == "PORT=8000\n"
