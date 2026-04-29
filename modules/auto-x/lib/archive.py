"""Raw JSONL archive with atomic write and 30-day dated rotation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from models import Tweet


_DATED_FILE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.jsonl$")


def _serialize(tweet: Tweet) -> dict:
    d = asdict(tweet)
    d["media_urls"] = list(tweet.media_urls)
    d["created_at"] = tweet.created_at.isoformat()
    return d


def write_raw_jsonl(path: str | Path, tweets: list[Tweet]) -> None:
    """Atomic write: build under .tmp suffix, then rename (POSIX rename = atomic on same FS)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for t in tweets:
            f.write(json.dumps(_serialize(t), ensure_ascii=False))
            f.write("\n")
    tmp.rename(path)


def rotate_raw_archive(
    archive_dir: str | Path,
    *,
    retain_days: int = 30,
    now: datetime,
) -> int:
    """Delete files matching YYYY-MM-DD.jsonl whose date is older than now - retain_days.
    Returns count deleted."""
    archive_dir = Path(archive_dir)
    if not archive_dir.is_dir():
        return 0

    cutoff = (now - timedelta(days=retain_days)).date()
    deleted = 0
    for entry in archive_dir.iterdir():
        m = _DATED_FILE_RE.match(entry.name)
        if not m:
            continue
        try:
            file_date = datetime(int(m[1]), int(m[2]), int(m[3])).date()
        except ValueError:
            continue
        if file_date < cutoff:
            entry.unlink()
            deleted += 1
    return deleted
