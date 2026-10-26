#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فاحص دروس دورات القوائم.

يفحص كل درس (`NN_*.md`) أمام حلقات قائمة التشغيل التي بُني عليها:

  1) **الإحالة**: كل `〔حN MM:SS〕` أو `〔حN H:MM:SS〕` → الحلقة N موجودة،
     والطابع الزمني داخل مداها الفعلي (لا يتجاوز آخر طابع في الملف).
  2) **الاقتباس**: كل ما بين «…» موجود حرفيًا في الحلقة المُحال إليها
     (بعد تطبيع الهمزات والتشكيل والمسافات). الاقتباس بلا إحالة يُبحث عنه في كل حلقات القائمة.
  3) **البنية**: العناوين الإلزامية لدرسٍ بأسلوب التأسيس موجودة وبالترتيب.
  4) **الأرقام**: أي رقم لاتيني في الدرس لا يوجد في الحلقات → تحذير (لا فشل) للمراجعة.

الاستعمال:
  python3 08_دورات_القوائم/tools/check_lesson.py 08_دورات_القوائم/02_دورة_علم_النفس
  python3 08_دورات_القوائم/tools/check_lesson.py <مجلد الدرس> --playlist transcripts/03-psychology
  python3 08_دورات_القوائم/tools/check_lesson.py <مجلد> --lesson 01     # درس واحد
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AR = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
CITE = re.compile(r"〔ح([٠-٩\d]+)\s+(\d{1,2}:\d{2}(?::\d{2})?)〕")
QUOTE = re.compile(r"«([^»]{4,300})»")
STAMP = re.compile(r"\*\*\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\([^)]*\)\*\*")
REQUIRED = [
    ("سؤال الدرس", r"^#+\s*.*سؤال الدرس"),
    ("مصدر الدرس", r"^#+\s*.*مصدر الدرس"),
    ("الكتلة ١", r"^#+\s*.*الكتلة\s*١"),
    ("الكتلة ٢", r"^#+\s*.*الكتلة\s*٢"),
    ("الكتلة ٣", r"^#+\s*.*الكتلة\s*٣"),
    ("مصيدة", r"^#+\s*.*مصيدة"),
    ("المهمة", r"^#+\s*.*المهمة"),
    ("القفلة", r"^#+\s*.*القفلة"),
]


def ar2en(s: str) -> str:
    return s.translate(AR)


def norm(s: str) -> str:
    """تطبيع للمقارنة: إزالة التشكيل والتطويل، وتوحيد الهمزات والألف والياء، وتبسيط المسافات."""
    s = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[«»\"'،؛:.,!؟?()\[\]{}<>ـ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def to_secs(ts: str) -> int:
    parts = [int(p) for p in ar2en(ts).split(":")]
    return parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0] * 60 + parts[1]


def load_episodes(playlist: Path) -> dict[int, dict]:
    eps = {}
    files = sorted(p for p in playlist.glob("*.md") if p.name.lower() != "readme.md")
    for i, f in enumerate(files, 1):
        text = f.read_text(encoding="utf-8", errors="replace")
        stamps = [to_secs(m.group(0)[3:m.group(0).index("]")]) for m in STAMP.finditer(text)]
        body = STAMP.sub("", text)
        link = re.search(r"watch\?v=([A-Za-z0-9_-]{6,})", text)
        eps[i] = {"file": f.name, "end": max(stamps) if stamps else None,
                  "n_plain": norm(body), "n_stamps": norm(text),
                  "url": link.group(1) if link else None}
    return eps


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    course = Path(argv[1])
    playlist = Path(argv[argv.index("--playlist") + 1]) if "--playlist" in argv else None
    only = argv[argv.index("--lesson") + 1] if "--lesson" in argv else None
    if not course.is_dir():
        print(f"✗ ليس مجلدًا: {course}")
        return 2
    if playlist is None:
        hint = course / "course.json"
        if hint.exists():
            import json
            playlist = ROOT / json.loads(hint.read_text(encoding="utf-8"))["playlist"]
        else:
            print("✗ حدّد القائمة بـ--playlist أو ضع course.json في مجلد الدورة")
            return 2
    if not playlist.is_absolute():
        playlist = ROOT / playlist

    eps = load_episodes(playlist)
    if not eps:
        print(f"✗ لا حلقات في {playlist}")
        return 2

    lessons = sorted(p for p in course.glob("[0-9][0-9]_*.md"))
    if only:
        lessons = [p for p in lessons if p.name.startswith(only)] or lessons
    if not lessons:
        print("✗ لا دروس (ملفات NN_*.md)")
        return 2

    failures, notes = [], []
    for lesson in lessons:
        text = lesson.read_text(encoding="utf-8")
        lines = text.splitlines()
        name = lesson.name

        # ١) الإحالات
        cites = [(int(ar2en(m.group(1))), m.group(2), i + 1)
                 for i, ln in enumerate(lines) for m in CITE.finditer(ln)]
        if len(cites) < 6:
            failures.append(f"{name}: إحالات قليلة ({len(cites)}) — الدرس بلا سند كافٍ")
        for n, ts, ln in cites:
            e = eps.get(n)
            if not e:
                failures.append(f"{name}:{ln} — الحلقة {n} غير موجودة (القائمة {len(eps)} حلقة)")
                continue
            if e["end"] and to_secs(ts) > e["end"]:
                failures.append(f"{name}:{ln} — {ts} بعد آخر الحلقة ({e['end'] // 60}:{e['end'] % 60:02d})")

        # ٢) الاقتباسات — كل اقتباس يُنسب لأقرب إحالة قبله في نفس الفقرة
        for i, ln in enumerate(lines):
            for m in QUOTE.finditer(ln):
                q = norm(m.group(1))
                if len(q) < 4:
                    continue
                # الإحالة تُنسب للاقتباس إن سبقته أو لحقته في نفس السطر (الأقرب مسافةً)
                cands = [(abs(c.start() - m.start()), int(ar2en(c.group(1)))) for c in CITE.finditer(ln)]
                target = min(cands)[1] if cands else None
                pool = {target: eps[target]} if target in eps else eps
                if not any(q in e["n_stamps"] or q in e["n_plain"] for e in pool.values()):
                    where = f"الحلقة {target}" if target else "أي حلقة"
                    failures.append(f"{name}:{i + 1} — اقتباس غير موجود في {where}: «{m.group(1)[:60]}»")
                if target is None:
                    notes.append(f"{name}:{i + 1} — اقتباس بلا إحالة في نفس السطر: «{m.group(1)[:40]}»")

        # ٢.٥) الرابط: رابط الحلقة في «مصدر الدرس» لا بد أن يكون رابط الحلقة المُحال إليها
        vids = set(re.findall(r"watch\?v=([A-Za-z0-9_-]{6,})", text))
        if vids and cites:
            modal = Counter(n for n, _, _ in cites).most_common(1)[0][0]
            want = eps.get(modal, {}).get("url")
            if want and want not in vids:
                failures.append(f"{name} — رابط الحلقة لا يطابق الحلقة {modal} (المتوقع …{want})")

        # ٣) البنية
        pos = 0
        for label, pat in REQUIRED:
            m = re.search(pat, text, re.M)
            if not m:
                failures.append(f"{name}: قسم ناقص «{label}»")
            elif m.start() < pos:
                failures.append(f"{name}: قسم «{label}» خارج الترتيب")
            else:
                pos = m.start()

        # ٤) أرقام لاتينية غير موجودة في الحلقات
        alltext = " ".join(e["n_stamps"] for e in eps.values())
        for tok in dict.fromkeys(re.findall(r"(?<![\w/])\d{2,}(?![\w])", text)):
            if ar2en(tok) not in alltext:
                notes.append(f"{name} — رقم «{tok}» غير موجود في الحلقات: راجعه")

    for n in notes:
        print("· " + n)
    if failures:
        for f in failures:
            print("✗ " + f)
        print(f"\nفشل: {len(failures)} · ملاحظات: {len(notes)}")
        return 1
    print(f"ok: {len(lessons)} درسًا اجتاز الإحالات والاقتباسات والبنية · ملاحظات: {len(notes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
