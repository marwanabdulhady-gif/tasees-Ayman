"""Registry of the playlists in the repo, one short course per playlist.

    python3 08_دورات_القوائم/tools/build_playlist_registry.py

Reads every episode file itself (not the README indexes, which can be out of order) and writes:
  08_دورات_القوائم/playlists.json            generated — playlists, episodes, fingerprints, warnings
  08_دورات_القوائم/<slug>/00_الحلقات.md        generated — the episode table each course is built from
and creates, only if missing, the hand-edited scaffold of each course:
  <slug>/README.md · <slug>/00_خريطة_الدورة.json
"""
import hashlib
import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ROOT = PKG.parent
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# slug, folder, title, speaker, voice, phase colour, atlas-relevant
# Each course lives in an Arabic folder (the layout the course agents already use):
COURSE_DIR = {
    "ayman-umayyad-abbasid": "تاريخ_الأمويين_والعباسيين",
    "ayman-linguistic-awareness": "الوعي_اللغوي",
    "ayman-psychology": "علم_النفس",
    "ayman-seerah-makkah": "السيرة_النبوية_العهد_المكي",
    "ayman-reestablishing-awareness": "إعادة_تأسيس_وعي_المسلم_المعاصر",
    "q100-history": "100_سؤال_في_التاريخ",
    "rihlat-alyaqeen": "رحلة_اليقين",
    "ayman-tasees": "05_دروس_بأسلوب_تأسيس/08_تأسيس_وعي_المسلم_المعاصر",
}
PLAYLISTS = [
    ("ayman-umayyad-abbasid", "transcripts/01-umayyad-abbasid-history", "تاريخ الأمويين والعباسيين",
     "م. أيمن عبد الرحيم", "ayman", 2, True),
    ("ayman-linguistic-awareness", "transcripts/02-linguistic-awareness", "دورة الوعي اللغوي",
     "م. أيمن عبد الرحيم", "ayman", 1, False),
    ("ayman-psychology", "transcripts/03-psychology", "دورة علم النفس",
     "م. أيمن عبد الرحيم", "ayman", 1, False),
    ("ayman-seerah-makkah", "transcripts/04-seerah-makkah-period", "السيرة النبوية — العهد المكي",
     "م. أيمن عبد الرحيم", "ayman", 2, True),
    ("ayman-reestablishing-awareness", "transcripts/05-reestablishing-muslim-awareness", "إعادة تأسيس وعي المسلم المعاصر — محاضرات متفرقة",
     "م. أيمن عبد الرحيم", "ayman", 3, False),
    ("ayman-tasees", "transcripts/06-tasees-muslim-awareness", "تأسيس وعي المسلم المعاصر (المستويان ١ و٢)",
     "م. أيمن عبد الرحيم", "ayman", 3, False),
    ("q100-history", "01_تفريغات_ومصادر/100_سؤال_في_التاريخ/transcripts", "١٠٠ سؤال في التاريخ",
     "أ. محمد إلهامي — بودكاست قناة «تاريخنا» (يُتحقق من الحلقات، مهمة D0)", "owner-decision", 2, True),
    ("rihlat-alyaqeen", "01_تفريغات_ومصادر/رحلة_اليقين/transcripts", "رحلة اليقين",
     "د. إياد قنيبي", "owner-decision", 1, False),
]

ORD = {"الاولي": 1, "الاولى": 1, "الثانيه": 2, "الثالثه": 3, "الرابعه": 4, "الخامسه": 5, "السادسه": 6,
       "السابعه": 7, "الثامنه": 8, "التاسعه": 9, "العاشره": 10, "الحاديه عشر": 11}
TS = re.compile(r"\*\*\[(\d{1,2}:\d{2}(?::\d{2})?)\]")


def norm(t):
    t = re.sub(r"[ً-ٰٟـ]", "", t)
    return re.sub("[أإآ]", "ا", t).replace("ة", "ه").replace("ى", "ي")


def secs(ts):
    p = [int(x) for x in ts.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def lecture_no(title):
    nt = norm(title)
    return next((v for k, v in sorted(ORD.items(), key=lambda kv: -len(kv[0])) if "المحاضره " + k in nt), None)


def body_of(text):
    """Transcript body: after the front matter/header block."""
    for marker in ("## Transcript", "## التفريغ", "\n---\n"):
        i = text.find(marker)
        if i > -1:
            return text[i + len(marker):]
    return text


def parse(f):
    raw = f.read_text(encoding="utf-8")
    title = next((l[2:].strip() for l in raw.splitlines() if l.startswith("# ")), f.stem)
    url = re.search(r"https://www\.youtube\.com/watch\?v=[\w-]+", raw)
    body = body_of(raw)
    stamps = TS.findall(body)
    paras = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith("---")]
    n_file = int(re.match(r"\d+", f.name).group()) if re.match(r"\d+", f.name) else None
    n_title = lecture_no(title)
    return dict(n=n_file, file=str(f.relative_to(ROOT)), title=re.sub(r"\s+", " ", title), url=url.group() if url else None,
                words=len(body.split()), paragraphs=len(paras), timestamps=len(stamps),
                last_ts=stamps[-1] if stamps else None, minutes=round(secs(stamps[-1]) / 60) if stamps else None,
                lecture_in_title=n_title, sha=hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16])


def main():
    reg = []
    for slug, folder, title, speaker, voice, phase, atlas in PLAYLISTS:
        d = ROOT / folder
        files = sorted(p for p in d.glob("*.md") if p.name.lower() not in ("readme.md", "index.md") and not p.name.startswith("_"))
        eps = [parse(f) for f in files]
        warnings = []
        for e in eps:
            if e["lecture_in_title"] and e["n"] and e["lecture_in_title"] != e["n"]:
                warnings.append(f"الملف {e['n']} عنوانه «المحاضرة {e['lecture_in_title']}» — رتّب بالمحتوى لا باسم الملف")
            if e["words"] < 800:
                warnings.append(f"الحلقة {e['n']} قصيرة جدًا ({e['words']} كلمة) — تحقّق أنها تفريغ كامل")
        readme = d / "README.md"
        if readme.exists():
            rows = re.findall(r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]", readme.read_text(encoding="utf-8"), re.M)
            bad = [(int(num), lecture_no(t)) for num, t in rows
                   if lecture_no(t) and next((x["lecture_in_title"] for x in eps if x["n"] == int(num)), None) not in (None, lecture_no(t))]
            if bad:
                warnings.append(f"فهرس README في `{folder}` يخالف الملفات في {len(bad)} صفًا (مثلًا الصف {bad[0][0]} يقول «المحاضرة {bad[0][1]}») — اعتمد عنوان الملف ومحتواه، لا الفهرس")
        stamped = sum(1 for e in eps if e["timestamps"])
        reg.append(dict(slug=slug, course_dir=COURSE_DIR[slug], title=title, folder=folder, speaker=speaker, voice=voice, phase=phase, atlas=atlas,
                        episodes=len(eps), words=sum(e["words"] for e in eps),
                        citation="timestamp" if stamped == len(eps) else "paragraph" if stamped == 0 else "mixed",
                        warnings=warnings, items=eps))

        out = PKG / COURSE_DIR[slug]
        out.mkdir(parents=True, exist_ok=True)
        table = [f"# {title} — الحلقات", "", "> **ملف مولَّد** من `08_دورات_القوائم/tools/build_playlist_registry.py`. لا تعدّله يدويًا.", "",
                 f"- **المتحدث:** {speaker}", f"- **المصدر:** `{folder}/`", f"- **الحلقات:** {str(len(eps)).translate(AR)} · **الكلمات:** {sum(e['words'] for e in eps):,}",
                 f"- **طريقة الاستشهاد:** {'طابع زمني [mm:ss]' if stamped == len(eps) else 'رقم الفقرة ¶ + اقتباس قصير' if stamped == 0 else 'طابع زمني حيث يوجد، وإلا رقم الفقرة'}", ""]
        if warnings:
            table += ["## ⚠ تنبيهات", ""] + [f"- {w}" for w in warnings] + [""]
        table += ["| # | العنوان (من الملف) | الكلمات | الفقرات | الطوابع | المدة التقريبية | الرابط |", "|---:|---|---:|---:|---:|---:|---|"]
        for e in eps:
            table.append(f"| {e['n']} | {e['title']} | {e['words']:,} | {e['paragraphs']} | {e['timestamps']} | "
                         f"{(str(e['minutes']) + ' د') if e['minutes'] else '—'} | {e['url'] or '—'} |")
        (out / "00_الحلقات.md").write_text("\n".join(table) + "\n", encoding="utf-8")

        if not (out / "README.md").exists():
            (out / "README.md").write_text(
                f"# دورة «{title}»\n\n**الحالة:** لم تبدأ · **المتحدث:** {speaker}\n\n"
                f"دورة قصيرة مستقلة مبنية على قائمة «{title}» ({str(len(eps)).translate(AR)} حلقة)، بهوية «الكراسة والعمود» وقوالبها.\n"
                f"المواصفة: [`../00_مواصفة_دورة_القائمة.md`](../00_مواصفة_دورة_القائمة.md) · الحلقات: [`00_الحلقات.md`](00_الحلقات.md)\n", encoding="utf-8")
        if not (out / "00_خريطة_الدورة.json").exists():
            has_lessons = any((out / d).is_dir() and any((out / d).rglob("*.md")) for d in ("الدروس", "دروس"))
            (out / "00_خريطة_الدورة.json").write_text(json.dumps(dict(
                slug=slug, title=title, status="نصوص بلا خريطة" if has_lessons else "لم تبدأ", audience="", guiding_question="", phase=phase,
                voice=voice, lessons=[]), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    (PKG / "playlists.json").write_text(json.dumps(dict(
        note="Generated by 08_دورات_القوائم/tools/build_playlist_registry.py — do not edit by hand.",
        playlists=reg), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    order = ["ayman-psychology", "ayman-linguistic-awareness", "ayman-seerah-makkah", "ayman-umayyad-abbasid",
             "ayman-tasees", "ayman-reestablishing-awareness", "q100-history", "rihlat-alyaqeen"]
    summ = ["# القوائم ودوراتها", "", "> **ملف مولَّد** من `tools/build_playlist_registry.py`. الترتيب = ترتيب العمل الموصى به (مواصفة §6).", "",
            "| الترتيب | الدورة | المتحدث | الحلقات | الكلمات | الاستشهاد | الأطلس | تنبيهات | الحالة |", "|---:|---|---|---:|---:|---|---|---:|---|"]
    by = {r["slug"]: r for r in reg}
    for i, sl in enumerate(order, 1):
        r = by[sl]
        st = json.loads((PKG / COURSE_DIR[sl] / "00_خريطة_الدورة.json").read_text(encoding="utf-8")).get("status", "")
        summ.append(f"| {i} | [{r['title']}]({COURSE_DIR[sl]}/README.md) | {r['speaker']} | {r['episodes']} | {r['words']:,} | "
                    f"{dict(timestamp='طابع زمني', paragraph='رقم فقرة', mixed='مختلط')[r['citation']]} | {'نعم' if r['atlas'] else '—'} | {len(r['warnings'])} | {st} |")
    (PKG / "01_القوائم.md").write_text("\n".join(summ) + "\n", encoding="utf-8")
    for r in reg:
        print(f"{r['slug']:32} {r['episodes']:3} eps {r['words']:8,} words  cite={r['citation']:9} warnings={len(r['warnings'])}")


if __name__ == "__main__":
    sys.exit(main())
