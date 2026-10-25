"""Download transcripts for every episode in the playlists listed in
transcripts/playlists.json, one folder per playlist.

Order of attempts per video:
  1. ytfetcher (youtube-transcript-api) in the configured languages.
  2. Fallback: YouTube captions (manual, then auto-generated) via yt-dlp.

Episodes that already have a file are skipped, so the script can be re-run
to resume. Set YT_COOKIES_FILE to a Netscape cookies.txt path if YouTube
asks to "confirm you're not a bot".
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import requests
import yt_dlp
from ytfetcher import YTFetcher
from ytfetcher.config import FetchOptions

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "transcripts"
CONFIG_PATH = TRANSCRIPTS_DIR / "playlists.json"
SUPADATA_API_KEY = os.environ.get("SUPADATA_API_KEY")
COOKIES_FILE = os.environ.get("YT_COOKIES_FILE")
if COOKIES_FILE and not Path(COOKIES_FILE).is_file():
    COOKIES_FILE = None


def ydl_opts(**extra) -> dict:
    # lang=ar keeps the original Arabic titles instead of YouTube's auto-translations.
    opts = {"quiet": True, "no_warnings": True, "ignoreerrors": True,
            "extractor_args": {"youtube": {"lang": ["ar"]}}}
    if COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
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


ORDINALS = {
    "الأولى": 1, "الأولي": 1, "الاولى": 1, "الاولي": 1, "الثانية": 2, "الثالثة": 3, "الرابعة": 4,
    "الخامسة": 5, "السادسة": 6, "السابعة": 7, "الثامنة": 8, "التاسعة": 9, "العاشرة": 10,
    "one": 1, "first": 1, "two": 2, "second": 2, "three": 3, "third": 3, "four": 4, "fourth": 4,
    "five": 5, "fifth": 5, "six": 6, "sixth": 6, "seven": 7, "seventh": 7, "eight": 8,
    "eighth": 8, "nine": 9, "ninth": 9, "ten": 10, "tenth": 10,
}


def lecture_number(title: str) -> int | None:
    """Lecture number from a title like "... المحاضرة السادسة" or "Lecture Five"."""
    m = re.search(r"(?:المحاضرة|lecture)\s+(\S+)", title, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
        if word.isdigit():
            return int(word)
        if word in ORDINALS:
            return ORDINALS[word]
    m = re.match(r"\s*(\d{1,3})\s", title)
    return int(m.group(1)) if m else None


def order_by_lecture(entries: list[dict]) -> list[dict]:
    """Sort entries by lecture number; keep playlist order if any title can't be parsed."""
    numbers = [lecture_number(e.get("title") or "") for e in entries]
    if None in numbers or len(set(numbers)) != len(numbers):
        print("  could not read every lecture number; keeping playlist order", file=sys.stderr)
        return entries
    return [e for _, e in sorted(zip(numbers, entries), key=lambda pair: pair[0])]


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


def fetch_with_supadata(video_id: str, languages: list[str]) -> list[tuple[float, str]] | None:
    """Supadata transcript API. mode=native only reads YouTube's existing captions
    (1 credit each; failed requests are free) and never pays for AI transcription."""
    headers = {"x-api-key": SUPADATA_API_KEY}
    params = {"url": f"https://www.youtube.com/watch?v={video_id}", "lang": languages[0], "mode": "native"}
    for attempt in range(5):
        time.sleep(1.5)  # free plan allows about 1 request per second
        r = requests.get("https://api.supadata.ai/v1/transcript", headers=headers, params=params, timeout=120)
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code != 200:
            print(f"  supadata {video_id}: HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
            return None
        data = r.json()
        job_id = data.get("jobId")
        while job_id:
            time.sleep(5)
            data = requests.get(f"https://api.supadata.ai/v1/transcript/{job_id}", headers=headers, timeout=60).json()
            if data.get("status") == "failed":
                print(f"  supadata {video_id}: job failed {data.get('error')}", file=sys.stderr)
                return None
            if data.get("status") != "completed":
                continue
            data = data.get("result") or data
            job_id = None
        content = data.get("content")
        if isinstance(content, list) and content:
            return [(c.get("offset", 0) / 1000, c.get("text", "").replace("\n", " ")) for c in content]
        print(f"  supadata {video_id}: empty transcript", file=sys.stderr)
        return None
    print(f"  supadata {video_id}: still rate-limited, giving up", file=sys.stderr)
    return None


def fetch_with_ytfetcher(video_ids: list[str], languages: list[str]) -> dict[str, list[tuple[float, str]]]:
    if not video_ids:
        return {}
    options = FetchOptions(languages=languages, cache_enabled=False, max_concurrent_requests=3)
    fetcher = YTFetcher.from_video_ids(video_ids, options=options)
    try:
        results = fetcher.fetch_transcripts()
    except Exception as exc:  # noqa: BLE001 - fall back to captions on any failure
        print(f"  ytfetcher failed: {exc}", file=sys.stderr)
        return {}
    for failed in fetcher.get_failed_transcripts():
        print(f"  ytfetcher: no transcript for {failed.video_id} ({failed.reason})", file=sys.stderr)
    return {
        r.video_id: [(t.start, t.text.replace("\n", " ")) for t in r.transcripts]
        for r in results
        if r.transcripts
    }


def fetch_captions(video_id: str, languages: list[str]) -> list[tuple[float, str]] | None:
    """Fallback: download caption files (manual first, then auto) with yt-dlp."""
    with tempfile.TemporaryDirectory() as tmp:
        for auto in (False, True):
            opts = ydl_opts(
                skip_download=True,
                writesubtitles=not auto,
                writeautomaticsub=auto,
                subtitleslangs=languages,
                subtitlesformat="vtt",
                outtmpl=os.path.join(tmp, "%(id)s.%(ext)s"),
            )
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            files = sorted(Path(tmp).glob(f"{video_id}*.vtt"))
            if files:
                segments = parse_vtt(files[0].read_text(encoding="utf-8"))
                if segments:
                    return segments
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


def process_playlist(pl: dict, languages: list[str]) -> list[str]:
    folder = TRANSCRIPTS_DIR / pl["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    yt_title, entries = list_playlist(pl["playlist_id"])
    if pl.get("sort_by_lecture"):
        entries = order_by_lecture(entries)
    print(f"\n== {pl['folder']}: {yt_title} ({len(entries)} videos)")

    episodes = []
    for n, e in enumerate(entries, 1):
        title = e.get("title") or e["id"]
        filename = f"{n:02d} - {safe_filename(title)}.md"
        existing = next(folder.glob(f"{n:02d} - *.md"), None)
        episodes.append({"n": n, "id": e["id"], "title": title,
                         "file": existing.name if existing else filename, "done": existing is not None})

    pending = [ep for ep in episodes if not ep["done"]]
    # With a Supadata key (CI), skip the direct-YouTube paths that cloud IPs can't use.
    transcripts = {} if SUPADATA_API_KEY else fetch_with_ytfetcher([ep["id"] for ep in pending], languages)

    missing = []
    for ep in pending:
        if SUPADATA_API_KEY:
            segments, source = fetch_with_supadata(ep["id"], languages), "Supadata API (YouTube captions)"
        else:
            segments, source = transcripts.get(ep["id"]), "ytfetcher (youtube-transcript-api)"
        if not segments and not SUPADATA_API_KEY:
            segments, source = fetch_captions(ep["id"], languages), "YouTube captions (yt-dlp)"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", help="folder names to process (default: all)")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    languages = config.get("languages") or ["ar"]
    all_missing = {}
    for pl in config["playlists"]:
        if args.only and pl["folder"] not in args.only:
            continue
        try:
            missing = process_playlist(pl, languages)
        except Exception as exc:  # noqa: BLE001 - keep going with other playlists
            print(f"  ERROR in {pl['folder']}: {exc}", file=sys.stderr)
            missing = ["<playlist failed>"]
        if missing:
            all_missing[pl["folder"]] = missing

    if all_missing:
        print("\nEpisodes without transcripts:", json.dumps(all_missing, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
