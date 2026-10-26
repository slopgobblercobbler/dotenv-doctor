"""Tests for the dotenv parser."""
from dotenv_doctor.models import LineType
from dotenv_doctor.parser import EnvParser


def test_parse_simple_entries():
    content = "FOO=bar\nBAZ=qux\n"
    env = EnvParser.parse(content)
    assert env.keys == ["FOO", "BAZ"]
    assert env.get("FOO") == "bar"
    assert env.get("BAZ") == "qux"


def test_parse_comments_and_empty_lines():
    content = """
    # Section header
    APP_ENV=production

    # Port config
    PORT=8080
    """
    env = EnvParser.parse(content)
    assert env.keys == ["APP_ENV", "PORT"]
    assert env.get("APP_ENV") == "production"
    assert env.get("PORT") == "8080"
    
    port_entry = env.get_entries("PORT")[0]
    assert any("Port config" in c for c in port_entry.associated_comments)


def test_parse_export_prefix():
    content = "export API_KEY=secret_123\n"
    env = EnvParser.parse(content)
    assert env.get("API_KEY") == "secret_123"
    entry = env.get_entries("API_KEY")[0]
    assert entry.is_exported is True


def test_parse_quoted_values():
    content = '''
    SINGLE='single quoted value'
    DOUBLE="double quoted value with \\"escapes\\""
    BACKTICK=`backtick value`
    '''
    env = EnvParser.parse(content)
    assert env.get("SINGLE") == "single quoted value"
    assert env.get("DOUBLE") == 'double quoted value with "escapes"'
    assert env.get("BACKTICK") == "backtick value"


def test_parse_multiline_quotes():
    content = '''
    RSA_KEY="-----BEGIN CERTIFICATE-----
    MIIDXTCCAkWgAwIBAgIJAL7
    -----END CERTIFICATE-----"
    NEXT_VAR=1
    '''
    env = EnvParser.parse(content)
    assert env.keys == ["RSA_KEY", "NEXT_VAR"]
    rsa_val = env.get("RSA_KEY")
    assert rsa_val is not None
    assert "-----BEGIN CERTIFICATE-----" in rsa_val
    assert "-----END CERTIFICATE-----" in rsa_val
    assert env.get("NEXT_VAR") == "1"


def test_parse_inline_comments():
    content = """
    HOST=0.0.0.0 # bind to all interfaces
    QUOTED="some value" # quote comment
    HASH_URL=https://example.com#section
    """
    env = EnvParser.parse(content)
    assert env.get("HOST") == "0.0.0.0"
    assert env.get_entries("HOST")[0].inline_comment == "bind to all interfaces"

    assert env.get("QUOTED") == "some value"
    assert env.get_entries("QUOTED")[0].inline_comment == "quote comment"

    # In URL with # without preceding space, # is part of value
    assert env.get("HASH_URL") == "https://example.com#section"


def test_parse_syntax_errors():
    content = """
    VALID_KEY=123
    THIS_LINE_HAS_NO_EQUALS
    ANOTHER_VALID=abc
    UNCLOSED_VAR="unclosed string
    """
    env = EnvParser.parse(content)
    assert env.keys == ["VALID_KEY", "ANOTHER_VALID"]
    
    syntax_errors = [e for e in env.entries if e.line_type == LineType.SYNTAX_ERROR]
    assert len(syntax_errors) == 2


def test_roundtrip_serialization():
    content = """# Comment line
APP_NAME="My Application"

PORT=3000 # Default port
"""
    env = EnvParser.parse(content)
    serialized = env.to_string()
    assert "# Comment line" in serialized
    assert 'APP_NAME="My Application"' in serialized
    assert "PORT=3000 # Default port" in serialized
