# tasees-Ayman

Transcripts of the lecture playlists by م. أيمن عبدالرحيم ([@AymanComplete](https://www.youtube.com/@AymanComplete)).

## Layout

`transcripts/<playlist-folder>/` holds one Markdown file per episode (`NN - title.md`, with timestamped paragraphs linking back to the video) and a `README.md` index for the playlist. Playlists are listed in `transcripts/playlists.json`; `"sort_by_lecture": true` numbers episodes by the lecture number in their title (المحاضرة الأولى، الثانية …) instead of playlist order.

## Fetching

`scripts/fetch_transcripts.py` lists each playlist with yt-dlp, fetches transcripts with [ytfetcher](https://github.com/kaya70875/ytfetcher) (youtube-transcript-api), and falls back to YouTube captions (manual, then auto-generated) via yt-dlp. Re-running skips episodes already saved.

```bash
pip install -r scripts/requirements.txt
python scripts/fetch_transcripts.py            # all playlists
python scripts/fetch_transcripts.py --only 03-psychology
```

The `Fetch YouTube transcripts` GitHub Actions workflow runs the same script and commits the results. If YouTube blocks the runner ("confirm you're not a bot"), add a Netscape-format `cookies.txt` export as the `YT_COOKIES` repository secret and re-run the workflow.
