#!/usr/bin/env python3
"""Migrate ~/Documents/knowledge-vault/ content into ~/Documents/auto-reading-vault/learning/.

Spec: docs/superpowers/specs/2026-04-28-vault-merge-design.md

Usage:
    # Preview (default — no writes)
    python tools/migrate_vault.py --dry-run

    # Execute migration
    python tools/migrate_vault.py --apply

    # Audit a previously-migrated vault
    python tools/migrate_vault.py --verify
"""
import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger("migrate_vault")

DEFAULT_READING_VAULT = Path("~/Documents/auto-reading-vault").expanduser()
DEFAULT_LEARNING_VAULT = Path("~/Documents/knowledge-vault").expanduser()


class MigrationError(Exception):
    """Base class for migration failures."""


class PreflightError(MigrationError):
    """Raised when pre-conditions for --apply are not met."""


def check_preflight(reading_vault: Path, learning_vault: Path) -> None:
    """Validate paths and idempotency guard. Raises PreflightError on failure.

    - Reading vault must exist and be a directory.
    - Learning vault must exist and be a directory.
    - <reading-vault>/learning/ may exist if and only if it contains zero .md files
      (recursively). Existing .md files mean a previous --apply already ran;
      direct user to --verify instead.
    """
    if not reading_vault.is_dir():
        raise PreflightError(f"Reading vault not found: {reading_vault}")
    if not learning_vault.is_dir():
        raise PreflightError(f"Learning vault not found: {learning_vault}")
    target = reading_vault / "learning"
    if target.exists():
        existing_md = list(target.rglob("*.md"))
        if existing_md:
            raise PreflightError(
                f"{target} already contains {len(existing_md)} .md file(s). "
                "Run with --verify to audit, or remove the directory and re-run --apply."
            )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_vault",
        description="One-shot vault merge: copy knowledge-vault into auto-reading-vault/learning/.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="Preview the planned copies without writing (default).")
    mode.add_argument("--apply", action="store_true",
                      help="Execute the migration. Creates timestamped backups first.")
    mode.add_argument("--verify", action="store_true",
                      help="Audit a previously-migrated vault.")
    parser.add_argument("--reading-vault", type=Path, default=DEFAULT_READING_VAULT,
                        help=f"Path to reading vault (default: {DEFAULT_READING_VAULT}).")
    parser.add_argument("--learning-vault", type=Path, default=DEFAULT_LEARNING_VAULT,
                        help=f"Path to learning vault (default: {DEFAULT_LEARNING_VAULT}).")
    parser.add_argument("--verbose", action="store_true", help="Debug-level logging.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if args.apply:
        return cmd_apply(args.reading_vault, args.learning_vault)
    if args.verify:
        return cmd_verify(args.reading_vault, args.learning_vault)
    return cmd_dry_run(args.reading_vault, args.learning_vault)


def cmd_dry_run(reading_vault: Path, learning_vault: Path) -> int:
    """Print planned migration without writing anything."""
    raise NotImplementedError("Implemented in Task 5")


def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")
    # Subsequent phases added in Tasks 3–8.
    return 0


def cmd_verify(reading_vault: Path, learning_vault: Path) -> int:
    """Audit a previously-migrated vault."""
    raise NotImplementedError("Implemented in Task 10")


if __name__ == "__main__":
    sys.exit(main())
