"""One-time headed-browser login flow.

Usage:
    python -m modules.auto_x.scripts.login

Opens a headed Chromium at https://x.com/login. After the user completes
login (incl. 2FA), the page redirects to /home; the script saves the
user-data-dir and exits."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-time X login → save session.")
    parser.add_argument(
        "--session-dir",
        default=str(Path.home() / ".local/share/start-my-day/auto-x/session"),
        help="Where to persist Chromium user-data-dir.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="How long to wait for login redirect (default 5 min).",
    )
    args = parser.parse_args(argv)

    session_dir = Path(args.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    print(f"Opening headed Chromium at https://x.com/login")
    print(f"Session will be saved to: {session_dir}")
    print(
        f"Complete login (incl. 2FA). Waiting up to {args.timeout_seconds}s for redirect to /home..."
    )

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False,
        )
        page = ctx.new_page()
        page.goto("https://x.com/login", timeout=args.timeout_seconds * 1000)

        deadline = time.time() + args.timeout_seconds
        while time.time() < deadline:
            if page.url.startswith("https://x.com/home"):
                ctx.close()
                print("Session saved.")
                return 0
            time.sleep(2)

        ctx.close()
        print("Timed out waiting for login redirect.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
