#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سجل حلقات قوائم التشغيل — يقرأ ملفات الحلقات نفسها، لا فهارس README.

لماذا: فهارس `README.md` في `transcripts/01`–`04` مقلوبة (الصف الأول يشير إلى
آخر محاضرة)، وأحيانًا تُخلط أرقام المحاضرات. ملفات الحلقات نفسها سليمة، فهي
المصدر الوحيد الموثوق.

المخرج (مولَّد — لا يُحرَّر يدويًا):
  - `episodes.json`        : بيانات كل حلقة (القائمة · الملف · المدة · الكلمات · الشكل)
  - `فهرس_الحلقات.md`      : جدول مقروء لكل قائمة + إجماليات
  - `تحذيرات.md`           : كل ما يحتاج عينًا بشرية (ملفات قصيرة، أرقام مقلوبة، غير حلقات)

الاستعمال:
  python3 08_دورات_القوائم/tools/build_playlist_registry.py
  python3 08_دورات_القوائم/tools/build_playlist_registry.py --check   # لا يكتب، يخبر إن كان السجل قديمًا
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPTS = ROOT / "transcripts"
OUT = Path(__file__).resolve().parents[1] / "01_سجل_الحلقات"

TITLES = {
    "01-umayyad-abbasid-history": ("تاريخ الأمويين والعباسيين", "أيمن عبد الرحيم"),
    "02-linguistic-awareness": ("دورة الوعي اللغوي", "أيمن عبد الرحيم"),
    "03-psychology": ("دورة علم النفس", "أيمن عبد الرحيم"),
    "04-seerah-makkah-period": ("السيرة النبوية — العهد المكي", "أيمن عبد الرحيم"),
    "05-reestablishing-muslim-awareness": ("محاضرات متفرقة", "أيمن عبد الرحيم"),
    "06-tasees-muslim-awareness": ("دورة تأسيس وعي المسلم المعاصر (١+٢)", "أيمن عبد الرحيم"),
}

TS = re.compile(r"\*\*\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\((https?://[^)]+)\)\*\*")
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
SHORT_WORDS = 1200  # أقل من كده = نص قصير يحتاج مراجعة بشرية


def ar(n) -> str:
    return str(n).translate(AR)


def secs(m) -> int:
    a, b, c = m.group(1), m.group(2), m.group(3)
    if c is None:                      # MM:SS
        return int(a) * 60 + int(b)
    return int(a) * 3600 + int(b) * 60 + int(c)


def read_episode(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    stamps = [secs(m) for m in TS.finditer(text)]
    body = TS.sub("", text)
    words = len([w for w in re.split(r"\s+", body) if w.strip()])
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), path.stem)
    link = re.search(r"- الرابط:\s*(https?://\S+)", text)
    return {
        "file": path.name,
        "title": title,
        "video": link.group(1) if link else "",
        "format": "timestamped" if stamps else "plain",
        "start": min(stamps) if stamps else None,
        "end": max(stamps) if stamps else None,
        "stamps": len(stamps),
        "words": words,
    }


def lecture_no(name: str) -> int | None:
    """رقم المحاضرة من اسم الملف أو عنوانه — لفحص ترتيب الفهرس فقط."""
    words = {"الأولى": 1, "الاولي": 1, "الأولي": 1, "الثانية": 2, "الثالثة": 3, "الرابعة": 4,
             "الخامسة": 5, "السادسة": 6, "السابعة": 7, "الثامنة": 8, "التاسعة": 9, "العاشرة": 10}
    m = re.search(r"المحاضرة\s+([^\s\]\[\(]+)", name)
    if m and m.group(1) in words:
        return words[m.group(1)]
    m = re.match(r"(\d+)\s*[-–]", name)
    return int(m.group(1)) if m else None


def readme_rows(folder: Path) -> list[str]:
    p = folder / "README.md"
    if not p.exists():
        return []
    return [ln for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.startswith("| ") and "](<" in ln]


def main(argv: list[str]) -> int:
    check = "--check" in argv
    if not TRANSCRIPTS.exists():
        print(f"✗ لا مجلد تفريغات: {TRANSCRIPTS}")
        return 1

    episodes, warnings, playlists = [], [], []
    for folder in sorted(TRANSCRIPTS.iterdir()):
        if not folder.is_dir():
            continue
        title, presenter = TITLES.get(folder.name, (folder.name, ""))
        files = sorted(p for p in folder.glob("*.md") if p.name.lower() != "readme.md")
        if not files:
            warnings.append(f"**{title}** — لا ملفات حلقات في `{folder.name}`.")
            continue

        eps, short = [], []
        for i, f in enumerate(files, 1):
            e = read_episode(f)
            e.update(playlist=folder.name, n=i)
            eps.append(e)
            if e["format"] == "plain":
                warnings.append(f"**{title}** — `{f.name}` بلا طوابع زمنية: الاقتباس منه برقم الفقرة.")
            if e["words"] < SHORT_WORDS:
                short.append((f.name, e["words"]))

        # فحص فهرس README: هل ترتيب صفوفه يخالف ترتيب الملفات؟
        rows = readme_rows(folder)
        if rows:
            mismatch = 0
            for row, ep in zip(rows, eps):
                num_in_label = lecture_no(row)
                num_in_file = lecture_no(ep["file"])
                if num_in_label and num_in_file and num_in_label != num_in_file:
                    mismatch += 1
            if mismatch >= 2:
                warnings.append(
                    f"**{title}** — فهرس `README.md` مقلوب أو مخالف في {ar(mismatch)} صفًا "
                    f"(الصف ١ يشير إلى آخر محاضرة). **الملفات هي المرجع**، لا الفهرس.")

        if short:
            names = " · ".join(f"`{n}` ({ar(w)})" for n, w in short[:4])
            more = f" و{ar(len(short) - 4)} غيرها" if len(short) > 4 else ""
            warnings.append(
                f"**{title}** — {ar(len(short))} نص قصير (< {ar(SHORT_WORDS)} كلمة) قد يكون تفريغًا ناقصًا: "
                f"{names}{more}. راجعها قبل بناء درس عليها.")
        duration = max((e["end"] or 0) for e in eps)
        playlists.append({
            "folder": folder.name,
            "title": title,
            "presenter": presenter,
            "episodes": len(eps),
            "words": sum(e["words"] for e in eps),
            "longest": duration,
        })
        episodes.extend(eps)

    data = {"source": "transcripts/ (ملفات الحلقات — لا README)", "playlists": playlists,
            "episodes": episodes, "warnings": warnings}
    index = render(data)

    OUT.mkdir(parents=True, exist_ok=True)
    jp, mp = OUT / "episodes.json", OUT / "فهرس_الحلقات.md"
    if check:
        stale = []
        for path, text in ((jp, json.dumps(data, ensure_ascii=False, indent=2) + "\n"), (mp, index)):
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        print(("✗ قديم: " + " · ".join(stale)) if stale else "ok: السجل مطابق لملفات الحلقات")
        return 1 if stale else 0

    jp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mp.write_text(index, encoding="utf-8")
    (OUT / "تحذيرات.md").write_text(render_warnings(data), encoding="utf-8")

    total_w = sum(p["words"] for p in playlists)
    print(f"ok: {len(playlists)} قوائم · {len(episodes)} حلقة · ~{total_w:,} كلمة · {len(warnings)} تحذيرًا")
    return 0


def fmt_dur(s: int | None) -> str:
    if not s:
        return "—"
    h, m = divmod(s, 60)
    return f"{h}:{m:02d} س" if h else f"{m} د"


def render(data: dict) -> str:
    L = ["# فهرس حلقات قوائم التشغيل",
         "",
         "> **ملف مولَّد** بـ`tools/build_playlist_registry.py` من ملفات الحلقات في `transcripts/` مباشرة — لا من فهارس `README.md`.",
         "> **لا يُحرَّر يدويًا.** أعد التوليد بعد أي إضافة تفريغ.",
         "",
         "## الإجماليات",
         "",
         "| # | القائمة | الحلقات | الكلمات | أطول حلقة |",
         "|---|---|---:|---:|---|"]
    for i, p in enumerate(data["playlists"], 1):
        L.append(f"| {ar(i)} | {p['title']} | {ar(p['episodes'])} | ~{p['words']:,} | {fmt_dur(p['longest'])} |")
    L.append(f"| | **الإجمالي** | **{ar(sum(p['episodes'] for p in data['playlists']))}** | "
             f"**~{sum(p['words'] for p in data['playlists']):,}** | |")
    L.append("")
    for p in data["playlists"]:
        L += [f"## {p['title']}", "", f"`transcripts/{p['folder']}/` — {ar(p['episodes'])} حلقة", "",
              "| # | الحلقة | الشكل | المدة | الكلمات | الملف |",
              "|---:|---|---|---:|---:|---|"]
        for e in [x for x in data["episodes"] if x["playlist"] == p["folder"]]:
            L.append(f"| {ar(e['n'])} | {e['title'][:60]} | "
                     f"{'طوابع' if e['format'] == 'timestamped' else 'نص متصل'} | "
                     f"{fmt_dur(e['end'])} | {e['words']:,} | `{e['file']}` |")
        L.append("")
    return "\n".join(L) + "\n"


def render_warnings(data: dict) -> str:
    L = ["# تحذيرات السجل — ما يحتاج عينًا بشرية",
         "",
         "> مولَّد بـ`tools/build_playlist_registry.py`. كل بند هنا **ليس** خطأً في المحتوى، "
         "بل شيء لا يصلح أن يبنى عليه وكيل بلا مراجعة.",
         ""]
    if data["warnings"]:
        L += [f"- {w}" for w in data["warnings"]]
    else:
        L.append("- لا شيء.")
    L += ["",
          "## قواعد ثابتة مستخلصة من هذا الفحص",
          "",
          "1. **الملفات هي المرجع، لا `README.md`** — فهارس القوائم الأربع الأولى مقلوبة الترتيب.",
          "2. **كل اقتباس يُطابق نص الحلقة حرفيًا** — والطابع الزمني لا يتجاوز آخر طابع في الملف.",
          "3. **النص القصير يُراجع يدويًا** قبل بناء درس عليه (قد يكون تفريغًا ناقصًا).",
          "4. **الحلقة بلا طوابع** يُستشهد منها برقم الفقرة + مقتطف قصير قابل للبحث.",
          ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main(sys.argv))
