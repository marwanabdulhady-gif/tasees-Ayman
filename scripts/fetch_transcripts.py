"""Download transcripts for every episode in the playlists listed in
transcripts/playlists.json, one folder per playlist.

Order of attempts per video:
  1. ytfetcher (youtube-transcript-api) in the configured languages.
  2. Fallback: YouTube captions (manual, then auto-generated) via yt-dlp,
     trying several player clients (android/ios/tv/default). Datacenter IPs
     (GitHub Actions runners) are frequently bot-blocked on some clients but
     not others, so the first client that yields captions wins and is then
     preferred for the remaining videos.

Episodes that already have a file are skipped, so the script can be re-run
to resume. Per-video failure reasons are written to transcripts/_failures.md
(committed by the workflow) so they can be inspected without Actions logs.
Set YT_COOKIES_FILE to a Netscape cookies.txt path if YouTube asks to
"confirm you're not a bot".
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

CLIENTS = ["android", "ios", "tv", "default"]
client_success: Counter = Counter()
videos_attempted = 0
FAILURES: dict[str, list[str]] = {}


def note_failure(key: str, msg: str) -> None:
    FAILURES.setdefault(key, []).append(re.sub(r"\s+", " ", str(msg))[:300])


def ordered_clients() -> list[str]:
    return sorted(CLIENTS, key=lambda c: -client_success[c])


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
    """Fallback: download caption files (manual first, then auto) with yt-dlp."""
    global videos_attempted
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
    global videos_attempted
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
        videos_attempted += 1
        segments, source = transcripts.get(ep["id"]), "ytfetcher (youtube-transcript-api)"
        if not segments:
            clients = ordered_clients()
            # Circuit breaker: if nothing ever worked, don't burn the full
            # client matrix on every remaining video — probe two clients only.
            if sum(client_success.values()) == 0 and videos_attempted > 10:
                clients = ["android", "default"]
            for client in clients:
                segments = fetch_captions(ep["id"], languages, client)
                if segments:
                    source = f"YouTube captions (yt-dlp, client={client})"
                    break
                time.sleep(0.3)
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
