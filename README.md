# tasees-Ayman

Transcripts of the lecture playlists by م. أيمن عبدالرحيم ([@AymanComplete](https://www.youtube.com/@AymanComplete)),
76 episode slots across five playlists, saved as Markdown.

**YouTube blocks cloud servers** ("Sign in to confirm you're not a bot"), so the transcripts are fetched
by running the script once on an ordinary home computer. That is what the two double-click files below do.

---

## Quick start (one time)

1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).
   On Windows, tick **“Add python.exe to PATH”** during setup — this is the step people miss.
2. Download this branch: **Code → Download ZIP**, then unzip it.
3. Double-click:
   - Windows — `get_transcripts_windows.bat`
   - macOS / Linux — `get_transcripts_mac_linux.sh` (or `bash get_transcripts_mac_linux.sh`)

The runner creates a private `.venv` folder, installs the required packages into it (so nothing is
installed system-wide), and then fetches every episode into `transcripts/`. Expect roughly
**20–40 minutes** for all 76 videos. Leaving the window open is enough; the progress is printed as it goes.

> **بالعربية:** ثبّت Python 3.10+ من python.org (وعلى ويندوز فعّل «Add python.exe to PATH»)، ثم نزّل الفرع
> عبر Code → Download ZIP وفك الضغط، ثم انقر مزدوجًا على `get_transcripts_windows.bat` (ويندوز) أو
> `get_transcripts_mac_linux.sh` (ماك/لينكس). سيُنشئ البرنامج بيئة خاصة به داخل مجلد `.venv` ويجلب كل
> الحلقات إلى مجلد `transcripts/`. المدة المتوقعة ٢٠–٤٠ دقيقة. إذا توقّف، شغّله مرة أخرى وسيكمل من حيث توقّف.

### If it stops or skips episodes

Everything is resumable: an episode that already has a file is skipped, so just run the file again.

`transcripts/_status.md` lists exactly which episodes are missing and why, and
`transcripts/_last_run.log` has the full output of the last run. The usual reason is YouTube's bot check:

```
ERROR: [youtube] …: Sign in to confirm you're not a bot.
```

When that happens, let yt-dlp reuse the YouTube session from the browser you are already signed into:

```bash
# Windows
.venv\Scripts\python.exe scripts\fetch_transcripts.py --cookies-from-browser chrome
# macOS / Linux
./.venv/bin/python scripts/fetch_transcripts.py --cookies-from-browser chrome
```

`chrome`, `chromium`, `edge`, `firefox`, `safari`, `brave`, `opera` and `vivaldi` are accepted.
Close the browser first if it locks its cookie database (Chrome on Windows does).

---

## What the output looks like

```
transcripts/
├── README.md                              index of all playlists
├── _status.md                             what is missing after the last run
├── playlists.json                         the five playlists
├── 01-umayyad-abbasid-history/
│   ├── README.md                          episode index for this playlist
│   ├── 01 - … المحاضرة الأولي.md
│   └── 06 - … المحاضرة السادسة.md
├── 02-linguistic-awareness/
├── 03-psychology/
├── 04-seerah-makkah-period/
└── 05-reestablishing-muslim-awareness/
```

Each episode file starts with its number, its YouTube link and the caption source, then the transcript in
roughly one-minute paragraphs, each timestamped and linked to that second of the video:

```markdown
# أيمن عبدالرحيم, تاريخ الأمويين والعباسيين  المحاضرة السادسة

- الحلقة: 6
- الرابط: https://www.youtube.com/watch?v=BcICQHs9lbI
- المصدر: ytfetcher (youtube-transcript-api)

---

**[00:00](https://www.youtube.com/watch?v=BcICQHs9lbI&t=0s)** بسم الله الرحمن الرحيم …
```

**Numbering.** In the four course playlists every title contains the lecture ("المحاضرة السادسة",
"Lecture Five"), including in Arabic-Indic digits. Files are numbered by that lecture number and sorted
the same way, so `06 - … المحاضرة السادسة.md` keeps its name even if the playlist order changes later and
a re-run always resumes onto the right file. The fifth playlist is a collection of unrelated talks with no
lecture numbers, so it is numbered by playlist order.

## Options

```bash
python scripts/fetch_transcripts.py                 # everything, resumable
python scripts/fetch_transcripts.py --dry-run       # show what is already saved, fetch nothing
python scripts/fetch_transcripts.py --only 03-psychology
python scripts/fetch_transcripts.py --limit 2       # try two episodes per playlist
python scripts/fetch_transcripts.py --force         # re-fetch episodes that already exist
python scripts/fetch_transcripts.py --cookies-from-browser firefox
```

`--only` accepts several folders: `--only 01-umayyad-abbasid-history 02-linguistic-awareness`.

The runners pass any extra arguments straight through, e.g.
`get_transcripts_windows.bat --only 03-psychology`.

## How fetching works

For each video the script tries, in order:

1. **ytfetcher** (which uses `youtube-transcript-api`) in `ar`, `ar-EG`, `ar-SA` — the fast path.
2. **YouTube captions via yt-dlp** — the manually written Arabic track first, then the auto-generated one,
   then any Arabic track, then whatever the video has.

Requests are spread out (three at a time, with a short pause between videos and exponential backoff on
errors) so a home connection does not get throttled. Caption parsing handles both normal WebVTT files and
YouTube's "rolling" auto-captions, which repeat the previous line in every cue.

## Running it in the cloud instead (GitHub Actions)

`.github/workflows/fetch-transcripts.yml` runs the same script and commits the result. It only works if
YouTube accepts the runner's IP, which normally requires cookies: export a Netscape-format `cookies.txt`
from a **throwaway Google account** and save its contents as the repository secret `YT_COOKIES`
(Settings → Secrets and variables → Actions). Then run **Actions → Fetch YouTube transcripts → Run
workflow**. The optional `only` / `limit` inputs map to the flags above, and the run log is uploaded as an
artifact.

## Requirements

`scripts/requirements.txt` — `ytfetcher`, `youtube-transcript-api`, `yt-dlp`. The runners install them into
`.venv`; doing it manually is `pip install -r scripts/requirements.txt`.
