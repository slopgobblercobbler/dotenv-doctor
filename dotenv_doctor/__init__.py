"""dotenv-doctor: Production-grade developer CLI & library for .env health."""
from __future__ import annotations

from dotenv_doctor.checker import CheckResult, EnvChecker, check
from dotenv_doctor.fixer import EnvFixer, FixResult, fix
from dotenv_doctor.linter import EnvLinter, lint
from dotenv_doctor.models import EnvEntry, EnvFile, Issue, LineType, Severity
from dotenv_doctor.parser import EnvParser
from dotenv_doctor.syncer import EnvSyncer, SyncResult, sync

__version__ = "0.1.0"

parse = EnvParser.parse

__all__ = [
    "__version__",
    "parse",
    "check",
    "lint",
    "sync",
    "fix",
    "EnvParser",
    "EnvFile",
    "EnvEntry",
    "Issue",
    "Severity",
    "LineType",
    "EnvChecker",
    "CheckResult",
    "EnvLinter",
    "EnvSyncer",
    "SyncResult",
    "EnvFixer",
    "FixResult",
]
