"""Tests for dotenv linter and rules."""
from dotenv_doctor.linter import EnvLinter
from dotenv_doctor.models import Severity


def test_linter_syntax_error():
    content = "FOO=123\nINVALID LINE WITHOUT EQUALS\nBAR=456\n"
    linter = EnvLinter()
    issues = linter.lint_content(content)
    assert any(i.rule_id == "syntax-error" for i in issues)
    error = next(i for i in issues if i.rule_id == "syntax-error")
    assert error.severity == Severity.ERROR
    assert error.line_number == 2


def test_linter_unclosed_quote():
    content = 'KEY="this is unclosed\nANOTHER=1\n'
    linter = EnvLinter()
    issues = linter.lint_content(content)
    assert any(i.rule_id == "unclosed-quote" for i in issues)


def test_linter_invalid_key_name():
    content = "123_INVALID=val\nVALID_KEY=val\nINVALID-KEY=val\n"
    linter = EnvLinter()
    issues = linter.lint_content(content)
    invalid_keys = [i.key for i in issues if i.rule_id == "invalid-key-name"]
    assert "123_INVALID" in invalid_keys
    assert "INVALID-KEY" in invalid_keys
    assert "VALID_KEY" not in invalid_keys


def test_linter_lowercase_key():
    content = "my_lowercase_key=val\nUPPER_KEY=val\n"
    linter = EnvLinter()
    issues = linter.lint_content(content)
    assert any(i.rule_id == "lowercase-key" for i in issues)


def test_linter_whitespace_around_equals():
    content = "KEY1 = val1\nKEY2= val2\nKEY3 =val3\nKEY4=val4\n"
    linter = EnvLinter()
    issues = linter.lint_content(content)
    flagged = [i.key for i in issues if i.rule_id == "whitespace-around-equals"]
    assert "KEY1" in flagged
    assert "KEY2" in flagged
    assert "KEY3" in flagged
    assert "KEY4" not in flagged


def test_linter_duplicate_keys():
    content = "DATABASE_URL=sqlite:///first.db\nPORT=3000\nDATABASE_URL=sqlite:///second.db\n"
    linter = EnvLinter()
    issues = linter.lint_content(content)
    assert any(i.rule_id == "duplicate-key" for i in issues)


def test_linter_unescaped_value():
    content = "MESSAGE=hello world this is unquoted\nQUOTED=\"hello world\"\n"
    linter = EnvLinter()
    issues = linter.lint_content(content)
    assert any(i.rule_id == "unescaped-value" and i.key == "MESSAGE" for i in issues)
    assert not any(i.rule_id == "unescaped-value" and i.key == "QUOTED" for i in issues)


def test_linter_weak_default_secrets():
    content = """
    APP_SECRET=changeme
    DATABASE_PASSWORD=password
    API_TOKEN=123456
    SAFE_KEY=x9a$kL8#91kLmz90184!@#
    """
    linter = EnvLinter()
    issues = linter.lint_content(content)
    weak_keys = [i.key for i in issues if i.rule_id == "weak-default-secret"]
    assert "APP_SECRET" in weak_keys
    assert "DATABASE_PASSWORD" in weak_keys
    assert "API_TOKEN" in weak_keys
    assert "SAFE_KEY" not in weak_keys


def test_linter_insecure_url():
    content = """
    API_ENDPOINT=http://api.production.com/v1
    LOCAL_URL=http://localhost:8000
    SAFE_ENDPOINT=https://api.production.com/v1
    """
    linter = EnvLinter()
    issues = linter.lint_content(content)
    insecure = [i.key for i in issues if i.rule_id == "insecure-url"]
    assert "API_ENDPOINT" in insecure
    assert "LOCAL_URL" not in insecure
    assert "SAFE_ENDPOINT" not in insecure


def test_linter_ignore_rules():
    content = "my_var=hello world\n"
    linter = EnvLinter(ignore_rules=["lowercase-key", "unescaped-value"])
    issues = linter.lint_content(content)
    assert len(issues) == 0
