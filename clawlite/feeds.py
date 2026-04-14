"""RSS feed subscription + fetching — pure Python, no LLM in the loop.

Layout:
    ~/.clawlite/feeds.json         Subscriptions + dedup state.
    memory/feeds/<slug>.jsonl      Per-feed inbox. Written on fetch, drained
                                   by `digest`, cleared once the agent has read.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import httpx

from clawlite.config import MEMORY_DIR

SUBS_PATH = Path.home() / ".clawlite" / "feeds.json"
INBOX_DIR = MEMORY_DIR / "feeds"
MAX_ITEMS_PER_FETCH = 100
MAX_SUMMARY_CHARS = 500
# Reddit and some other hosts block feedparser's default UA. A browser-like
# UA is the most reliable way to get past aggressive bot filters.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class FeedFetchError(Exception):
    """Raised when a feed URL can't be fetched or returns non-feed content."""


def _fetch_curl(url: str) -> bytes:
    """Fetch via curl subprocess — bypasses TLS fingerprinting blocks."""
    try:
        result = subprocess.run(
            [
                "curl", "-sS", "-L",
                "-A", USER_AGENT,
                "-H", "Accept: application/atom+xml, application/rss+xml, application/xml, */*",
                "--max-time", "15",
                url,
            ],
            capture_output=True,
            timeout=20,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise FeedFetchError(f"curl fallback failed: {e}") from e

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        raise FeedFetchError(f"curl exited {result.returncode}: {stderr}")

    return result.stdout


def _parse(url: str):
    """
    Fetch via httpx first. If the host blocks it (403, HTML anti-bot page),
    retry with curl whose TLS fingerprint passes most bot detectors.

    Raises FeedFetchError when both methods fail.
    """
    # --- attempt 1: httpx ---
    use_curl = False
    try:
        response = httpx.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/atom+xml, application/rss+xml, application/xml, */*",
            },
            follow_redirects=True,
            timeout=15.0,
        )
        ctype = response.headers.get("content-type", "").lower()
        blocked = (
            response.status_code == 403
            or ("html" in ctype and "xml" not in ctype)
        )
        if blocked:
            use_curl = True
        elif response.status_code != 200:
            raise FeedFetchError(
                f"HTTP {response.status_code} from {url}"
            )
    except httpx.HTTPError:
        use_curl = True

    if use_curl:
        raw = _fetch_curl(url)
        return feedparser.parse(raw)

    return feedparser.parse(response.content)


# ---------- subscriptions ----------

def _load() -> Dict[str, Any]:
    if not SUBS_PATH.exists():
        return {"feeds": []}
    try:
        return json.loads(SUBS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"feeds": []}


def _save(data: Dict[str, Any]) -> None:
    SUBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _slug(url: str, title: Optional[str]) -> str:
    base = title or urlparse(url).netloc or "feed"
    s = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")
    return s or "feed"


def _unique_slug(candidate: str, taken: set) -> str:
    if candidate not in taken:
        return candidate
    i = 2
    while f"{candidate}_{i}" in taken:
        i += 1
    return f"{candidate}_{i}"


def list_subscriptions() -> List[Dict[str, Any]]:
    return _load().get("feeds", [])


def add_subscription(url: str) -> Dict[str, Any]:
    subs = _load()
    feeds = subs.setdefault("feeds", [])
    for f in feeds:
        if f["url"] == url:
            return {"status": "exists", "feed": f}

    # Fetch once to discover the feed's title. Discovery failure is
    # non-fatal — we still register the subscription so `fetch` can retry
    # later, and surface a warning to the caller.
    title = None
    discovery_error = None
    try:
        parsed = _parse(url)
        if parsed.entries:
            title = parsed.feed.get("title")
    except FeedFetchError as e:
        discovery_error = str(e)

    slug = _unique_slug(_slug(url, title), {f.get("slug") for f in feeds})
    feed = {
        "url": url,
        "slug": slug,
        "title": title or url,
        "last_seen_guid": None,
    }
    feeds.append(feed)
    _save(subs)
    return {"status": "added", "feed": feed, "warning": discovery_error}


def remove_subscription(url: str) -> Dict[str, Any]:
    subs = _load()
    feeds = subs.get("feeds", [])
    remaining = [f for f in feeds if f["url"] != url]
    if len(remaining) == len(feeds):
        return {"status": "not_found"}
    subs["feeds"] = remaining
    _save(subs)
    return {"status": "removed"}


# ---------- fetching ----------

def _guid(entry: Dict[str, Any]) -> str:
    return (
        entry.get("id")
        or entry.get("guid")
        or entry.get("link")
        or entry.get("title", "")
    )


def _truncate(text: str, n: int) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"


def _strip_html(text: str) -> str:
    """Light HTML tag strip — feed summaries often contain markup."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _fetch_feed(feed: Dict[str, Any]) -> int:
    """
    Append new items for `feed` to its JSONL inbox file. Mutates `feed`
    (updates `last_seen_guid`). Returns the number of new items written.
    """
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = INBOX_DIR / f"{feed['slug']}.jsonl"

    last_seen = feed.get("last_seen_guid")
    parsed = _parse(feed["url"])

    new_items = []
    new_top_guid = None
    for entry in parsed.entries[:MAX_ITEMS_PER_FETCH]:
        guid = _guid(entry)
        if guid == last_seen:
            break
        if new_top_guid is None:
            new_top_guid = guid
        new_items.append({
            "title": entry.get("title", "(untitled)"),
            "link": entry.get("link", ""),
            "published": entry.get("published") or entry.get("updated") or "",
            "summary": _truncate(_strip_html(entry.get("summary", "")), MAX_SUMMARY_CHARS),
            "feed_title": feed.get("title", feed["url"]),
        })

    if new_items:
        with jsonl_path.open("a", encoding="utf-8") as fp:
            for item in new_items:
                fp.write(json.dumps(item, ensure_ascii=False) + "\n")
        feed["last_seen_guid"] = new_top_guid

    return len(new_items)


def fetch_all() -> Dict[str, Any]:
    """Fetch every subscribed feed. Returns {slug: int | str-error}."""
    subs = _load()
    results: Dict[str, Any] = {}
    for feed in subs.get("feeds", []):
        try:
            results[feed["slug"]] = _fetch_feed(feed)
        except Exception as e:
            results[feed["slug"]] = f"error: {e}"
    _save(subs)  # persist updated last_seen_guid
    return results


# ---------- inbox management ----------

def inbox_files() -> List[Path]:
    if not INBOX_DIR.exists():
        return []
    return sorted(p for p in INBOX_DIR.glob("*.jsonl") if p.stat().st_size > 0)


def clear_inbox() -> List[Path]:
    """Delete all .jsonl files in the inbox. Returns the list of files removed."""
    files = inbox_files()
    for f in files:
        f.unlink()
    return files
