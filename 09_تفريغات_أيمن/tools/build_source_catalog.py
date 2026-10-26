"""Catalogue of every audio/video source of Ayman Abdulrahim's teaching that the repo already points to.

    python3 09_تفريغات_أيمن/tools/build_source_catalog.py

Scans the Telegram exports (03_فهارس_تليغرام/*/message_inventory.csv), the research docs and the
transcript folders for YouTube / SoundCloud / archive.org links, de-duplicates them, and marks each
YouTube video that already has a transcript in the repo. Writes (generated — never edit by hand):
  09_تفريغات_أيمن/sources.csv          one row per source: kind, id, url, first label seen, mentions, transcribed
  09_تفريغات_أيمن/00_حالة_المصادر.md     counts by kind and status
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ROOT = PKG.parent
csv.field_size_limit(sys.maxsize)

PATTERNS = [
    ("youtube-playlist", re.compile(r"(?:youtube\.com/(?:playlist|watch)\?[^\s\"'<>)]*?list=)([\w-]{13,})")),
    ("youtube-video", re.compile(r"(?:youtube\.com/watch\?(?:[^\s\"'<>)]*?&)?v=|youtu\.be/|youtube\.com/live/|youtube\.com/shorts/)([\w-]{11})")),
    ("youtube-channel", re.compile(r"youtube\.com/(@[\w.\-؀-ۿ]+|channel/[\w-]+|c/[\w.\-]+)")),
    ("soundcloud", re.compile(r"soundcloud\.com/([\w-]+(?:/(?:sets/)?[\w-]+)?)")),
    ("archive-org", re.compile(r"archive\.org/details/([\w.\-]+)")),
]
URL = {"youtube-playlist": "https://www.youtube.com/playlist?list={}", "youtube-video": "https://www.youtube.com/watch?v={}",
       "youtube-channel": "https://www.youtube.com/{}", "soundcloud": "https://soundcloud.com/{}",
       "archive-org": "https://archive.org/details/{}"}


def texts():
    for f in sorted((ROOT / "03_فهارس_تليغرام").glob("*/message_inventory.csv")):
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                yield f.parent.name, (row.get("text") or "") + " " + (row.get("links") or ""), (row.get("text") or "")[:90]
    for f in list((ROOT / "00_الوثائق_العامة").glob("*.md")) + [ROOT / "transcripts" / "playlists.json"]:
        t = f.read_text(encoding="utf-8")
        for line in t.splitlines():
            yield f.name, line, line[:90]


def transcribed_ids():
    ids = set()
    for f in list((ROOT / "transcripts").rglob("*.md")) + list((ROOT / "01_تفريغات_ومصادر").rglob("*.md")):
        head = f.read_text(encoding="utf-8", errors="ignore")[:1500]
        m = re.search(r"(?:watch\?v=|video_id:\s*)([\w-]{11})", head)
        if m:
            ids.add(m.group(1))
    return ids


def main():
    found = defaultdict(lambda: {"mentions": 0, "label": "", "where": set()})
    for where, text, label in texts():
        for kind, rx in PATTERNS:
            for m in rx.finditer(text):
                key = (kind, m.group(1))
                rec = found[key]
                rec["mentions"] += 1
                rec["where"].add(where)
                if not rec["label"]:
                    rec["label"] = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", label)).strip()
    done = transcribed_ids()
    fetched = {}
    import json
    pj = json.loads((ROOT / "transcripts" / "playlists.json").read_text(encoding="utf-8"))
    for p in pj["playlists"]:
        fetched[p["playlist_id"]] = p["folder"]
        rec = found[("youtube-playlist", p["playlist_id"])]
        rec["where"].add("transcripts/playlists.json")
        rec["label"] = rec["label"] or p["title"]
    rows = []
    for (kind, sid), rec in sorted(found.items(), key=lambda kv: (kv[0][0], -kv[1]["mentions"])):
        rows.append(dict(kind=kind, id=sid, url=URL[kind].format(sid), label=rec["label"][:90], mentions=rec["mentions"],
                         seen_in=" | ".join(sorted(rec["where"])),
                         transcribed=("yes" if sid in done else "no") if kind == "youtube-video"
                         else (f"yes ({fetched[sid]})" if sid in fetched else "no") if kind == "youtube-playlist" else "n/a",
                         speaker="", status="to-verify"))
    with open(PKG / "sources.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        by[r["kind"]][0] += 1
        by[r["kind"]][1] += r["transcribed"].startswith("yes")
    out = ["# حالة مصادر أيمن عبد الرحيم", "", "> **ملف مولَّد** من `tools/build_source_catalog.py`. لا تعدّله يدويًا.", "",
           "| النوع | المصادر المميزة | مُفرَّغة في المستودع |", "|---|---:|---:|"]
    out += [f"| {k} | {v[0]} | {v[1] if k.startswith('youtube-') and k != 'youtube-channel' else '—'} |" for k, v in sorted(by.items())]
    out += ["", f"المجموع: {len(rows)} مصدرًا. الفيديوهات المفرّغة سابقًا في المستودع: {len(done)}.",
            "", "**تنبيه:** القائمة مستخرجة آليًا من روابط تليجرام والوثائق؛ ليست كلها لأيمن (بعضها مراجع أو محاضرات لغيره). عمود `speaker` و`status` يملؤهما الوكيل في المهمة T1."]
    (PKG / "00_حالة_المصادر.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[4:4 + len(by) + 2]))


if __name__ == "__main__":
    main()
