#!/usr/bin/env python3
"""Build one Markdown transcript file per episode of a YouTube playlist.

Transcript priority per episode:
1. Creator-uploaded captions
2. YouTube automatic captions
3. Optional local faster-whisper transcription (--whisper)

Use --cookies-from-browser on your own computer if YouTube requires a browser
sign-in. Do not copy or share cookies with this script or with anyone else.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from html import unescape
from pathlib import Path
from typing import Any

import yt_dlp

PARAGRAPH_SECONDS = 60
VTT_CUE = re.compile(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{3})\s+-->")
VTT_TAG = re.compile(r"<[^>]*>")


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def slugify(text: str, max_len: int = 70) -> str:
    """Keep Arabic and non-Latin letters while removing unsafe punctuation."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:max_len].rstrip("-") or "episode"


def fmt_ts(seconds: float | int) -> str:
    seconds = max(0, int(seconds))
    hours, remaining = divmod(seconds, 3600)
    minutes, seconds = divmod(remaining, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def preferred_languages(info: dict[str, Any], requested: list[str]) -> list[str]:
    """Original video language first, then unique user language preferences."""
    languages: list[str] = []
    for language in [info.get("language"), *requested]:
        if language and language not in languages:
            languages.append(language)
    return languages


def pick_track(info: dict[str, Any], languages: list[str]) -> tuple[str | None, list[dict[str, Any]] | None, str | None]:
    """Choose manual captions before automatic captions in the requested order."""
    order = preferred_languages(info, languages)
    for kind, tracks in (("manual", info.get("subtitles") or {}), ("auto", info.get("automatic_captions") or {})):
        # Exact language code, e.g. ar.
        for language in order:
            if language in tracks:
                return language, tracks[language], kind
        # Manual tracks can use language regions like ar-SA. Auto tracks should
        # only use an explicitly original track to avoid machine translations.
        for language in order:
            if kind == "manual":
                for key, track in tracks.items():
                    if key.lower().startswith(f"{language.lower()}-"):
                        return key, track, kind
            elif f"{language}-orig" in tracks:
                key = f"{language}-orig"
                return key, tracks[key], kind
    return None, None, None


def subtract_rolling_overlap(previous: str, current: str) -> str:
    """Remove the repeated leading words in rolling YouTube caption cues."""
    old_words = previous.split()
    new_words = current.split()
    for length in range(min(len(old_words), len(new_words)), 0, -1):
        if old_words[-length:] == new_words[:length]:
            return " ".join(new_words[length:])
    return current


def normalise_segments(segments: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """Collapse whitespace and remove overlaps from auto-caption fragments."""
    cleaned: list[tuple[float, str]] = []
    previous_raw = ""
    for start, text in segments:
        raw = re.sub(r"\s+", " ", text).strip()
        if not raw:
            continue
        delta = subtract_rolling_overlap(previous_raw, raw) if previous_raw else raw
        previous_raw = raw
        if delta:
            cleaned.append((start, delta))
    return cleaned


def parse_json3(data: dict[str, Any]) -> list[tuple[float, str]]:
    """Convert YouTube json3 caption data into timestamped text fragments."""
    segments: list[tuple[float, str]] = []
    for event in data.get("events", []):
        pieces = event.get("segs")
        if not pieces:
            continue
        text = "".join(piece.get("utf8", "") for piece in pieces).replace("\n", " ").strip()
        if text:
            segments.append((event.get("tStartMs", 0) / 1000.0, text))
    return normalise_segments(segments)


def parse_vtt(raw: str) -> list[tuple[float, str]]:
    """Parse VTT caption data when json3 is unavailable."""
    segments: list[tuple[float, str]] = []
    for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")):
        match = VTT_CUE.search(block)
        if not match:
            continue
        start = (
            int(match.group("h")) * 3600
            + int(match.group("m")) * 60
            + int(match.group("s"))
            + int(match.group("ms")) / 1000
        )
        text_lines = [
            line.strip()
            for line in block.splitlines()
            if "-->" not in line and line.strip() and not line.startswith(("WEBVTT", "NOTE"))
        ]
        text = re.sub(r"\s+", " ", unescape(VTT_TAG.sub("", " ".join(text_lines)))).strip()
        if text:
            segments.append((start, text))
    return normalise_segments(segments)


def fetch_captions(ydl: yt_dlp.YoutubeDL, track: list[dict[str, Any]]) -> list[tuple[float, str]]:
    """Use the most structured subtitle track that YouTube exposes."""
    by_extension = {item.get("ext"): item["url"] for item in track if item.get("url")}
    if "json3" in by_extension:
        raw = ydl.urlopen(by_extension["json3"]).read().decode("utf-8")
        return parse_json3(json.loads(raw))
    if "vtt" in by_extension:
        raw = ydl.urlopen(by_extension["vtt"]).read().decode("utf-8")
        return parse_vtt(raw)
    return []


def whisper_transcribe(video_url: str, workdir: Path, model_name: str, ydl_options: dict[str, Any]) -> tuple[list[tuple[float, str]], str]:
    """Optionally transcribe audio locally when no YouTube captions exist."""
    from faster_whisper import WhisperModel  # installed only for --whisper

    workdir.mkdir(parents=True, exist_ok=True)
    download_options = {
        **ydl_options,
        "format": "bestaudio/best",
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        "skip_download": False,
    }
    audio_file: Path | None = None
    try:
        with yt_dlp.YoutubeDL(download_options) as ydl:
            info = ydl.extract_info(video_url, download=True)
            audio_file = Path(ydl.prepare_filename(info))
        model = WhisperModel(model_name, device="auto", compute_type="auto")
        raw_segments, metadata = model.transcribe(str(audio_file), vad_filter=True)
        segments = [(segment.start, segment.text.strip()) for segment in raw_segments if segment.text.strip()]
        return normalise_segments(segments), metadata.language
    finally:
        if audio_file:
            audio_file.unlink(missing_ok=True)


def to_paragraphs(segments: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """Join short cues into readable timestamped paragraphs of roughly a minute."""
    paragraphs: list[tuple[float, str]] = []
    current: list[str] = []
    current_start: float | None = None
    for start, text in segments:
        if current_start is None:
            current_start = start
        current.append(text)
        elapsed = start - current_start
        is_sentence_end = bool(re.search(r"[.!?؟…]$", text))
        if (elapsed >= PARAGRAPH_SECONDS and is_sentence_end) or elapsed >= PARAGRAPH_SECONDS * 2:
            paragraphs.append((current_start, re.sub(r"\s+", " ", " ".join(current)).strip()))
            current, current_start = [], None
    if current and current_start is not None:
        paragraphs.append((current_start, re.sub(r"\s+", " ", " ".join(current)).strip()))
    return paragraphs


def yaml_string(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def build_markdown(episode_number: int, info: dict[str, Any], paragraphs: list[tuple[float, str]], language: str, source: str) -> str:
    video_id = info["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    upload_date = info.get("upload_date") or ""
    if len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    duration = fmt_ts(info["duration"]) if info.get("duration") else ""
    source_label = {
        "manual": "Creator-uploaded subtitles",
        "auto": "YouTube auto-generated captions",
        "whisper": "Local Whisper speech-to-text",
    }[source]
    title = info.get("title", video_id)
    channel = info.get("channel") or info.get("uploader") or "n/a"

    output = [
        "---",
        f"episode: {episode_number}",
        f"title: {yaml_string(title)}",
        f"video_id: {video_id}",
        f"url: {video_url}",
        f"channel: {yaml_string(channel)}",
        f"upload_date: {yaml_string(upload_date)}",
        f"duration: {yaml_string(duration)}",
        f"language: {yaml_string(language)}",
        f"transcript_source: {source}",
        "---",
        "",
        f"# Episode {episode_number}: {title}",
        "",
        f"- **Video:** [{video_url}]({video_url})",
        f"- **Channel:** {channel}",
        f"- **Published:** {upload_date or 'n/a'}  |  **Duration:** {duration or 'n/a'}",
        f"- **Transcript source:** {source_label} (`{language}`)",
        "",
        "## Transcript",
        "",
    ]
    for start, text in paragraphs:
        output += [f"**[{fmt_ts(start)}]({video_url}&t={int(start)}s)** {text}", ""]
    return "\n".join(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("playlist_url")
    parser.add_argument("-o", "--out", default="transcripts", help="output folder")
    parser.add_argument("--langs", default="en,ar", help="caption priority after the original language (default: en,ar)")
    parser.add_argument("--whisper", action="store_true", help="transcribe missing-caption audio locally using faster-whisper")
    parser.add_argument("--whisper-model", default="small", help="tiny/base/small/medium/large-v3")
    parser.add_argument("--cookies-from-browser", help="local browser name, e.g. chrome or firefox")
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds to wait between episodes")
    parser.add_argument("--force", action="store_true", help="rewrite existing episode files")
    args = parser.parse_args()

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)
    languages = [language.strip() for language in args.langs.split(",") if language.strip()]
    base_options: dict[str, Any] = {"quiet": True, "no_warnings": True, "noprogress": True, "skip_download": True}
    if args.cookies_from_browser:
        base_options["cookiesfrombrowser"] = (args.cookies_from_browser, None, None, None)

    with yt_dlp.YoutubeDL({**base_options, "extract_flat": "in_playlist"}) as ydl:
        playlist = ydl.extract_info(args.playlist_url, download=False) or {}
    entries = [entry for entry in playlist.get("entries") or [] if entry and entry.get("id")]
    if not entries:
        log("No readable videos were found in the playlist.")
        return 1

    width = max(2, len(str(len(entries))))
    log(f"Playlist: {playlist.get('title', 'YouTube playlist')} — {len(entries)} episode(s)")
    index_rows: list[tuple[int, str, str | None, str]] = []
    failures: list[tuple[int, str, str]] = []

    with yt_dlp.YoutubeDL(base_options) as ydl:
        for number, entry in enumerate(entries, start=1):
            video_id = entry["id"]
            existing = list(output_dir.glob(f"{number:0{width}d}-*.md"))
            if existing and not args.force:
                log(f"[{number}/{len(entries)}] skip (exists): {existing[0].name}")
                index_rows.append((number, entry.get("title") or video_id, existing[0].name, "existing"))
                continue
            try:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                info = ydl.extract_info(video_url, download=False) or {}
                language, track, source = pick_track(info, languages)
                segments = fetch_captions(ydl, track) if track else []
                if not segments and args.whisper:
                    log(f"[{number}/{len(entries)}] no captions — Whisper ({args.whisper_model})")
                    segments, language = whisper_transcribe(video_url, output_dir / ".audio", args.whisper_model, base_options)
                    source = "whisper"
                if not segments or not language or not source:
                    raise RuntimeError("No matching caption track is available; retry locally with --whisper if appropriate.")

                language = language.removesuffix("-orig")
                filename = f"{number:0{width}d}-{slugify(info.get('title', video_id))}.md"
                (output_dir / filename).write_text(
                    build_markdown(number, info, to_paragraphs(segments), language, source), encoding="utf-8"
                )
                index_rows.append((number, info.get("title", video_id), filename, f"{source} · {language}"))
                log(f"[{number}/{len(entries)}] saved: {filename} ({source}, {language})")
            except Exception as error:
                failures.append((number, video_id, str(error)))
                index_rows.append((number, entry.get("title") or video_id, None, f"FAILED: {error}"))
                log(f"[{number}/{len(entries)}] failed {video_id}: {error}")
            time.sleep(args.sleep)

    index = [
        f"# {playlist.get('title', 'Playlist')} — Transcripts",
        "",
        f"Source: {args.playlist_url}",
        "",
        "| # | Episode | Source |",
        "|---|---|---|",
    ]
    for number, title, filename, note in index_rows:
        episode = f"[{title}]({filename})" if filename else title
        index.append(f"| {number} | {episode.replace('|', '/')} | {note.replace('|', '/')} |")
    (output_dir / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    log(f"\nDone: {len(entries) - len(failures)}/{len(entries)} episode(s) → {output_dir.resolve()}")
    for number, video_id, message in failures:
        log(f"  failed #{number} ({video_id}): {message}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
