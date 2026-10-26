"""Command-line interface for dotenv-doctor using argparse."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from dotenv_doctor import __version__
from dotenv_doctor.checker import EnvChecker
from dotenv_doctor.fixer import EnvFixer
from dotenv_doctor.formatter import (
    Color,
    format_check_result,
    format_fix_result,
    format_issues,
    format_sync_result,
)
from dotenv_doctor.linter import EnvLinter
from dotenv_doctor.models import Severity
from dotenv_doctor.syncer import EnvSyncer


def create_parser() -> argparse.ArgumentParser:
    """Construct the command line parser."""
    parser = argparse.ArgumentParser(
        prog="dotenv-doctor",
        description="Production-grade doctor and diagnostics utility for .env and environment files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: check
    check_parser = subparsers.add_parser(
        "check",
        help="Compare .env against .env.example template to detect missing or mismatched variables.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    check_parser.add_argument(
        "target",
        nargs="?",
        default=".env",
        help="Target environment file to check.",
    )
    check_parser.add_argument(
        "reference",
        nargs="?",
        default=".env.example",
        help="Reference template file (e.g. .env.example).",
    )
    check_parser.add_argument(
        "--ignore-extra",
        action="store_true",
        help="Ignore extra variables present in target but not in reference.",
    )
    check_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 on warnings (e.g. empty or placeholder values).",
    )
    check_parser.add_argument(
        "--format",
        choices=["pretty", "simple", "json"],
        default="pretty",
        help="Output format.",
    )
    check_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized terminal output.",
    )

    # Command: lint
    lint_parser = subparsers.add_parser(
        "lint",
        help="Analyze environment files for syntax errors, weak secrets, and formatting issues.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    lint_parser.add_argument(
        "files",
        nargs="*",
        default=[".env"],
        help="One or more environment files to lint.",
    )
    lint_parser.add_argument(
        "--ignore-rule",
        action="append",
        default=[],
        help="Rule IDs to ignore (e.g., --ignore-rule lowercase-key). Can be specified multiple times.",
    )
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 on warnings as well as errors.",
    )
    lint_parser.add_argument(
        "--format",
        choices=["pretty", "simple", "json"],
        default="pretty",
        help="Output format.",
    )
    lint_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized terminal output.",
    )

    # Command: sync
    sync_parser = subparsers.add_parser(
        "sync",
        help="Synchronize target .env with reference .env.example, adding missing variables.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sync_parser.add_argument(
        "target",
        nargs="?",
        default=".env",
        help="Target environment file to update.",
    )
    sync_parser.add_argument(
        "reference",
        nargs="?",
        default=".env.example",
        help="Reference template file.",
    )
    sync_parser.add_argument(
        "--fill",
        choices=["example", "empty"],
        default="example",
        help="How to fill newly added missing variables: with example value or empty.",
    )
    sync_parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove keys in target that are not present in reference template.",
    )
    sync_parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Do not copy descriptive comments from reference file.",
    )
    sync_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a backup file (.env.bak) before modifying.",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display unified diff of changes without modifying target file.",
    )
    sync_parser.add_argument(
        "--format",
        choices=["pretty", "simple", "json"],
        default="pretty",
        help="Output format.",
    )
    sync_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized terminal output.",
    )

    # Command: fix
    fix_parser = subparsers.add_parser(
        "fix",
        help="Automatically repair safe syntax and formatting issues in .env files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    fix_parser.add_argument(
        "files",
        nargs="*",
        default=[".env"],
        help="One or more environment files to fix.",
    )
    fix_parser.add_argument(
        "--no-whitespace",
        action="store_true",
        help="Do not fix whitespace around '=' or trailing whitespace.",
    )
    fix_parser.add_argument(
        "--no-quoting",
        action="store_true",
        help="Do not auto-quote unquoted strings with whitespace.",
    )
    fix_parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Do not deduplicate repeated keys.",
    )
    fix_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a backup file before modifying.",
    )
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display unified diff of fixes without writing to disk.",
    )
    fix_parser.add_argument(
        "--format",
        choices=["pretty", "simple", "json"],
        default="pretty",
        help="Output format.",
    )
    fix_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colorized terminal output.",
    )

    return parser


def handle_check(args: argparse.Namespace) -> int:
    """Execute check command."""
    checker = EnvChecker(ignore_extra=args.ignore_extra, strict=args.strict)
    result = checker.check(args.target, args.reference)
    output = format_check_result(result, output_format=args.format)
    print(output)

    if result.has_errors:
        return 1
    if args.strict and not result.is_clean:
        return 1
    return 0


def handle_lint(args: argparse.Namespace) -> int:
    """Execute lint command."""
    # Flatten ignore rules if comma-separated
    flat_ignore = []
    for item in args.ignore_rule:
        flat_ignore.extend(r.strip() for r in item.split(",") if r.strip())

    linter = EnvLinter(ignore_rules=flat_ignore)
    all_issues = []
    for file_path in args.files:
        issues = linter.lint_file(file_path)
        all_issues.extend(issues)

    output = format_issues(all_issues, output_format=args.format)
    print(output)

    has_errors = any(i.severity == Severity.ERROR for i in all_issues)
    has_warnings = any(i.severity == Severity.WARNING for i in all_issues)

    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


def handle_sync(args: argparse.Namespace) -> int:
    """Execute sync command."""
    syncer = EnvSyncer(
        fill_mode=args.fill,
        prune=args.prune,
        preserve_comments=not args.no_comments,
        backup=not args.no_backup,
        dry_run=args.dry_run,
    )
    try:
        result = syncer.sync(args.target, args.reference)
    except Exception as e:
        Color.red(f"Error during sync: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = format_sync_result(result, output_format=args.format)
    print(output)
    return 0


def handle_fix(args: argparse.Namespace) -> int:
    """Execute fix command."""
    fixer = EnvFixer(
        fix_whitespace=not args.no_whitespace,
        fix_quoting=not args.no_quoting,
        fix_duplicates=not args.no_dedup,
        backup=not args.no_backup,
        dry_run=args.dry_run,
    )

    exit_code = 0
    for file_path in args.files:
        try:
            result = fixer.fix_file(file_path)
            output = format_fix_result(result, output_format=args.format)
            print(output)
        except Exception as e:
            print(f"Error fixing {file_path}: {e}", file=sys.stderr)
            exit_code = 1

    return exit_code


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if getattr(args, "no_color", False):
        Color.set_color(False)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "check":
        return handle_check(args)
    elif args.command == "lint":
        return handle_lint(args)
    elif args.command == "sync":
        return handle_sync(args)
    elif args.command == "fix":
        return handle_fix(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
