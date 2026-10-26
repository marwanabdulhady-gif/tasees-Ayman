# YouTube playlist → Markdown transcripts

`youtube_playlist_transcripts.py` reads every video in a YouTube playlist, retrieves an available caption transcript, and saves **one UTF-8 Markdown file per episode**. It defaults to the playlist you provided:

<https://www.youtube.com/watch?v=kOcyMYIvmec&list=PL9saDKf7tQ7u280crdGI8ZsWu782ZVsDU>

The files preserve Arabic titles/text and are named like:

```text
001 - أيمن عبدالرحيم، دورة تأسيس وعي المسلم المعاصر المحاضرة الأولى.md
002 - … .md
_summary.csv
```

Each Markdown file has YAML metadata, a direct YouTube link, and timestamped caption lines.

## Setup

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -r requirements.txt
```

## Run the supplied playlist

Start with yt-dlp captions; it is generally more resilient to YouTube request blocks:

```bash
python youtube_playlist_transcripts.py --use-yt-dlp-captions
```

It writes into `youtube_playlist_transcripts/` by default.

### If YouTube shows a bot check on your own computer

Run the command locally with a browser profile that is already signed in to YouTube. The script reads the cookies locally through yt-dlp and sends them only to YouTube; **do not upload, send, or commit cookies**.

```bash
# Chrome / Chromium
python youtube_playlist_transcripts.py --cookies-from-browser chrome

# Firefox (example profile name)
python youtube_playlist_transcripts.py --cookies-from-browser firefox \
  --browser-profile default-release
```

If the browser database is locked, close the browser completely and try again. For an exported, local Netscape cookie file, use `--cookies /private/path/cookies.txt` instead.

## Useful options

```bash
# First 2 videos only — good test before a full playlist export
python youtube_playlist_transcripts.py --limit 2

# Different playlist and output folder
python youtube_playlist_transcripts.py "https://www.youtube.com/playlist?list=PLAYLIST_ID" \
  --output-dir my_transcripts

# Prefer English, then Arabic captions
python youtube_playlist_transcripts.py --languages en,ar

# Replace Markdown files from a prior run
python youtube_playlist_transcripts.py --overwrite

# Omit [00:00:00] markers
python youtube_playlist_transcripts.py --no-timestamps
```

## Notes

- It fetches caption tracks exposed by YouTube, including automatic captions when available; it does **not** download or transcribe audio.
- A video without retrievable captions, or one that is private, age/region restricted, or blocked by YouTube, still receives an `.md` file stating why the transcript was unavailable. Check `_summary.csv` for all results.
- Do not use the output in a way that violates YouTube's terms, a creator's rights, or applicable law. Ensure you have a right to download and use the transcripts.
