"""Obsidian CLI wrapper -- single entry point for all vault operations."""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_MACOS_DEFAULT = "/Applications/Obsidian.app/Contents/MacOS/obsidian"

_NO_MATCHES = "No matches found."


class CLINotFoundError(Exception):
    """Obsidian CLI not installed or not in PATH."""


class ObsidianNotRunningError(Exception):
    """Obsidian app is not running (CLI requires it)."""


class VaultNotFoundError(Exception):
    """Raised when Obsidian CLI's `vault info=path` returns a non-path response,
    typically because no vault is open or OBSIDIAN_VAULT_NAME is misconfigured.
    """


class ObsidianCLI:
    """Obsidian CLI wrapper. Single entry point for all vault operations.

    Immutable after __init__ -- vault_name, vault_path, and _cli_path
    are set once and never change.

    Argument format: all key=value pairs are passed WITHOUT shell quoting
    around values, since subprocess.run receives a list and does not use
    a shell. The CLI parses ``key=value`` tokens directly.
    """

    def __init__(self, vault_name: str | None = None) -> None:
        self._vault_name = vault_name
        self._cli_path = self._find_cli()
        self._vault_path = self._resolve_vault_path()

    @property
    def vault_name(self) -> str | None:
        return self._vault_name

    @property
    def vault_path(self) -> str:
        return self._vault_path

    # -- Internal -----------------------------------------------------------

    @staticmethod
    def _find_cli() -> str:
        env_path = os.environ.get("OBSIDIAN_CLI_PATH")
        if env_path:
            if not Path(env_path).exists():
                raise CLINotFoundError(
                    f"OBSIDIAN_CLI_PATH points to non-existent path: {env_path}"
                )
            return env_path

        which_path = shutil.which("obsidian")
        if which_path:
            return which_path

        if Path(_MACOS_DEFAULT).exists():
            return _MACOS_DEFAULT

        raise CLINotFoundError(
            "Obsidian CLI not found. Install it via Obsidian Settings -> General -> "
            "Command line interface, then register to PATH."
        )

    def _resolve_vault_path(self) -> str:
        out = self._run("vault", "info=path").strip()
        candidate = Path(out).expanduser() if out else None
        if not candidate or not candidate.is_absolute() or not candidate.exists():
            raise VaultNotFoundError(
                f"Obsidian CLI returned non-path output: {out!r}. "
                f"Likely causes: no vault is open in Obsidian, OBSIDIAN_VAULT_NAME "
                f"mismatches a registered vault, or Obsidian CLI registration is stale. "
                f"Check `obsidian vault list` and `obsidian vault info=path`."
            )
        return out

    def _run(self, *args: str, timeout: int = 30) -> str:
        cmd = [self._cli_path, *args]
        if self._vault_name:
            cmd.append(f"vault={self._vault_name}")

        logger.debug("CLI: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Obsidian CLI timed out after {timeout}s: {' '.join(cmd)}"
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "connect" in stderr.lower() or "ipc" in stderr.lower():
                raise ObsidianNotRunningError(
                    "Obsidian app must be running to use the CLI. "
                    "Please start Obsidian."
                )
            raise RuntimeError(f"Obsidian CLI error: {stderr}")

        return result.stdout

    # ── File operations ───────────────────────────────────────

    def create_note(self, path: str, content: str, overwrite: bool = False) -> str:
        args = ["create", f"path={path}", f"content={content}"]
        if overwrite:
            args.append("overwrite")
        self._run(*args)
        return path

    def read_note(self, path: str) -> str:
        return self._run("read", f"path={path}")

    def delete_note(self, path: str, permanent: bool = False) -> None:
        args = ["delete", f"path={path}"]
        if permanent:
            args.append("permanent")
        self._run(*args)

    # ── Property operations ───────────────────────────────────

    def get_property(self, path: str, name: str) -> str | None:
        try:
            out = self._run("property:read", f"name={name}", f"path={path}")
            value = out.strip()
            return value if value else None
        except RuntimeError:
            return None

    def set_property(self, path: str, name: str, value: str, prop_type: str = "text") -> None:
        self._run(
            "property:set", f"name={name}", f"value={value}",
            f"type={prop_type}", f"path={path}",
        )

    # ── Search ────────────────────────────────────────────────

    def search(self, query: str, path: str | None = None, limit: int | None = None) -> list[str]:
        args = ["search", f"query={query}", "format=json"]
        if path:
            args.append(f"path={path}")
        if limit is not None:
            args.append(f"limit={limit}")
        out = self._run(*args, timeout=60)
        stripped = out.strip()
        if not stripped or stripped == _NO_MATCHES:
            return []
        return json.loads(stripped)

    def search_context(self, query: str, path: str | None = None, limit: int | None = None) -> list[dict]:
        args = ["search:context", f"query={query}", "format=json"]
        if path:
            args.append(f"path={path}")
        if limit is not None:
            args.append(f"limit={limit}")
        out = self._run(*args, timeout=60)
        stripped = out.strip()
        if not stripped or stripped == _NO_MATCHES:
            return []
        return json.loads(stripped)

    # ── Link graph ────────────────────────────────────────────

    def backlinks(self, path: str) -> list[str]:
        out = self._run("backlinks", f"path={path}", "format=json")
        entries = json.loads(out) if out.strip() else []
        return [e["file"] for e in entries]

    def outgoing_links(self, path: str) -> list[str]:
        out = self._run("links", f"path={path}")
        return [line for line in out.strip().splitlines() if line]

    def unresolved_links(self) -> list[dict]:
        out = self._run("unresolved", "format=json")
        return json.loads(out) if out.strip() else []

    # ── File listing ──────────────────────────────────────────

    def list_files(self, folder: str | None = None, ext: str | None = None) -> list[str]:
        args = ["files"]
        if folder:
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={ext}")
        out = self._run(*args)
        return [line for line in out.strip().splitlines() if line]

    def file_count(self, folder: str | None = None, ext: str | None = None) -> int:
        args = ["files", "total"]
        if folder:
            args.append(f"folder={folder}")
        if ext:
            args.append(f"ext={ext}")
        out = self._run(*args)
        return int(out.strip())

    # ── Tags ──────────────────────────────────────────────────

    def tags(self, path: str | None = None) -> list[dict]:
        args = ["tags", "format=json"]
        if path:
            args.append(f"path={path}")
        out = self._run(*args)
        return json.loads(out) if out.strip() else []

    # ── Vault info ────────────────────────────────────────────

    def vault_info(self) -> dict:
        out = self._run("vault")
        result = {}
        for line in out.strip().splitlines():
            if "\t" in line:
                key, value = line.split("\t", 1)
                result[key] = value
        return result
