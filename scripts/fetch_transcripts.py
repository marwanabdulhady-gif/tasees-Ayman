"""Download transcripts for every episode in the playlists listed in
transcripts/playlists.json, one folder per playlist.

Order of attempts per video:
  1. ytfetcher (youtube-transcript-api) in the configured languages.
  2. yt-dlp captions (manual, then auto-generated). All clients are probed
     only when cookies are available; without cookies a single quick probe
     is made because GitHub runner IPs are currently bot-blocked ("Sign in
     to confirm you're not a bot") on every player client.
  3. Invidious instances (public YouTube frontends) — captions API.
  4. Piped instances — streams API subtitles.

Episodes that already have a file are skipped, so the script can be re-run
to resume. Per-video failure reasons are written to transcripts/_failures.md
(committed by the workflow) so they can be inspected without Actions logs.
Set YT_COOKIES_FILE to a Netscape cookies.txt path (or the YT_COOKIES repo
secret via the workflow) if YouTube asks to "confirm you're not a bot".
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp
from ytfetcher import YTFetcher
from ytfetcher.config import FetchOptions

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "transcripts"
CONFIG_PATH = TRANSCRIPTS_DIR / "playlists.json"
FAILURES_PATH = TRANSCRIPTS_DIR / "_failures.md"
COOKIES_FILE = os.environ.get("YT_COOKIES_FILE")
if COOKIES_FILE and not Path(COOKIES_FILE).is_file():
    COOKIES_FILE = None

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yewtu.be",
    "https://invidious.f5.si",
    "https://iv.ggtyler.dev",
    "https://invidious.materialio.us",
    "https://inv.tux.pizza",
]
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.private.coffee",
    "https://pipedapi.adminforge.de",
    "https://api.piped.yt",
    "https://pipedapi.drgns.space",
]
INSTANCE_FAIL_LIMIT = 3  # skip an instance for the rest of the run after N failures
instance_fails: Counter = Counter()

CLIENTS = ["android", "ios", "tv", "default"]
client_success: Counter = Counter()
FAILURES: dict[str, list[str]] = {}


def note_failure(key: str, msg: str) -> None:
    FAILURES.setdefault(key, []).append(re.sub(r"\s+", " ", str(msg))[:300])


def ordered_clients() -> list[str]:
    return sorted(CLIENTS, key=lambda c: -client_success[c])


def _host(url: str) -> str:
    return urlparse(url).netloc


def _is_arabic(*texts: str) -> bool:
    joined = " ".join(t.lower() for t in texts if t)
    return any(h in joined for h in ("ar", "arabic", "عرب"))


class CollectingLogger:
    """yt-dlp logger that keeps the last warnings/errors for diagnostics."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def debug(self, msg) -> None:
        pass

    def info(self, msg) -> None:
        pass

    def warning(self, msg) -> None:
        self.lines.append(str(msg)[:200])

    def error(self, msg) -> None:
        self.lines.append(str(msg)[:200])


def ydl_opts(logger=None, client: str = "default", **extra) -> dict:
    opts = {"quiet": True, "no_warnings": True, "ignoreerrors": True}
    if COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
    if client != "default":
        opts["extractor_args"] = {"youtube": {"player_client": [client]}}
    if logger is not None:
        opts["logger"] = logger
    opts.update(extra)
    return opts


def list_playlist(playlist_id: str) -> tuple[str, list[dict]]:
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    with yt_dlp.YoutubeDL(ydl_opts(extract_flat="in_playlist")) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError(f"could not list playlist {playlist_id}")
    entries = [e for e in info.get("entries") or [] if e and e.get("id")]
    return info.get("title") or playlist_id, entries


def safe_filename(name: str, limit: int = 90) -> str:
    name = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:limit].rstrip(" .") or "untitled"


def fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def segments_to_paragraphs(segments: list[tuple[float, str]], every: int = 60) -> list[tuple[float, str]]:
    """Group caption segments into ~1-minute paragraphs, each with its start time."""
    paragraphs: list[tuple[float, str]] = []
    start, buf = None, []
    for t, text in segments:
        if start is None:
            start = t
        buf.append(text)
        if t - start >= every:
            paragraphs.append((start, " ".join(buf)))
            start, buf = None, []
    if buf:
        paragraphs.append((start or 0.0, " ".join(buf)))
    return paragraphs


VTT_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})\.(\d{3})\s+-->")


def parse_vtt(vtt: str) -> list[tuple[float, str]]:
    """Parse WebVTT into (start, text) segments, removing the line repetition
    that YouTube's auto-generated "rolling" captions produce."""
    segments: list[tuple[float, str]] = []
    seen_lines: list[str] = []
    for block in re.split(r"\n\s*\n", vtt.replace("\r\n", "\n")):
        lines = block.strip().split("\n")
        idx = next((i for i, ln in enumerate(lines) if VTT_TIME.search(ln)), None)
        if idx is None:
            continue
        h, m, s, ms = map(int, VTT_TIME.search(lines[idx]).groups())
        start = h * 3600 + m * 60 + s + ms / 1000
        new_text = []
        for ln in lines[idx + 1:]:
            ln = re.sub(r"<[^>]+>", "", ln).strip()
            if not ln or ln in seen_lines[-3:]:
                continue
            seen_lines.append(ln)
            new_text.append(ln)
        if new_text:
            segments.append((start, " ".join(new_text)))
    return segments


def fetch_with_ytfetcher(video_ids: list[str], languages: list[str]) -> dict[str, list[tuple[float, str]]]:
    if not video_ids:
        return {}
    options = FetchOptions(languages=languages, cache_enabled=False, max_concurrent_requests=3)
    fetcher = YTFetcher.from_video_ids(video_ids, options=options)
    try:
        results = fetcher.fetch_transcripts()
    except Exception as exc:  # noqa: BLE001 - fall back to captions on any failure
        print(f"  ytfetcher failed: {exc}", file=sys.stderr)
        for vid in video_ids:
            note_failure(vid, f"ytfetcher exception: {exc}")
        return {}
    for failed in fetcher.get_failed_transcripts():
        print(f"  ytfetcher: no transcript for {failed.video_id} ({failed.reason})", file=sys.stderr)
        note_failure(failed.video_id, f"ytfetcher: {failed.reason}")
    return {
        r.video_id: [(t.start, t.text.replace("\n", " ")) for t in r.transcripts]
        for r in results
        if r.transcripts
    }


def fetch_captions(video_id: str, languages: list[str], client: str = "default") -> list[tuple[float, str]] | None:
    """Download caption files (manual first, then auto) with yt-dlp."""
    logger = CollectingLogger()
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmp:
        for auto in (False, True):
            opts = ydl_opts(
                logger=logger,
                client=client,
                skip_download=True,
                writesubtitles=not auto,
                writeautomaticsub=auto,
                subtitleslangs=languages,
                subtitlesformat="vtt",
                outtmpl=os.path.join(tmp, "%(id)s.%(ext)s"),
            )
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            except Exception as exc:  # noqa: BLE001
                note_failure(video_id, f"yt-dlp[{client},{'auto' if auto else 'manual'}] exception: {exc}")
                continue
            files = sorted(Path(tmp).glob(f"{video_id}*.vtt"))
            if files:
                segments = parse_vtt(files[0].read_text(encoding="utf-8"))
                if segments:
                    client_success[client] += 1
                    return segments
    tail = "; ".join(logger.lines[-2:])
    note_failure(video_id, f"yt-dlp[{client}] no usable captions" + (f" — {tail}" if tail else ""))
    return None


def fetch_via_invidious(video_id: str) -> tuple[list[tuple[float, str]] | None, str | None]:
    """Captions through public Invidious instances."""
    for inst in INVIDIOUS_INSTANCES:
        if instance_fails[inst] >= INSTANCE_FAIL_LIMIT:
            continue
        host = _host(inst)
        try:
            r = requests.get(f"{inst}/api/v1/captions/{video_id}",
                             timeout=20, headers={"User-Agent": UA})
            r.raise_for_status()
            caps = r.json()
            if not isinstance(caps, list) or not caps:
                raise RuntimeError(f"unexpected captions payload: {str(caps)[:120]}")
            pick = next((c for c in caps
                         if _is_arabic(c.get("languageCode", ""), c.get("label", ""))), caps[0])
            url = pick.get("url") or ""
            if url.startswith("/"):
                url = inst + url
            rv = requests.get(url, timeout=30, headers={"User-Agent": UA})
            rv.raise_for_status()
            segments = parse_vtt(rv.text)
            if segments:
                print(f"  [invidious] {video_id} via {host} ({pick.get('label')})")
                return segments, host
            raise RuntimeError("VTT parsed to zero segments")
        except Exception as exc:  # noqa: BLE001
            instance_fails[inst] += 1
            note_failure(video_id, f"invidious[{host}]: {exc}")
    return None, None


def fetch_via_piped(video_id: str) -> tuple[list[tuple[float, str]] | None, str | None]:
    """Captions through public Piped instances."""
    for inst in PIPED_INSTANCES:
        if instance_fails[inst] >= INSTANCE_FAIL_LIMIT:
            continue
        host = _host(inst)
        try:
            r = requests.get(f"{inst}/streams/{video_id}",
                             timeout=20, headers={"User-Agent": UA})
            r.raise_for_status()
            subs = (r.json() or {}).get("subtitles") or []
            if not subs:
                raise RuntimeError("no subtitles in streams payload")
            pick = next((s for s in subs if _is_arabic(s.get("name", ""), s.get("code", ""))), subs[0])
            rv = requests.get(pick["url"], timeout=30, headers={"User-Agent": UA})
            rv.raise_for_status()
            segments = parse_vtt(rv.text)
            if segments:
                print(f"  [piped] {video_id} via {host} ({pick.get('name')})")
                return segments, host
            raise RuntimeError("VTT parsed to zero segments")
        except Exception as exc:  # noqa: BLE001
            instance_fails[inst] += 1
            note_failure(video_id, f"piped[{host}]: {exc}")
    return None, None


def write_episode(path: Path, number: int, title: str, video_id: str, source: str,
                  segments: list[tuple[float, str]]) -> None:
    url = f"https://www.youtube.com/watch?v={video_id}"
    lines = [
        f"# {title}",
        "",
        f"- الحلقة: {number}",
        f"- الرابط: {url}",
        f"- المصدر: {source}",
        "",
        "---",
        "",
    ]
    for start, text in segments_to_paragraphs(segments):
        lines.append(f"**[{fmt_time(start)}]({url}&t={int(start)}s)** {text}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def process_playlist(pl: dict, languages: list[str], limit: int = 0) -> list[str]:
    folder = TRANSCRIPTS_DIR / pl["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    yt_title, entries = list_playlist(pl["playlist_id"])
    print(f"\n== {pl['folder']}: {yt_title} ({len(entries)} videos)")

    episodes = []
    for n, e in enumerate(entries, 1):
        title = e.get("title") or e["id"]
        filename = f"{n:02d} - {safe_filename(title)}.md"
        existing = next(folder.glob(f"{n:02d} - *.md"), None)
        episodes.append({"n": n, "id": e["id"], "title": title,
                         "file": existing.name if existing else filename, "done": existing is not None})

    pending = [ep for ep in episodes if not ep["done"]]
    if limit > 0:
        pending = pending[:limit]
    transcripts = fetch_with_ytfetcher([ep["id"] for ep in pending], languages)

    missing = []
    for ep in pending:
        segments, source = transcripts.get(ep["id"]), "ytfetcher (youtube-transcript-api)"
        if not segments:
            # With cookies, probe every client (best success rate). Without,
            # a single canary probe is enough — runner IPs are bot-blocked.
            clients = ordered_clients() if COOKIES_FILE else ["default"]
            for client in clients:
                segments = fetch_captions(ep["id"], languages, client)
                if segments:
                    source = f"YouTube captions (yt-dlp, client={client})"
                    break
                time.sleep(0.2)
        if not segments:
            segments, inst = fetch_via_invidious(ep["id"])
            if segments:
                source = f"Invidious captions ({inst})"
        if not segments:
            segments, inst = fetch_via_piped(ep["id"])
            if segments:
                source = f"Piped captions ({inst})"
        if not segments:
            print(f"  [missing] {ep['n']:02d} {ep['title']}")
            missing.append(ep["id"])
            continue
        write_episode(folder / ep["file"], ep["n"], ep["title"], ep["id"], source, segments)
        ep["done"] = True
        print(f"  [ok] {ep['n']:02d} {ep['title']} ({source})")

    index = [
        f"# {pl['title']}",
        "",
        f"قائمة التشغيل: https://www.youtube.com/playlist?list={pl['playlist_id']}",
        "",
        "| # | الحلقة | النص |",
        "|---|---|---|",
    ]
    for ep in episodes:
        link = f"https://www.youtube.com/watch?v={ep['id']}"
        status = f"[النص](<{ep['file']}>)" if ep["done"] else "غير متوفر"
        index.append(f"| {ep['n']} | [{ep['title']}]({link}) | {status} |")
    (folder / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return missing


def write_failures() -> None:
    if not FAILURES:
        if FAILURES_PATH.exists():
            FAILURES_PATH.unlink()
        return
    lines = ["# أسباب فشل الجلب (آخر تشغيل)", "",
             "> يُحدَّث هذا الملف تلقائيًا عند كل تشغيل للـ workflow.", ""]
    for vid, msgs in FAILURES.items():
        lines.append(f"## {vid}")
        lines.extend(f"- {m}" for m in msgs[:12])
        lines.append("")
    FAILURES_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", help="folder names to process (default: all)")
    parser.add_argument("--limit", type=int, default=0, help="max episodes per playlist (0 = all)")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    languages = config.get("languages") or ["ar"]
    all_missing = {}
    ok_count = 0
    for pl in config["playlists"]:
        if args.only and pl["folder"] not in args.only:
            continue
        try:
            missing = process_playlist(pl, languages, limit=args.limit)
            folder = TRANSCRIPTS_DIR / pl["folder"]
            ok_count += len(list(folder.glob("[0-9][0-9] - *.md")))
        except Exception as exc:  # noqa: BLE001 - keep going with other playlists
            print(f"  ERROR in {pl['folder']}: {exc}", file=sys.stderr)
            note_failure(pl["folder"], f"playlist error: {exc}")
            missing = ["<playlist failed>"]
        if missing:
            all_missing[pl["folder"]] = missing

    write_failures()
    print(f"\nDone. {ok_count} episode file(s) on disk.", flush=True)
    if all_missing:
        print("Episodes without transcripts:", json.dumps(all_missing, indent=2))
        print("See transcripts/_failures.md for per-video reasons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
