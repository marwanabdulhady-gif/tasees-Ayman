#!/usr/bin/env python3
"""Save available YouTube captions from every video in a playlist as Markdown.

The script saves caption tracks supplied by YouTube (manual or automatic), not
an audio transcription. It does not bypass age, private-video, geo, or caption
restrictions. For local bot checks it can ask yt-dlp to use *your local browser*
cookies; never share cookies with anyone or upload them to this project.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


DEFAULT_PLAYLIST = "https://www.youtube.com/watch?v=kOcyMYIvmec&list=PL9saDKf7tQ7u280crdGI8ZsWu782ZVsDU"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")
VTT_CUE = re.compile(
    r"^(?P<start>(?:\d{1,}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{1,}:)?\d{2}:\d{2}[.,]\d{3})(?:\s+.*)?$"
)
VTT_TAG = re.compile(r"<[^>]*>")


@dataclass
class Video:
    """The minimum metadata needed to retrieve and name one playlist video."""

    position: int
    video_id: str
    title: str
    url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export YouTube playlist transcripts to one Markdown file per video."
    )
    parser.add_argument(
        "playlist_url",
        nargs="?",
        default=DEFAULT_PLAYLIST,
        help="Playlist URL (defaults to the playlist in the request).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("youtube_playlist_transcripts"),
        help="Directory to receive Markdown files (default: %(default)s).",
    )
    parser.add_argument(
        "-l",
        "--languages",
        default="ar,en",
        help="Preferred caption language codes, in order (default: %(default)s).",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=None,
        help="Only process the first N videos; useful for testing.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing Markdown files instead of skipping them.",
    )
    parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="Write plain transcript lines without [hh:mm:ss] timestamps.",
    )

    # youtube-transcript-api is convenient for public videos. yt-dlp is more
    # reliable when YouTube asks a locally logged-in browser to verify a user.
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help=(
            "Use cookies from a local browser profile (for example chrome, firefox, "
            "edge, brave, or vivaldi). This switches caption retrieval to yt-dlp. "
            "Run this only on your own computer; never share cookies."
        ),
    )
    auth.add_argument(
        "--cookies",
        type=Path,
        metavar="COOKIES_TXT",
        help=(
            "Use a local Netscape-format cookies.txt file with yt-dlp. Keep this "
            "private and do not upload it."
        ),
    )
    parser.add_argument(
        "--browser-profile",
        help=(
            "Optional profile name/path for --cookies-from-browser, such as Default "
            "or default-release."
        ),
    )
    parser.add_argument(
        "--use-yt-dlp-captions",
        action="store_true",
        help="Retrieve captions through yt-dlp even without cookies.",
    )
    return parser.parse_args()


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def normalise_text(value: Any) -> str:
    """Make titles and caption fragments safe and readable in Markdown."""
    return WHITESPACE.sub(" ", str(value or "")).strip()


def safe_filename(name: str, max_length: int = 140) -> str:
    name = INVALID_FILENAME_CHARS.sub("_", normalise_text(name))
    name = name.rstrip(". ")
    return (name[:max_length].rstrip() or "untitled")


def markdown_escape(value: str) -> str:
    """Keep YAML front-matter valid without needlessly altering Arabic text."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def timestamp(seconds: Any) -> str:
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def yt_dlp_auth_options(args: argparse.Namespace) -> dict[str, Any]:
    """Return yt-dlp options that use credentials only from the local machine."""
    if args.cookies_from_browser:
        browser = args.cookies_from_browser.strip().lower()
        if not browser:
            raise ValueError("--cookies-from-browser needs a browser name.")
        # yt-dlp's API format is (browser, profile, keyring, container).
        return {"cookiesfrombrowser": (browser, args.browser_profile, None, None)}
    if args.cookies:
        if not args.cookies.is_file():
            raise ValueError(f"Cookies file not found: {args.cookies}")
        return {"cookiefile": str(args.cookies)}
    return {}


def get_playlist_videos(
    playlist_url: str, limit: int | None, auth_options: dict[str, Any]
) -> tuple[str, list[Video]]:
    """Use yt-dlp's resilient playlist parser without downloading media."""
    options: dict[str, Any] = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "noplaylist": False,
        **auth_options,
    }
    if limit:
        options["playlistend"] = limit

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    if not info:
        raise RuntimeError("yt-dlp could not read this playlist URL.")

    # A plain video URL is still useful: export it as a one-item playlist.
    raw_entries = info.get("entries") or [info]
    playlist_title = normalise_text(info.get("title")) or "YouTube playlist"
    playlist_id = normalise_text(info.get("id"))

    videos: list[Video] = []
    for fallback_position, entry in enumerate(raw_entries, start=1):
        if not entry:
            continue
        video_id = normalise_text(entry.get("id"))
        if not video_id:
            continue
        position = entry.get("playlist_index") or fallback_position
        try:
            position = int(position)
        except (TypeError, ValueError):
            position = fallback_position
        title = normalise_text(entry.get("title")) or video_id
        url = f"https://www.youtube.com/watch?v={video_id}"
        if playlist_id:
            url += f"&list={playlist_id}"
        videos.append(Video(position=position, video_id=video_id, title=title, url=url))

    if not videos:
        raise RuntimeError("The playlist contains no readable video entries.")
    return playlist_title, videos


def fetch_transcript_api(
    video_id: str, languages: list[str]
) -> tuple[list[dict[str, Any]], str, bool | None, str]:
    """Fetch a public caption track with youtube-transcript-api >= 1.0."""
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)

    raw = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched
    snippets: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            snippets.append(item)
        else:
            snippets.append(
                {
                    "text": getattr(item, "text", ""),
                    "start": getattr(item, "start", 0),
                    "duration": getattr(item, "duration", 0),
                }
            )

    language = normalise_text(getattr(fetched, "language_code", "")) or "unknown"
    is_generated = getattr(fetched, "is_generated", None)
    return snippets, language, is_generated, "youtube-transcript-api"


def vtt_time_seconds(value: str) -> float:
    """Convert a WebVTT timestamp such as 01:02:03.500 to seconds."""
    parts = value.replace(",", ".").split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes, seconds = "0", parts[0], parts[1]
    else:
        raise ValueError(f"Unexpected WebVTT timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_vtt(caption_file: Path) -> list[dict[str, Any]]:
    """Parse the useful text cues from a downloaded WebVTT caption file."""
    lines = caption_file.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    snippets: list[dict[str, Any]] = []
    index = 0

    while index < len(lines):
        match = VTT_CUE.match(lines[index].strip())
        if not match:
            index += 1
            continue

        start = vtt_time_seconds(match.group("start"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1

        # Strip VTT voice/class/karaoke tags and decode entities such as &amp;.
        text = normalise_text(html.unescape(VTT_TAG.sub("", " ".join(text_lines))))
        if text:
            # Automatic YouTube VTT tracks use rolling captions. A new cue often
            # repeats the tail of the preceding cue plus a few new words. Keep
            # only those new words so the Markdown is not full of duplicates.
            current_words = text.split()
            previous_words = snippets[-1]["_source_words"] if snippets else []
            overlap = 0
            for length in range(min(len(previous_words), len(current_words)), 0, -1):
                if previous_words[-length:] == current_words[:length]:
                    overlap = length
                    break
            new_text = " ".join(current_words[overlap:])
            if new_text:
                snippets.append(
                    {
                        "text": new_text,
                        "start": start,
                        "duration": 0,
                        # Internal parser state; removed before returning.
                        "_source_words": current_words,
                    }
                )
            elif snippets:
                # Even when the cue adds nothing, retain its words as the
                # comparison baseline for the next rolling-caption cue.
                snippets[-1]["_source_words"] = current_words

    for snippet in snippets:
        snippet.pop("_source_words", None)
    if not snippets:
        raise RuntimeError(f"No readable caption cues were found in {caption_file.name}.")
    return snippets


def language_from_caption_filename(video_id: str, caption_file: Path) -> str:
    """yt-dlp names subtitle files as '<video id>.<language>.vtt'."""
    name = caption_file.name
    prefix = f"{video_id}."
    if name.startswith(prefix) and name.lower().endswith(".vtt"):
        return name[len(prefix) : -4]
    return "unknown"


def choose_caption_file(
    caption_dir: Path, video_id: str, languages: list[str]
) -> tuple[Path, str]:
    candidates = sorted(caption_dir.glob(f"{video_id}.*.vtt"))
    if not candidates:
        raise RuntimeError("yt-dlp did not download a matching VTT caption track.")

    candidates_with_languages = [
        (candidate, language_from_caption_filename(video_id, candidate)) for candidate in candidates
    ]
    # Honour the user's priority, accepting regional variants like ar-SA.
    for preferred in languages:
        preferred = preferred.lower()
        for candidate, language in candidates_with_languages:
            language_lower = language.lower()
            if language_lower == preferred or language_lower.startswith(f"{preferred}-"):
                return candidate, language
    return candidates_with_languages[0]


def fetch_transcript_yt_dlp(
    video: Video,
    languages: list[str],
    caption_dir: Path,
    auth_options: dict[str, Any],
) -> tuple[list[dict[str, Any]], str, bool | None, str]:
    """Download the first available preferred VTT caption through yt-dlp.

    Languages are tried one at a time rather than all at once. This preserves
    the requested priority (Arabic before English by default) and avoids a
    failure downloading a lower-priority language discarding an already
    downloaded preferred caption.
    """
    errors: list[str] = []
    for preferred_language in languages:
        options: dict[str, Any] = {
            "skip_download": True,
            "noplaylist": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [preferred_language],
            "subtitlesformat": "vtt",
            "outtmpl": str(caption_dir / "%(id)s.%(ext)s"),
            "overwrites": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            **auth_options,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(video.url, download=True) or {}
            caption_file, language = choose_caption_file(
                caption_dir, video.video_id, [preferred_language]
            )
            snippets = parse_vtt(caption_file)
            automatic_languages = {
                str(code).lower() for code in (info.get("automatic_captions") or {})
            }
            is_generated: bool | None = language.lower() in automatic_languages
            return snippets, language, is_generated, "yt-dlp"
        except Exception as error:
            errors.append(f"{preferred_language}: {normalise_text(error)}")

    detail = "; ".join(errors) or "No requested caption language was available."
    raise RuntimeError(f"yt-dlp could not retrieve captions ({detail})")


def front_matter(
    video: Video,
    playlist_title: str,
    language: str,
    is_generated: bool | None,
    backend: str,
) -> str:
    generated = "unknown" if is_generated is None else str(is_generated).lower()
    extracted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return "\n".join(
        [
            "---",
            f'title: "{markdown_escape(video.title)}"',
            f'playlist: "{markdown_escape(playlist_title)}"',
            f'video_id: "{video.video_id}"',
            f'position: {video.position}',
            f'url: "{video.url}"',
            f'transcript_language: "{markdown_escape(language)}"',
            f'transcript_is_generated: {generated}',
            f'transcript_backend: "{backend}"',
            f'extracted_at_utc: "{extracted_at}"',
            "---",
        ]
    )


def transcript_markdown(
    video: Video,
    playlist_title: str,
    snippets: Iterable[dict[str, Any]],
    language: str,
    is_generated: bool | None,
    backend: str,
    include_timestamps: bool,
) -> str:
    lines = [
        front_matter(video, playlist_title, language, is_generated, backend),
        "",
        f"# {video.title}",
        "",
        f"[Watch on YouTube]({video.url})",
        "",
        "## Transcript",
        "",
    ]
    for snippet in snippets:
        text = normalise_text(snippet.get("text", ""))
        if not text:
            continue
        if include_timestamps:
            lines.append(f"[{timestamp(snippet.get('start', 0))}] {text}")
        else:
            lines.append(text)
    return "\n".join(lines).rstrip() + "\n"


def failure_markdown(video: Video, playlist_title: str, error: Exception) -> str:
    message = normalise_text(error)
    return "\n".join(
        [
            front_matter(video, playlist_title, "unavailable", None, "none"),
            "",
            f"# {video.title}",
            "",
            f"[Watch on YouTube]({video.url})",
            "",
            "## Transcript unavailable",
            "",
            "No usable caption track could be retrieved for this video.",
            "",
            f"> {message}",
            "",
        ]
    )


def write_summary(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    """Write a small machine-readable report alongside the Markdown files."""
    fields = ["position", "video_id", "title", "url", "status", "language", "file", "message"]
    with (output_dir / "_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    languages = [code.strip() for code in args.languages.split(",") if code.strip()]
    if not languages:
        print("Error: provide at least one language code with --languages.", file=sys.stderr)
        return 2

    try:
        auth_options = yt_dlp_auth_options(args)
        playlist_title, videos = get_playlist_videos(args.playlist_url, args.limit, auth_options)
    except Exception as error:
        print(f"Error reading playlist: {error}", file=sys.stderr)
        return 1

    use_yt_dlp_captions = bool(auth_options) or args.use_yt_dlp_captions
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []
    success_count = 0

    print(f'Playlist: {playlist_title} ({len(videos)} video(s))')
    print(f"Saving to: {args.output_dir.resolve()}")
    if use_yt_dlp_captions:
        print("Caption source: yt-dlp" + (" with local browser/cookie authentication" if auth_options else ""))
    else:
        print("Caption source: youtube-transcript-api (yt-dlp fallback enabled)")

    # Downloaded VTT files live only in a temporary directory and are removed
    # after conversion. The Markdown output never contains cookie data.
    with tempfile.TemporaryDirectory(prefix="youtube-caption-") as temporary_directory:
        caption_dir = Path(temporary_directory)
        for index, video in enumerate(videos, start=1):
            filename = f"{video.position:03d} - {safe_filename(video.title)}.md"
            destination = args.output_dir / filename
            print(f"[{index}/{len(videos)}] {video.title}")

            if destination.exists() and not args.overwrite:
                print("  ↳ skipped (already exists; use --overwrite to replace)")
                summary.append(
                    {
                        "position": video.position,
                        "video_id": video.video_id,
                        "title": video.title,
                        "url": video.url,
                        "status": "skipped_existing",
                        "language": "",
                        "file": filename,
                        "message": "",
                    }
                )
                continue

            try:
                if use_yt_dlp_captions:
                    snippets, language, is_generated, backend = fetch_transcript_yt_dlp(
                        video, languages, caption_dir, auth_options
                    )
                else:
                    # Public transcript requests are lightweight, but YouTube
                    # sometimes blocks a data-centre IP. In that case attempt
                    # yt-dlp before declaring the transcript unavailable.
                    try:
                        snippets, language, is_generated, backend = fetch_transcript_api(
                            video.video_id, languages
                        )
                    except Exception as api_error:
                        try:
                            snippets, language, is_generated, backend = fetch_transcript_yt_dlp(
                                video, languages, caption_dir, auth_options
                            )
                            print("  ↳ API unavailable; recovered through yt-dlp")
                        except Exception as ytdlp_error:
                            raise RuntimeError(
                                "Both caption backends failed. "
                                f"youtube-transcript-api: {normalise_text(api_error)}; "
                                f"yt-dlp: {normalise_text(ytdlp_error)}"
                            ) from ytdlp_error
                content = transcript_markdown(
                    video,
                    playlist_title,
                    snippets,
                    language,
                    is_generated,
                    backend,
                    include_timestamps=not args.no_timestamps,
                )
                destination.write_text(content, encoding="utf-8")
                success_count += 1
                print(f"  ↳ saved ({language}; {backend})")
                status, message = "saved", ""
            except Exception as error:  # captions may be disabled, private, or unavailable
                destination.write_text(failure_markdown(video, playlist_title, error), encoding="utf-8")
                print("  ↳ unavailable; wrote an explanatory Markdown file")
                language, status, message = "", "unavailable", normalise_text(error)

            summary.append(
                {
                    "position": video.position,
                    "video_id": video.video_id,
                    "title": video.title,
                    "url": video.url,
                    "status": status,
                    "language": language,
                    "file": filename,
                    "message": message,
                }
            )

    write_summary(args.output_dir, summary)
    print(f"\nDone: {success_count}/{len(videos)} transcript(s) saved.")
    print(f"Report: {(args.output_dir / '_summary.csv').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
