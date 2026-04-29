"""Import X cookies from a real Chrome session into Playwright storage_state.

Why this exists: X's bot detection breaks the headless Playwright login flow
(`x.com/i/flow/login` returns a generic "出错了" error before the form even
renders). Instead of fighting the detection, we let the user log in via their
NORMAL Chrome (with full fingerprint legitimacy), export cookies via a
browser extension, and inject them into Playwright's storage_state directly.

Usage:
    1. In your regular Chrome (already logged in to x.com), install Cookie-Editor:
       https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
    2. Open https://x.com, click Cookie-Editor → "Export" → "Export as JSON"
    3. Save the JSON to e.g. /tmp/x-cookies.json
    4. Run: python modules/auto-x/scripts/import_cookies.py /tmp/x-cookies.json

The script validates the export contains the required cookies (auth_token, ct0),
converts the Cookie-Editor format to Playwright's storage_state format, and
writes ~/.local/share/start-my-day/auto-x/session/storage_state.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_COOKIES = frozenset({"auth_token", "ct0"})


def _default_session_dir() -> Path:
    """Resolve the session directory at run time so XDG_DATA_HOME is honored.
    Mirrors what `today.py` does via `lib.storage.module_state_dir`, so the
    importer and the fetcher always agree on where storage_state.json lives."""
    from lib.storage import module_state_dir  # type: ignore[import-not-found]
    return module_state_dir("auto-x") / "session"


def _convert_same_site(value: str | None) -> str:
    """Cookie-Editor uses 'lax' / 'strict' / 'no_restriction' / 'unspecified' / None.
    Playwright wants 'Lax' / 'Strict' / 'None' (capitalized)."""
    if value is None or value in {"unspecified", "no_restriction"}:
        return "None"
    if value.lower() == "lax":
        return "Lax"
    if value.lower() == "strict":
        return "Strict"
    if value.lower() == "none":
        return "None"
    return "None"


def convert_cookies(raw: list[dict]) -> list[dict]:
    """Translate Cookie-Editor format → Playwright storage_state cookies.
    Filters to x.com / twitter.com domains only."""
    out: list[dict] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        domain = c.get("domain")
        name = c.get("name")
        if not domain or not name:
            continue
        if "x.com" not in domain and "twitter.com" not in domain:
            continue

        item: dict = {
            "name": name,
            "value": c.get("value", ""),
            "domain": domain,
            "path": c.get("path", "/"),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", False)),
            "sameSite": _convert_same_site(c.get("sameSite")),
        }
        # Skip `expires` for session cookies (no expiration). Cookie-Editor
        # uses `expirationDate` (float, seconds since epoch) for persistent ones.
        if not c.get("session", False):
            exp = c.get("expirationDate")
            if exp is not None:
                item["expires"] = float(exp)
        out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import X cookies into auto-x Playwright session.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="JSON file exported from Cookie-Editor (or compatible format).",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help=(
            "Where to write storage_state.json. Default: "
            "lib.storage.module_state_dir('auto-x')/session, "
            "which honors $XDG_DATA_HOME if set."
        ),
    )
    args = parser.parse_args(argv)
    if args.state_dir is None:
        args.state_dir = _default_session_dir()

    if not args.input.exists():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        raw = json.loads(args.input.read_text())
    except json.JSONDecodeError as e:
        print(f"could not parse {args.input} as JSON: {e}", file=sys.stderr)
        return 1

    if not isinstance(raw, list):
        print(
            f"expected a JSON array of cookies, got {type(raw).__name__}; "
            "did you export with Cookie-Editor → Export as JSON?",
            file=sys.stderr,
        )
        return 1

    converted = convert_cookies(raw)
    if not converted:
        print(
            "no x.com/twitter.com cookies found in input; "
            "make sure you exported while on the x.com page",
            file=sys.stderr,
        )
        return 1

    found_names = {c["name"] for c in converted}
    missing = REQUIRED_COOKIES - found_names
    if missing:
        print(
            f"required cookie(s) missing: {sorted(missing)}; "
            "make sure you exported while logged in to x.com",
            file=sys.stderr,
        )
        return 1

    args.state_dir.mkdir(parents=True, exist_ok=True)
    storage_state = {"cookies": converted, "origins": []}
    target = args.state_dir / "storage_state.json"
    target.write_text(json.dumps(storage_state, indent=2))

    print(f"Imported {len(converted)} cookies → {target}")
    print("You can now run: python modules/auto-x/scripts/today.py --output /tmp/x.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
