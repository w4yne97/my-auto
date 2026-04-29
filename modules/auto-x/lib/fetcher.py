"""Playwright-driven fetch of the user's X Following timeline.

This is the ONLY file in the codebase that imports playwright. Other modules
exercise it via the `fetch_following_timeline` public function or by stubbing
it out in tests via monkeypatch. Playwright is imported lazily inside the
public function so module-level loading does not require playwright to be
installed (unit tests only need the parser helpers)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from models import Tweet


@dataclass
class FetcherError(Exception):
    """Raised by fetcher on any failure path. `code` is one of:
       'auth', 'network', 'parse', 'rate_limited', 'browser_crash'.
    `detail` is a human-readable description (raw error text)."""
    code: str
    detail: str = ""

    def __str__(self) -> str:  # pragma: no cover (cosmetic)
        return f"FetcherError({self.code}): {self.detail}"


# --- Public API ----------------------------------------------------------


def fetch_following_timeline(
    *,
    session_dir: Path,
    window_start: datetime,
    max_tweets: int = 200,
    timeout_seconds: int = 60,
) -> list[Tweet]:
    """Launch a headless Chromium with cookies loaded from
    `session_dir/storage_state.json`, navigate to https://x.com/home, switch to
    the Following tab, scroll until either `max_tweets` collected or the first
    tweet older than `window_start` is seen.

    Includes 1× retry on rate-limit soft-block (60 s sleep). Returns a list of
    Tweet ordered newest-first (the order produced by sequentially observed
    GraphQL payloads as the user scrolls).

    The storage_state.json file is produced by `scripts/import_cookies.py` after
    the user exports cookies from their normal logged-in Chrome session via a
    Cookie-Editor extension. We do NOT attempt headless login — X's bot
    detection breaks the login SPA at /i/flow/login."""
    storage_state = session_dir / "storage_state.json"
    if not storage_state.exists():
        raise FetcherError(
            "auth",
            f"no storage_state at {storage_state}; "
            "run: python modules/auto-x/scripts/import_cookies.py /path/to/cookies.json",
        )

    from playwright.sync_api import (  # type: ignore[import-not-found]
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )

    collected: list[Tweet] = []
    seen_ids: set[str] = set()

    def collect_from_response(payload: Any) -> bool:
        """Append parsed tweets from a single GraphQL payload. Returns True
        if a tweet older than window_start has been seen (signal to stop)."""
        try:
            nodes = _extract_graphql_response(payload)
        except FetcherError:
            raise
        oldest_seen = False
        for node in nodes:
            try:
                t = _parse_tweet_node(node)
            except FetcherError:
                continue
            if t.tweet_id in seen_ids:
                continue
            seen_ids.add(t.tweet_id)
            if t.created_at < window_start:
                oldest_seen = True
                continue
            collected.append(t)
            if len(collected) >= max_tweets:
                return True
        return oldest_seen

    last_err_detail: str = ""

    for attempt in (1, 2):  # 1× retry on rate_limited
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    ctx = browser.new_context(storage_state=str(storage_state))
                    page = ctx.new_page()

                    payloads: list[Any] = []

                    def on_response(resp):
                        if "HomeTimeline" in resp.url or "HomeLatestTimeline" in resp.url:
                            try:
                                payloads.append(resp.json())
                            except Exception:
                                pass  # binary or non-JSON body; ignore

                    page.on("response", on_response)

                    page.goto("https://x.com/home", timeout=timeout_seconds * 1000)

                    if not _is_logged_in(page.url):
                        raise FetcherError(
                            "auth",
                            f"redirected to {page.url} (cookies likely expired; re-export)",
                        )

                    # Try to switch to "Following" tab. CSS / role labels can drift;
                    # if absent (already on Following or DOM changed), continue —
                    # parse-side errors will surface separately.
                    try:
                        page.get_by_role("tab", name="Following").click(timeout=5000)
                    except PlaywrightTimeoutError:
                        pass

                    done = False
                    for _ in range(50):
                        if done or len(collected) >= max_tweets:
                            break
                        page.mouse.wheel(0, 5000)
                        page.wait_for_timeout(800)
                        while payloads:
                            done = collect_from_response(payloads.pop(0)) or done

                    # Soft-block detection (X surfaces a "Try again later" toast).
                    body_text = (page.inner_text("body") or "").lower()
                    if "try again later" in body_text or "rate limit" in body_text:
                        raise FetcherError("rate_limited", "X soft-blocked the session")

                    return collected
                finally:
                    browser.close()

        except FetcherError as e:
            if e.code == "rate_limited" and attempt == 1:
                last_err_detail = e.detail
                time.sleep(60)
                collected.clear()
                seen_ids.clear()
                continue
            raise
        except PlaywrightTimeoutError as e:
            raise FetcherError("network", str(e))
        except PlaywrightError as e:
            raise FetcherError("browser_crash", str(e))

    # Both attempts hit rate_limited
    raise FetcherError(
        "rate_limited",
        f"{last_err_detail} (after 1 retry, 60s sleep)",
    )


# --- Private helpers (exercised by tests) ---------------------------------


def _is_logged_in(url: str) -> bool:
    """Logged-in landing URL is /home (with arbitrary query string).
    Login URLs include /login or /i/flow/login."""
    return url.startswith("https://x.com/home") and "/login" not in url


def _extract_graphql_response(payload: Any) -> list[dict]:
    """Walk the HomeTimeline GraphQL shape and return tweet 'result' nodes."""
    try:
        instructions = payload["data"]["home"]["home_timeline_urt"]["instructions"]
    except (KeyError, TypeError) as e:
        raise FetcherError(
            "parse",
            f"missing path data.home.home_timeline_urt.instructions: {e}",
        )

    nodes: list[dict] = []
    for instr in instructions:
        if instr.get("type") != "TimelineAddEntries":
            continue
        for entry in instr.get("entries") or []:
            try:
                result = entry["content"]["itemContent"]["tweet_results"]["result"]
            except (KeyError, TypeError):
                continue
            nodes.append(result)
    return nodes


def _parse_tweet_node(node: dict) -> Tweet:
    """Translate a single tweet result node into a Tweet dataclass.
    Raises FetcherError(parse) on any missing required field."""
    try:
        rest_id = node["rest_id"]
        legacy = node["legacy"]
        full_text = legacy["full_text"]
        created_raw = legacy["created_at"]
        like_count = legacy.get("favorite_count", 0)
        retweet_count = legacy.get("retweet_count", 0)
        reply_count = legacy.get("reply_count", 0)
        lang = legacy.get("lang")
        in_reply_to = legacy.get("in_reply_to_status_id_str")
        user_legacy = node["core"]["user_results"]["result"]["legacy"]
        screen_name = user_legacy["screen_name"]
        display_name = user_legacy["name"]
    except (KeyError, TypeError) as e:
        raise FetcherError("parse", f"missing required field in tweet node: {e}")

    media = legacy.get("entities", {}).get("media") or []
    media_urls = tuple(
        m["media_url_https"] for m in media if "media_url_https" in m
    )

    try:
        created_at = parsedate_to_datetime(created_raw)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
    except (TypeError, ValueError) as e:
        raise FetcherError("parse", f"unparseable created_at {created_raw!r}: {e}")

    return Tweet(
        tweet_id=rest_id,
        author_handle=f"@{screen_name}",
        author_display_name=display_name,
        text=full_text,
        created_at=created_at,
        url=f"https://x.com/{screen_name}/status/{rest_id}",
        like_count=int(like_count),
        retweet_count=int(retweet_count),
        reply_count=int(reply_count),
        is_thread_root=in_reply_to is None,
        media_urls=media_urls,
        lang=lang,
    )
