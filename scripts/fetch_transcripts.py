"""Download the Arabic transcripts of every episode in transcripts/playlists.json.

One folder per playlist, one Markdown file per episode. Episodes are numbered by
their lecture number (المحاضرة الأولى، الثانية …) when the playlist sets
"sort_by_lecture": true, otherwise by playlist order. Each ~1-minute paragraph
is timestamped and links back to the video at that second.

Per video the script tries:
  1. ytfetcher (youtube-transcript-api) — the fast path.
  2. YouTube captions via yt-dlp — manual track first, then auto-generated.

Episodes that already have a file are skipped, so simply re-running the script
resumes where it stopped. If YouTube answers "Sign in to confirm you're not a
bot", re-run with --cookies-from-browser chrome (or firefox/edge/safari/brave)
and yt-dlp reuses your browser's session. Progress and failures are written to
transcripts/_status.md and transcripts/_last_run.log.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp
from ytfetcher import YTFetcher
from ytfetcher.config import FetchOptions

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = Path(os.environ.get("TRANSCRIPTS_DIR") or ROOT / "transcripts")
CONFIG_PATH = Path(os.environ.get("PLAYLISTS_JSON") or TRANSCRIPTS_DIR / "playlists.json")
STATUS_PATH = TRANSCRIPTS_DIR / "_status.md"
OVERVIEW_PATH = TRANSCRIPTS_DIR / "README.md"
LOG_PATH = TRANSCRIPTS_DIR / "_last_run.log"

MIN_EPISODE_BYTES = 200  # smaller than this means an interrupted/empty file

COOKIES_FILE = os.environ.get("YT_COOKIES_FILE")
if COOKIES_FILE and not Path(COOKIES_FILE).is_file():
    COOKIES_FILE = None


# --------------------------------------------------------------------------- #
# console + logging
# --------------------------------------------------------------------------- #
class _Tee:
    """Mirror everything printed to the console into the run log."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, text):
        for stream in self._streams:
            try:
                stream.write(text)
            except Exception:  # noqa: BLE001 - a broken console must not stop the run
                pass

    def flush(self):
        for stream in self._streams:
            try:
                stream.flush()
            except Exception:  # noqa: BLE001
                pass

    def isatty(self):
        return False


def setup_console(log_path: Path | None) -> None:
    """UTF-8 console (Windows cp1256/cp437 would otherwise crash on Arabic) + log file."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - Python < 3.7 or an exotic stream
            pass
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(log_path, "w", encoding="utf-8", errors="replace")  # noqa: SIM115
    sys.stdout = _Tee(sys.__stdout__, handle)
    sys.stderr = _Tee(sys.__stderr__, handle)


def log(*parts: object) -> None:
    print(*parts, flush=True)


def short(exc: BaseException, limit: int = 160) -> str:
    text = " ".join(str(exc).split())
    return text[:limit] + ("…" if len(text) > limit else "")


# --------------------------------------------------------------------------- #
# yt-dlp helpers
# --------------------------------------------------------------------------- #
class _YdlLogger:
    """Keep yt-dlp's error text (e.g. YouTube's bot check) instead of printing it."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def debug(self, message):
        pass

    def info(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        text = " ".join(str(message).split())
        if text:
            self.errors.append(text)

    def last_error(self) -> str | None:
        return self.errors[-1] if self.errors else None


def ydl_opts(browser: str | None = None, **extra) -> dict:
    # lang=ar keeps the original Arabic titles instead of YouTube's auto-translations.
    opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "retries": 3,
        "extractor_retries": 2,
        "socket_timeout": 30,
        "extractor_args": {"youtube": {"lang": ["ar"]}},
    }
    if COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
    elif browser:
        opts["cookiesfrombrowser"] = (browser,)
    opts.update(extra)
    return opts


def with_retries(func, *, what: str, tries: int = 3, base_delay: float = 5.0):
    """Run func(), retrying transient network/YouTube errors with backoff."""
    for attempt in range(1, tries + 1):
        try:
            return func()
        except Exception as exc:
            if attempt == tries:
                raise
            wait = base_delay * attempt + random.uniform(0, 2)
            log(f"    {what} failed ({short(exc)}); retry {attempt}/{tries - 1} in {wait:.0f}s")
            time.sleep(wait)
    raise AssertionError("unreachable")


def list_playlist(playlist_id: str) -> tuple[str, list[dict]]:
    def run():
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
        with yt_dlp.YoutubeDL(ydl_opts(extract_flat="in_playlist")) as ydl:
            return ydl.extract_info(url, download=False)

    info = with_retries(run, what=f"listing playlist {playlist_id}")
    if not info:
        raise RuntimeError(f"could not list playlist {playlist_id}")
    entries = [e for e in info.get("entries") or [] if e and e.get("id")]
    if not entries:
        raise RuntimeError(f"playlist {playlist_id} came back empty")
    return info.get("title") or playlist_id, entries


# --------------------------------------------------------------------------- #
# episode numbering
# --------------------------------------------------------------------------- #
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

ORDINALS = {
    "الأولى": 1, "الاولى": 1, "الأولي": 1, "الاولي": 1, "الأول": 1, "الاول": 1, "أولى": 1,
    "الثانية": 2, "الثانيه": 2, "الثاني": 2, "الثانیة": 2,
    "الثالثة": 3, "الثالثه": 3, "الثالث": 3,
    "الرابعة": 4, "الرابعه": 4, "الرابع": 4,
    "الخامسة": 5, "الخامسه": 5, "الخامس": 5,
    "السادسة": 6, "السادسه": 6, "السادس": 6,
    "السابعة": 7, "السابعه": 7, "السابع": 7,
    "الثامنة": 8, "الثامنه": 8, "الثامن": 8,
    "التاسعة": 9, "التاسعه": 9, "التاسع": 9,
    "العاشرة": 10, "العاشره": 10, "العاشر": 10,
    "الحادية": 11, "الحاديه": 11, "الحادي": 11,
    "الثانية عشرة": 12, "الثانية عشر": 12,
    "one": 1, "first": 1, "two": 2, "second": 2, "three": 3, "third": 3,
    "four": 4, "fourth": 4, "five": 5, "fifth": 5, "six": 6, "sixth": 6,
    "seven": 7, "seventh": 7, "eight": 8, "eighth": 8, "nine": 9, "ninth": 9,
    "ten": 10, "tenth": 10,
}

LECTURE_RE = re.compile(r"(?:المحاضرة|المحاضره|lecture)\s*[:\-–]?\s*([^\s,\-–|]+)", re.IGNORECASE)


def lecture_number(title: str) -> int | None:
    """Lecture number from a title like "… المحاضرة السادسة" or "Lecture Five"."""
    cleaned = (title or "").translate(ARABIC_DIGITS)
    match = LECTURE_RE.search(cleaned)
    if match:
        word = re.sub(r"^[\s.,،؛:]+|[\s.,،؛:]+$", "", match.group(1).lower())
        if word.isdigit():
            return int(word)
        if word in ORDINALS:
            return ORDINALS[word]
    match = re.match(r"\s*(\d{1,3})\s", cleaned)
    return int(match.group(1)) if match else None


def lecture_numbers(entries: list[dict]) -> list[int] | None:
    """Lecture numbers for every entry, or None if they are missing or ambiguous."""
    numbers = [lecture_number(entry.get("title") or "") for entry in entries]
    if None in numbers:
        unreadable = [e.get("title", "?") for e, n in zip(entries, numbers) if n is None]
        log(f"  lecture number missing in {len(unreadable)} title(s); numbering by playlist order")
        if unreadable:
            log(f"    e.g. {unreadable[0][:80]}")
        return None
    if len(set(numbers)) != len(numbers):
        log("  duplicate lecture numbers; numbering by playlist order")
        return None
    return [int(n) for n in numbers]


def order_by_lecture(entries: list[dict]) -> list[dict]:
    """Sort by lecture number; keep playlist order if any title can't be parsed."""
    numbers = lecture_numbers(entries)
    if numbers is None:
        return entries
    return [entry for _, entry in sorted(zip(numbers, entries), key=lambda pair: pair[0])]


# --------------------------------------------------------------------------- #
# formatting
# --------------------------------------------------------------------------- #
def safe_filename(name: str, limit: int = 90) -> str:
    name = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", name or "")
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:limit].rstrip(" .") or "untitled"


def fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def segments_to_paragraphs(segments: list[tuple[float, str]], every: int = 60) -> list[tuple[float, str]]:
    """Group caption segments into ~1-minute paragraphs, each with its start time."""
    paragraphs: list[tuple[float, str]] = []
    start: float | None = None
    buffer: list[str] = []
    for timestamp, text in segments:
        if start is None:
            start = timestamp
        buffer.append(text)
        if timestamp - start >= every:
            paragraphs.append((start, " ".join(buffer)))
            start, buffer = None, []
    if buffer:
        paragraphs.append((start if start is not None else 0.0, " ".join(buffer)))
    return paragraphs


VTT_TIMING = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->"
)
TAG_RE = re.compile(r"<[^>]*>")


def parse_vtt(vtt: str) -> list[tuple[float, str]]:
    """Parse WebVTT into (start, text) segments.

    Handles both plain cue files and YouTube's auto-generated "rolling" captions,
    where every cue repeats the last line or two of the previous cue.
    """
    segments: list[tuple[float, str]] = []
    emitted: list[str] = []  # last few lines, to drop rolling-caption repeats
    for block in re.split(r"\r?\n\s*\r?\n", vtt.replace("\ufeff", "")):
        lines = [line.strip() for line in block.splitlines()]
        timing = None
        start = None
        for index, line in enumerate(lines):
            match = VTT_TIMING.search(line)
            if match:
                hours = int(match.group(1) or 0)
                start = hours * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000
                timing = index
                break
        if timing is None or start is None:
            continue
        fresh: list[str] = []
        for line in lines[timing + 1:]:
            line = TAG_RE.sub("", line).strip()
            if not line or line in emitted[-3:] or line in fresh:
                continue
            fresh.append(line)
        if fresh:
            emitted = (emitted + fresh)[-6:]
            segments.append((start, " ".join(fresh)))
    return segments


# --------------------------------------------------------------------------- #
# fetching
# --------------------------------------------------------------------------- #
def fetch_with_ytfetcher(video_ids: list[str], languages: list[str]):
    """Return ({video_id: segments}, {video_id: failure reason})."""
    if not video_ids:
        return {}, {}
    options = FetchOptions(
        languages=languages,
        cache_enabled=False,          # always fetch fresh; resume is file-based
        max_concurrent_requests=3,    # gentle on a home connection
        with_recovery=True,
        recovery_delay=10,
    )
    fetcher = YTFetcher.from_video_ids(video_ids, options=options)
    try:
        results = fetcher.fetch_transcripts()
    except Exception as exc:  # noqa: BLE001 - fall back to captions on any failure
        log(f"  ytfetcher failed: {short(exc)}")
        return {}, {vid: f"ytfetcher: {short(exc)}" for vid in video_ids}
    reasons = {}
    try:
        for failure in fetcher.get_failed_transcripts():
            reasons[failure.video_id] = f"ytfetcher: {short(failure.reason)}"
    except Exception:  # noqa: BLE001
        pass
    transcripts = {
        result.video_id: [(float(t.start), " ".join(str(t.text).split())) for t in result.transcripts]
        for result in results
        if result.transcripts
    }
    return transcripts, reasons


def _download_captions(video_id: str, auto: bool, languages: list[str], browser: str | None):
    """Download one caption track set. Returns (segments|None, error|None)."""
    logger = _YdlLogger()
    with tempfile.TemporaryDirectory() as tmp:
        opts = ydl_opts(
            browser,
            logger=logger,
            skip_download=True,
            writesubtitles=not auto,
            writeautomaticsub=auto,
            subtitleslangs=list(languages),
            subtitlesformat="vtt",
            outtmpl=str(Path(tmp) / "%(id)s.%(ext)s"),
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        files = sorted(Path(tmp).glob(f"{video_id}*.vtt"))
        if not files:
            return None, logger.last_error() or "no caption files"
        # prefer an Arabic track if yt-dlp downloaded several
        files.sort(key=lambda path: (0 if ".ar" in path.name else 1, path.name))
        segments = parse_vtt(files[0].read_text(encoding="utf-8", errors="replace"))
        return (segments or None), (None if segments else f"empty caption file {files[0].name}")


def fetch_captions(video_id: str, languages: list[str], browser: str | None = None):
    """Fallback: YouTube captions via yt-dlp (manual first, then auto-generated).

    Tries the configured languages, then any Arabic track, then whatever exists.
    Returns (segments|None, human readable reason when it failed).
    """
    plans = [
        (False, list(languages)),
        (True, list(languages)),
        (True, ["ar.*"]),
        (True, ["all"]),
    ]
    errors: list[str] = []
    for auto, langs in plans:
        label = "auto" if auto else "manual"
        try:
            segments, error = _download_captions(video_id, auto, langs, browser)
        except Exception as exc:  # noqa: BLE001 - try the next plan
            errors.append(f"{label} {','.join(langs)}: {short(exc)}")
            continue
        if segments:
            return segments, None
        errors.append(f"{label} {','.join(langs)}: {error}")
    bot_check = next((e for e in errors if "not a bot" in e or "Sign in" in e), None)
    return None, bot_check or (errors[-1] if errors else "no captions")


# --------------------------------------------------------------------------- #
# writing
# --------------------------------------------------------------------------- #
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


def write_playlist_index(folder: Path, pl: dict, rows: list[dict]) -> None:
    done = sum(1 for row in rows if row["status"] == "ok")
    lines = [
        f"# {pl['title']}",
        "",
        f"قائمة التشغيل: https://www.youtube.com/playlist?list={pl['playlist_id']}",
        "",
        f"التفريغات الجاهزة: {done} من {len(rows)}",
        "",
        "| # | الحلقة | النص |",
        "|---|---|---|",
    ]
    for row in rows:
        link = f"https://www.youtube.com/watch?v={row['id']}"
        status = f"[النص](<{row['file']}>)" if row["status"] == "ok" else "غير متوفر"
        title = row["title"].replace("|", "\\|")
        lines.append(f"| {row['n']} | [{title}]({link}) | {status} |")
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_overview(results: list[tuple[dict, list[dict]]]) -> None:
    lines = [
        "# تفريغات محاضرات م. أيمن عبدالرحيم",
        "",
        f"آخر تحديث: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| المجلد | قائمة التشغيل | جاهز | الإجمالي |",
        "|---|---|---|---|",
    ]
    for pl, rows in results:
        done = sum(1 for row in rows if row["status"] == "ok")
        lines.append(
            f"| [{pl['title']}](<{pl['folder']}/README.md>) | "
            f"[YouTube](https://www.youtube.com/playlist?list={pl['playlist_id']}) | "
            f"{done} | {len(rows)} |"
        )
    lines += ["", "حالة آخر تشغيل والأخطاء: [_status.md](_status.md)", ""]
    OVERVIEW_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_status(results: list[tuple[dict, list[dict]]], languages: list[str]) -> int:
    total = sum(len(rows) for _, rows in results)
    done = sum(1 for _, rows in results for row in rows if row["status"] == "ok")
    missing = [(pl, row) for pl, rows in results for row in rows if row["status"] == "missing"]

    lines = [
        "# حالة جلب التفريغات",
        "",
        f"- آخر تشغيل: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- المجموعات المعالَجة: {', '.join(pl['folder'] for pl, _ in results)}",
        f"- الحلقات الجاهزة: {done} من {total}",
        f"- اللغات المطلوبة: {', '.join(languages)}",
        "",
    ]
    if missing:
        lines += [
            "## حلقات بدون تفريغ",
            "",
            "| المجلد | # | الحلقة | السبب |",
            "|---|---|---|---|",
        ]
        for pl, row in missing:
            reason = (row.get("reason") or "").replace("|", "\\|")[:220]
            title = row["title"].replace("|", "\\|")[:80]
            lines.append(f"| {pl['folder']} | {row['n']} | [{title}](https://www.youtube.com/watch?v={row['id']}) | {reason} |")
        lines += [
            "",
            ("أعد تشغيل السكربت لإكمال الناقص. إذا كان السبب «Sign in to confirm you're not a bot» فشغّله مع "
             "`--cookies-from-browser chrome` (أو firefox / edge / safari)."),
            "",
        ]
    else:
        lines += ["كل الحلقات المطلوبة جاهزة ✅", ""]

    STATUS_PATH.write_text("\n".join(lines), encoding="utf-8")
    return len(missing)


# --------------------------------------------------------------------------- #
# main flow
# --------------------------------------------------------------------------- #
def existing_episode(folder: Path, number: int) -> Path | None:
    for path in sorted(folder.glob(f"{number:02d} - *.md")):
        try:
            if path.stat().st_size > MIN_EPISODE_BYTES:
                return path
        except OSError:
            continue
    return None


def process_playlist(pl: dict, languages: list[str], args) -> list[dict]:
    folder = TRANSCRIPTS_DIR / pl["folder"]
    folder.mkdir(parents=True, exist_ok=True)

    yt_title, entries = list_playlist(pl["playlist_id"])
    numbers = None
    if pl.get("sort_by_lecture"):
        numbers = lecture_numbers(entries)
        if numbers is not None:
            entries = [entry for _, entry in sorted(zip(numbers, entries), key=lambda pair: pair[0])]
            numbers = sorted(numbers)
    if args.limit:
        entries = entries[: args.limit]
        numbers = numbers[: args.limit] if numbers is not None else None
    log(f"\n== {pl['folder']}: {yt_title} ({len(entries)} videos)")

    rows: list[dict] = []
    for position, entry in enumerate(entries, 1):
        # Number files by lecture number when the titles provide one: the file then stays
        # attached to the same lecture even if the playlist order changes between runs.
        number = numbers[position - 1] if numbers is not None else position
        title = entry.get("title") or entry["id"]
        existing = None if args.force else existing_episode(folder, number)
        rows.append({
            "n": number,
            "id": entry["id"],
            "title": title,
            "file": existing.name if existing else f"{number:02d} - {safe_filename(title)}.md",
            "status": "skipped" if existing else "pending",
            "reason": "",
        })

    todo = [row for row in rows if row["status"] == "pending"]
    log(f"  {len(rows) - len(todo)} already saved, {len(todo)} to fetch")

    if args.dry_run:
        for row in rows:
            log(f"  [{row['status']:>7}] {row['n']:02d} {row['title'][:70]}")
        return rows

    if todo:
        transcripts, reasons = fetch_with_ytfetcher([row["id"] for row in todo], languages)
        for row in todo:
            segments = transcripts.get(row["id"])
            source = "ytfetcher (youtube-transcript-api)"
            if not segments:
                segments, caption_error = fetch_captions(row["id"], languages, args.cookies_from_browser)
                source = "YouTube captions (yt-dlp)"
                if not segments:
                    row["reason"] = caption_error or reasons.get(row["id"]) or "no captions"
                    row["status"] = "missing"
                    log(f"  [missing] {row['n']:02d} {row['title'][:70]} — {row['reason']}")
                    time.sleep(max(0.0, args.sleep))
                    continue
            path = folder / row["file"]
            write_episode(path, row["n"], row["title"], row["id"], source, segments)
            if args.force:  # drop an older file for the same episode (title may have changed)
                for stale in folder.glob(f"{row['n']:02d} - *.md"):
                    if stale != path:
                        stale.unlink(missing_ok=True)
            row["status"] = "ok"
            log(f"  [ok] {row['n']:02d} {row['title'][:70]} ({source}, {len(segments)} lines)")
            time.sleep(max(0.0, args.sleep))

    # files saved by an earlier run still count as done
    for row in rows:
        if row["status"] == "skipped":
            row["status"] = "ok"
    write_playlist_index(folder, pl, rows)
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the Arabic transcripts of the Ayman Abdelrahim playlists.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python scripts/fetch_transcripts.py\n"
               "  python scripts/fetch_transcripts.py --only 03-psychology\n"
               "  python scripts/fetch_transcripts.py --cookies-from-browser chrome\n",
    )
    parser.add_argument("--only", nargs="*", metavar="FOLDER",
                        help="playlist folder names to process (default: all)")
    parser.add_argument("--limit", type=int, default=0,
                        help="fetch at most N episodes per playlist (0 = no limit)")
    parser.add_argument("--force", action="store_true",
                        help="re-fetch episodes that already have a file")
    parser.add_argument("--dry-run", action="store_true",
                        help="only list the episodes and what is already saved")
    parser.add_argument("--cookies-from-browser", metavar="BROWSER",
                        choices=["chrome", "chromium", "firefox", "edge", "safari", "brave", "opera", "vivaldi"],
                        help="use this browser's YouTube session (fixes 'confirm you're not a bot')")
    parser.add_argument("--sleep", type=float, default=1.5,
                        help="seconds to wait between videos (default: 1.5)")
    parser.add_argument("--no-log", action="store_true", help="do not write transcripts/_last_run.log")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    setup_console(None if args.no_log else LOG_PATH)

    log(f"Python {sys.version.split()[0]} on {sys.platform}")
    if not CONFIG_PATH.is_file():
        log(f"ERROR: {CONFIG_PATH} not found. Run this from the repository folder.")
        return 1
    if COOKIES_FILE:
        log(f"Using cookies from {COOKIES_FILE}")
    elif args.cookies_from_browser:
        log(f"Using YouTube cookies from {args.cookies_from_browser}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    languages = list(config.get("languages") or ["ar"])
    playlists = [pl for pl in config["playlists"] if not args.only or pl["folder"] in args.only]
    if not playlists:
        log(f"ERROR: no playlist matches {args.only}. Known folders: "
            f"{', '.join(pl['folder'] for pl in config['playlists'])}")
        return 1

    results: list[tuple[dict, list[dict]]] = []
    failed_playlists = 0
    try:
        for pl in playlists:
            try:
                results.append((pl, process_playlist(pl, languages, args)))
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001 - keep going with the other playlists
                failed_playlists += 1
                log(f"  ERROR in {pl['folder']}: {short(exc, 300)}")
                results.append((pl, []))
    except KeyboardInterrupt:
        log("\nStopped. Everything fetched so far is saved; run the script again to resume.")

    if not args.dry_run:
        missing = write_status(results, languages)
        if not args.only:  # a partial run must not overwrite the full overview
            write_overview(results)
        total = sum(len(rows) for _, rows in results)
        done = sum(1 for _, rows in results for row in rows if row["status"] == "ok")
        log(f"\nDone: {done}/{total} episodes saved in {TRANSCRIPTS_DIR}")
        if missing:
            log("Some episodes could not be fetched — see transcripts/_status.md.")
            log("If it says \"Sign in to confirm you're not a bot\", re-run with:")
            log("   python scripts/fetch_transcripts.py --cookies-from-browser chrome")
            log("(or firefox / edge / safari — whichever you use for YouTube).")
        if not args.no_log:
            log(f"Full log: {LOG_PATH}")

    if failed_playlists == len(playlists):
        log("\nERROR: every playlist failed to list. Check your internet connection.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
