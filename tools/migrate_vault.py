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
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("migrate_vault")

DEFAULT_READING_VAULT = Path("~/Documents/auto-reading-vault").expanduser()
DEFAULT_LEARNING_VAULT = Path("~/Documents/knowledge-vault").expanduser()


class MigrationError(Exception):
    """Base class for migration failures."""


class PreflightError(MigrationError):
    """Raised when pre-conditions for --apply are not met."""


FOLDER_PATTERN = re.compile(r"^[0-9]{2}_[A-Za-z][A-Za-z0-9-]*$")


@dataclass(frozen=True)
class FolderEntry:
    """One folder slated for migration."""
    name: str        # e.g. "10_Foundations"
    src: Path        # e.g. /Users/.../knowledge-vault/10_Foundations
    dst: Path        # e.g. /Users/.../auto-reading-vault/learning/10_Foundations
    md_count: int    # number of .md files (recursive) inside src


@dataclass(frozen=True)
class Manifest:
    """The full set of folders to migrate, in deterministic order."""
    folders: tuple[FolderEntry, ...]

    @property
    def total_md_files(self) -> int:
        return sum(f.md_count for f in self.folders)


def build_manifest(learning_vault: Path, reading_vault: Path) -> Manifest:
    """Walk learning_vault's top-level entries; return manifest of folders to migrate.

    Inclusion rule (both must hold):
      1. Folder name matches FOLDER_PATTERN (Johnny.Decimal: "NN_Name").
      2. Folder contains ≥1 .md file recursively.
    """
    target_root = reading_vault / "learning"
    entries: list[FolderEntry] = []
    for child in sorted(learning_vault.iterdir()):
        if not child.is_dir():
            continue
        if not FOLDER_PATTERN.match(child.name):
            continue
        md_count = sum(1 for _ in child.rglob("*.md"))
        if md_count == 0:
            continue
        entries.append(FolderEntry(
            name=child.name,
            src=child,
            dst=target_root / child.name,
            md_count=md_count,
        ))
    return Manifest(folders=tuple(entries))


def perform_copy(manifest: Manifest, reading_vault: Path) -> None:
    """Copy each manifest folder from src to dst. Source is preserved (copytree)."""
    target_root = reading_vault / "learning"
    target_root.mkdir(parents=True, exist_ok=True)
    for entry in manifest.folders:
        # copytree refuses to overwrite an existing dst by default — that's correct here:
        # Task 2's preflight has guaranteed dst doesn't already contain .md content.
        if entry.dst.exists() and not any(entry.dst.iterdir()):
            entry.dst.rmdir()  # remove empty pre-existing dst so copytree can create it
        shutil.copytree(entry.src, entry.dst)
        logger.info("Copied %s -> %s (%d files)", entry.src.name, entry.dst, entry.md_count)


def find_zero_byte_untitled(reading_vault: Path) -> list[Path]:
    """Return zero-byte files matching Untitled*.md in reading-vault root (non-recursive)."""
    return [
        p for p in reading_vault.glob("Untitled*.md")
        if p.is_file() and p.stat().st_size == 0
    ]


def cleanup_untitled_stubs(reading_vault: Path) -> list[Path]:
    """Delete zero-byte Untitled*.md stubs. Returns list of deleted paths."""
    stubs = find_zero_byte_untitled(reading_vault)
    for p in stubs:
        p.unlink()
        logger.info("Removed zero-byte stub: %s", p.name)
    return stubs


def make_backup_paths(
    reading_vault: Path, learning_vault: Path, now: datetime
) -> tuple[Path, Path]:
    """Construct timestamped backup destination paths (siblings of each vault)."""
    stamp = now.strftime("%Y%m%d-%H%M%S")
    rd_backup = reading_vault.with_name(f"{reading_vault.name}.premerge-{stamp}")
    ln_backup = learning_vault.with_name(f"{learning_vault.name}.premerge-{stamp}")
    return rd_backup, ln_backup


def create_backups(reading_vault: Path, learning_vault: Path) -> tuple[Path, Path]:
    """Copy both vaults to timestamped sibling backup directories. Returns (rd, ln) paths."""
    rd_backup, ln_backup = make_backup_paths(reading_vault, learning_vault, datetime.now())
    shutil.copytree(reading_vault, rd_backup)
    shutil.copytree(learning_vault, ln_backup)
    logger.info("Backup: reading -> %s", rd_backup)
    logger.info("Backup: learning -> %s", ln_backup)
    return rd_backup, ln_backup


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


def find_md_files(vault: Path) -> list[Path]:
    """Return all .md files under a vault, excluding `.obsidian/` and any pre-existing
    `learning/` subtree (which is the migration target, not source content)."""
    excluded_dirs = {".obsidian", "learning"}
    out: list[Path] = []
    for path in vault.rglob("*.md"):
        # Skip if any ancestor folder name (relative to vault) is in excluded_dirs
        rel_parts = path.relative_to(vault).parts
        if any(part in excluded_dirs for part in rel_parts[:-1]):
            continue
        out.append(path)
    return out


def check_basename_collisions(reading_vault: Path, learning_vault: Path) -> list[tuple[Path, Path]]:
    """Return list of (reading_path, learning_path) pairs sharing a basename.

    Empty list means no collisions.
    """
    reading_files = {p.name: p for p in find_md_files(reading_vault)}
    learning_files = find_md_files(learning_vault)
    collisions: list[tuple[Path, Path]] = []
    for lp in learning_files:
        if lp.name in reading_files:
            collisions.append((reading_files[lp.name], lp))
    return collisions


def _print_plan(reading_vault: Path, learning_vault: Path, manifest: Manifest) -> None:
    """Print a human-readable plan summary to stdout."""
    rd_count = len(find_md_files(reading_vault))
    print(f"Source vaults:")
    print(f"  reading:  {reading_vault}   ({rd_count} .md files)")
    print(f"  learning: {learning_vault}  ({manifest.total_md_files} .md files)")
    print()
    print("Pre-flight: OK")
    print("Basename collisions: 0")
    print()
    print(f"Planned copies ({manifest.total_md_files} files across {len(manifest.folders)} folders):")
    for entry in manifest.folders:
        print(f"  {entry.src.name}/  ->  {entry.dst}  ({entry.md_count} file(s))")


def cmd_dry_run(reading_vault: Path, learning_vault: Path) -> int:
    """Print planned migration without writing anything."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    manifest = build_manifest(learning_vault, reading_vault)
    _print_plan(reading_vault, learning_vault, manifest)
    print()
    print("[--dry-run mode: no changes written. Re-run with --apply to execute.]")
    return 0


def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration.

    Failure modes & recovery:
    - If `create_backups` raises mid-way, one vault may be backed up but not the other.
      The user should remove any orphaned `*.premerge-<stamp>/` directory before re-running.
    - If `perform_copy` raises mid-way (disk full, permissions), the reading vault will
      be left half-merged with some folders under `learning/` populated and others absent.
      The next `--apply` will be blocked by the preflight idempotency guard. To recover,
      `rm -rf <reading-vault>/learning/` and re-run `--apply`.
    """
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")

    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    logger.info("Basename collisions: 0")

    manifest = build_manifest(learning_vault, reading_vault)
    logger.info("Manifest: %d folders, %d .md files",
                len(manifest.folders), manifest.total_md_files)

    create_backups(reading_vault, learning_vault)
    perform_copy(manifest, reading_vault)
    deleted = cleanup_untitled_stubs(reading_vault)
    logger.info("Cleanup: removed %d zero-byte Untitled*.md stub(s)", len(deleted))
    logger.info("Apply complete.")
    return 0


def _find_latest_backup(vault: Path) -> Path | None:
    """Find the most recent .premerge-* backup sibling of vault, if any."""
    candidates = sorted(
        vault.parent.glob(f"{vault.name}.premerge-*"),
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def verify_migration(
    reading_vault: Path, learning_vault: Path
) -> tuple[bool, list[str]]:
    """Audit a previously-migrated vault. Returns (ok, messages).

    Mode priority for source-of-truth manifest:
      1. Backup of learning-vault (most authoritative — frozen pre-merge state)
      2. Live learning-vault (still exists if user hasn't manually deleted)
      3. Target-only (degraded — only checks shape, not completeness)
    """
    messages: list[str] = []
    target = reading_vault / "learning"
    if not target.is_dir():
        messages.append(f"Target {target} does not exist — vault is not merged.")
        return False, messages

    target_md = list(target.rglob("*.md"))
    if not target_md:
        messages.append(f"Target {target} exists but contains no .md files.")
        return False, messages

    # Determine source-of-truth for manifest
    learning_backup = _find_latest_backup(learning_vault)
    if learning_backup is not None and learning_backup.is_dir():
        source = learning_backup
        mode = 1
    elif learning_vault.is_dir():
        source = learning_vault
        mode = 2
    else:
        messages.append(
            f"Mode 3 (degraded): no backup, no source vault. "
            f"Found {len(target_md)} .md file(s) under {target}, but completeness cannot be verified."
        )
        return True, messages

    # Mode 1 or 2: rebuild manifest from source and check each file is present in target
    expected_manifest = build_manifest(source, reading_vault)
    missing: list[Path] = []
    for entry in expected_manifest.folders:
        for src_md in entry.src.rglob("*.md"):
            rel = src_md.relative_to(entry.src)
            expected_dst = entry.dst / rel
            if not expected_dst.is_file():
                missing.append(expected_dst)

    if missing:
        messages.append(f"Mode {mode}: {len(missing)} expected file(s) missing in target.")
        for m in missing[:5]:
            messages.append(f"  missing: {m}")
        return False, messages
    messages.append(
        f"Mode {mode}: verified {expected_manifest.total_md_files} file(s) "
        f"across {len(expected_manifest.folders)} folder(s)."
    )
    return True, messages


def cmd_verify(reading_vault: Path, learning_vault: Path) -> int:
    """Audit a previously-migrated vault."""
    if not reading_vault.is_dir():
        logger.error("Reading vault not found: %s", reading_vault)
        return 1
    ok, messages = verify_migration(reading_vault, learning_vault)
    for m in messages:
        if ok:
            logger.info("%s", m)
        else:
            logger.error("%s", m)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
