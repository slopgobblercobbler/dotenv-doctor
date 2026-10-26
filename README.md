# dotenv-doctor 🩺

[![CI](https://github.com/slopgobblercobbler/dotenv-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/slopgobblercobbler/dotenv-doctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)

> **Production-grade developer CLI and library to validate, lint, repair, and synchronize `.env` files with zero external runtime dependencies.**

`dotenv-doctor` keeps your environment configurations healthy across developer machines, staging environments, and production CI/CD pipelines. It prevents missing environment variables from crashing production containers, detects weak or leaked placeholder secrets, enforces syntax hygiene, and synchronizes `.env` files against `.env.example` templates automatically.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Commands & Usage](#cli-commands--usage)
  - [`dotenv-doctor check`](#dotenv-doctor-check)
  - [`dotenv-doctor lint`](#dotenv-doctor-lint)
  - [`dotenv-doctor sync`](#dotenv-doctor-sync)
  - [`dotenv-doctor fix`](#dotenv-doctor-fix)
- [Lint Rules & Security Detectors](#lint-rules--security-detectors)
- [Python Library API](#python-library-api)
- [CI/CD & Pre-commit Integration](#cicd--pre-commit-integration)
- [License](#license)

---

## Features

- 🔍 **Template Comparison (`check`)**: Verifies that your local `.env` has all required keys declared in `.env.example`, alerts on undocumented keys, detects empty values, and spots unmodified default placeholders.
- 🛡️ **Static Analysis & Security Scanning (`lint`)**: Identifies broken syntax, unclosed quotes, duplicate definitions, unescaped whitespace, weak/default credentials (`changeme`, `admin`, `123456`), and insecure HTTP endpoints.
- 🔄 **Safe Synchronization (`sync`)**: Syncs missing keys into your `.env` from template files with comment preservation and automatic `.env.bak` backups. Supports pruning orphaned variables and dry-run unified diffs.
- 🛠️ **Automated Repair (`fix`)**: Automatically strips illegal whitespace around `=` separators, properly quotes strings containing spaces, and deduplicates repeated variable declarations.
- ⚡ **Zero Runtime Dependencies**: Written entirely using Python standard libraries for instant startup, zero supply-chain risk, and maximum portability.
- 📊 **Multi-format Output**: Human-friendly colorized terminal output, plain simple output for UNIX pipes, and structured JSON output for toolchain integrations.

---

## Installation

### Via pip

```bash
pip install dotenv-doctor
```

### From GitHub source

```bash
pip install git+https://github.com/slopgobblercobbler/dotenv-doctor.git
```

---

## Quick Start

```bash
# 1. Compare your local .env against the template
dotenv-doctor check .env .env.example

# 2. Lint environment files for syntax errors and weak secrets
dotenv-doctor lint .env .env.staging

# 3. Synchronize missing variables into .env from .env.example
dotenv-doctor sync .env .env.example

# 4. Automatically repair syntax & formatting issues
dotenv-doctor fix .env
```

---

## CLI Commands & Usage

### `dotenv-doctor check`

Compare a target `.env` file against a reference template (such as `.env.example` or `.env.template`) to verify all expected variables are declared and properly configured.

```bash
dotenv-doctor check [target] [reference] [OPTIONS]
```

#### Arguments & Options

| Argument / Flag | Default | Description |
|---|---|---|
| `target` | `.env` | Path to target environment file. |
| `reference` | `.env.example` | Path to reference template file. |
| `--ignore-extra` | `False` | Ignore extra variables present in target but not in template. |
| `--strict` | `False` | Exit with code `1` on warnings (e.g., extra keys or unmodified placeholders). |
| `--format` | `pretty` | Output format: `pretty`, `simple`, or `json`. |
| `--no-color` | `False` | Suppress ANSI color escape sequences. |

#### Example

```bash
dotenv-doctor check .env .env.example --strict --format pretty
```

---

### `dotenv-doctor lint`

Statically analyze one or more `.env` files for syntax errors, formatting inconsistencies, and weak credentials.

```bash
dotenv-doctor lint [files...] [OPTIONS]
```

#### Arguments & Options

| Argument / Flag | Default | Description |
|---|---|---|
| `files` | `[".env"]` | One or more `.env` files to scan. |
| `--ignore-rule` | `[]` | Rule IDs to bypass (e.g. `--ignore-rule lowercase-key`). Repeatable or comma-separated. |
| `--strict` | `False` | Exit with code `1` on warnings in addition to errors. |
| `--format` | `pretty` | Output format: `pretty`, `simple`, or `json`. |
| `--no-color` | `False` | Disable colorized terminal output. |

#### Example

```bash
dotenv-doctor lint .env .env.production --ignore-rule lowercase-key --strict
```

---

### `dotenv-doctor sync`

Merge missing keys from your template into your working `.env` file without overwriting existing configured values. Preserves comments, creates automatic backups, and supports diff preview.

```bash
dotenv-doctor sync [target] [reference] [OPTIONS]
```

#### Arguments & Options

| Argument / Flag | Default | Description |
|---|---|---|
| `target` | `.env` | Path to target environment file to update. |
| `reference` | `.env.example` | Path to template file. |
| `--fill` | `example` | How to populate newly added keys: `example` (use template value) or `empty` (`KEY=`). |
| `--prune` | `False` | Delete keys in target that are not declared in the reference template. |
| `--no-comments` | `False` | Omit section comments from the reference template. |
| `--no-backup` | `False` | Do not create a `.env.bak` backup file before writing changes. |
| `--dry-run` | `False` | Output unified diff without modifying files on disk. |
| `--format` | `pretty` | Output format: `pretty`, `simple`, or `json`. |
| `--no-color` | `False` | Disable ANSI color codes. |

#### Example

```bash
dotenv-doctor sync .env .env.example --dry-run
dotenv-doctor sync .env .env.example --fill empty --prune
```

---

### `dotenv-doctor fix`

Automatically repair common syntax defects, illegal spaces around the `=` separator, unquoted values containing spaces, and duplicate variable definitions.

```bash
dotenv-doctor fix [files...] [OPTIONS]
```

#### Arguments & Options

| Argument / Flag | Default | Description |
|---|---|---|
| `files` | `[".env"]` | One or more files to repair. |
| `--no-whitespace`| `False` | Skip fixing spaces around `=` or trailing whitespace. |
| `--no-quoting` | `False` | Skip auto-quoting strings containing whitespace. |
| `--no-dedup` | `False` | Skip deduplication of repeated variable definitions. |
| `--no-backup` | `False` | Do not create a backup file before writing changes. |
| `--dry-run` | `False` | Display unified diff preview without modifying files. |
| `--format` | `pretty` | Output format: `pretty`, `simple`, or `json`. |
| `--no-color` | `False` | Disable color formatting. |

#### Example

```bash
dotenv-doctor fix .env --dry-run
dotenv-doctor fix .env .env.local
```

---

## Lint Rules & Security Detectors

| Rule ID | Severity | Description |
|---|---|---|
| `syntax-error` | **ERROR** | Missing `=` assignment separator on non-comment lines. |
| `unclosed-quote` | **ERROR** | Unbalanced or unclosed single/double quotes. |
| `invalid-key-name` | **ERROR** | Key names containing invalid characters or starting with numbers. |
| `whitespace-around-equals` | **WARNING** | Stray spaces around `=`, e.g. `KEY = value` (causes parsing bugs in loaders). |
| `duplicate-key` | **WARNING / INFO** | Keys defined multiple times in the same file. |
| `unescaped-value` | **WARNING** | Unquoted values that contain whitespace characters. |
| `weak-default-secret` | **WARNING** | Sensitive keys assigned placeholder/weak secrets (`changeme`, `123456`, `admin`). |
| `insecure-url` | **WARNING** | Sensitive endpoint URLs using unencrypted `http://` instead of `https://`. |
| `lowercase-key` | **INFO** | Variable name contains lowercase characters instead of `SCREAMING_SNAKE_CASE`. |
| `trailing-whitespace` | **INFO** | Unnecessary trailing spaces or tabs at end of line. |

---

## Python Library API

`dotenv-doctor` provides a full Python API for custom tooling and script integration:

```python
from dotenv_doctor import check, lint, sync, fix, parse

# Parse an environment file into an object model
env = parse(".env")
print("Declared keys:", env.keys)
print("Database host:", env.get_value("DB_HOST"))

# Perform health comparison check
result = check(target=".env", reference=".env.example", strict=True)
if not result.is_clean:
    print(f"Missing keys: {result.missing_keys}")
    print(f"Extra keys: {result.extra_keys}")

# Run linter programmatically
issues = lint(".env", ignore_rules=["lowercase-key"])
for issue in issues:
    print(f"[{issue.severity.value}] {issue.rule_id}: {issue.message}")

# Synchronize files programmatically
sync_res = sync(target=".env", reference=".env.example", fill_mode="example", dry_run=False)
print(f"Added keys: {sync_res.added_keys}")

# Fix safe formatting defects
fix_res = fix(".env", dry_run=False)
print(f"Fixed {fix_res.fixed_issues_count} issue(s)")
```

---

## CI/CD & Pre-commit Integration

### GitHub Actions Workflow

Add `.github/workflows/dotenv-check.yml` to validate your environment template files on every Pull Request:

```yaml
name: Verify Environment Templates

on:
  pull_request:
    paths:
      - '**/.env.example'
      - '**/.env.template'

jobs:
  dotenv-doctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install dotenv-doctor
      - name: Lint Template Files
        run: dotenv-doctor lint .env.example --strict
```

### Pre-commit Hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/slopgobblercobbler/dotenv-doctor
    rev: v0.1.0
    hooks:
      - id: dotenv-doctor-lint
        args: ["--strict"]
      - id: dotenv-doctor-check
        args: [".env", ".env.example"]
```

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).
Copyright (c) 2026 slopgobblercobbler.
