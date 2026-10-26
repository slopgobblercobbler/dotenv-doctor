"""Tests for the public Python API of dotenv-doctor."""
import dotenv_doctor


def test_api_exports():
    assert hasattr(dotenv_doctor, "__version__")
    assert hasattr(dotenv_doctor, "parse")
    assert hasattr(dotenv_doctor, "check")
    assert hasattr(dotenv_doctor, "lint")
    assert hasattr(dotenv_doctor, "sync")
    assert hasattr(dotenv_doctor, "fix")


def test_api_parse():
    env = dotenv_doctor.parse("A=1\nB=2\n")
    assert env.get("A") == "1"
    assert env.get("B") == "2"


def test_api_lint():
    issues = dotenv_doctor.lint("tests/nonexistent.env")
    assert any(i.rule_id == "file-not-found" for i in issues)
