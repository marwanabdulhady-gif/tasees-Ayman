#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فاحص دروس دورات القوائم.

يفحص كل درس (`NN_*.md` أو `lesson-NN.md`) أمام حلقات قائمة التشغيل التي بُني عليها:

  1) **الإحالة**: كل `〔حN MM:SS〕` أو `〔حN H:MM:SS〕` → الحلقة N موجودة،
     والطابع الزمني داخل مداها الفعلي (لا يتجاوز آخر طابع في الملف).
     وللمصادر التي لا طوابع فيها (تفريغ PDF): `〔حN فM〕` → الفقرة M داخل الحلقة،
     أو `〔حN صM〕` → صفحة PDF رقم M (حيث يحمل التفريغ علامات صفحات).
     للتفريغات النصية الأصلية: `〔حN سM[-K] sha256=<البصمة الكاملة>〕` + اقتباس حرفي واحد في السطر نفسه.
  2) **الاقتباس**: كل ما بين «…» موجود في الحلقة المُحال إليها
     بعد تطبيع الهمزات والتشكيل والمسافات، عدا إحالات السطور التي تتطلب تطابقًا حرفيًا داخل النطاق المحدد.
     الاقتباس بلا إحالة يُبحث عنه في كل حلقات القائمة.
  3) **البنية**: العناوين الإلزامية لدرسٍ بأسلوب التأسيس موجودة وبالترتيب.
  4) **الأرقام**: أي رقم لاتيني في الدرس لا يوجد في الحلقات → تحذير (لا فشل) للمراجعة.

الاستعمال:
  python3 08_دورات_القوائم/tools/check_lesson.py 08_دورات_القوائم/02_دورة_علم_النفس
  python3 08_دورات_القوائم/tools/check_lesson.py <مجلد الدرس> --playlist transcripts/03-psychology
  python3 08_دورات_القوائم/tools/check_lesson.py <مجلد> --lesson 01     # درس واحد
"""
from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AR = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
CITE = re.compile(r"〔ح([٠-٩\d]+)\s+(\d{1,2}:\d{2}(?::\d{2})?)〕")
# إحالة بالفِقرة: للمصادر التي لا طوابع زمنية فيها (تفريغ PDF مثلًا)
CITE_P = re.compile(r"〔ح([٠-٩\d]+)\s+ف([٠-٩\d]+)〕")
# إحالة بصفحة PDF: للمصادر المستخرجة من كتاب/PDF بعلامات صفحات
CITE_G = re.compile(r"〔ح([٠-٩\d]+)\s+ص([٠-٩\d]+)〕")
# Exact original 1-based text lines + full byte hash; do not infer timestamps.
CITE_L = re.compile(r"〔ح([٠-٩\d]+)\s+س([٠-٩\d]+)(?:-([٠-٩\d]+))?\s+sha256=([0-9a-f]{64})〕")
CITE_L_LIKE = re.compile(r"〔ح[٠-٩\d]+\s+س[^〕]*〕")
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
    # Existing Markdown numbering and behavior remain unchanged. Only use
    # numbered raw text files when a playlist has no Markdown transcripts.
    if not files:
        for f in sorted(playlist.glob("*.txt")):
            match = re.match(r"^(\d+)", f.name)
            if not match:
                continue
            key = int(match.group(1))
            if key < 1 or key in eps:
                raise ValueError(f"invalid or duplicate text episode number: {f.name}")
            data = f.read_bytes()
            text = data.decode("utf-8")
            eps[key] = {"file": f.name, "end": None, "n_plain": norm(text), "n_stamps": norm(text),
                        "paras": [], "pages": set(), "url": None,
                        "source_lines": text.splitlines(keepends=True), "sha256": hashlib.sha256(data).hexdigest()}
        return eps
    for i, f in enumerate(files, 1):
        text = f.read_text(encoding="utf-8", errors="replace")
        stamps = [to_secs(m.group(0)[3:m.group(0).index("]")]) for m in STAMP.finditer(text)]
        body = STAMP.sub("", text)
        link = re.search(r"watch\?v=([A-Za-z0-9_-]{6,})", text)
        paras = [norm(x) for x in re.split(r"\n\s*\n", body) if len(norm(x)) > 20]
        pages = {int(ar2en(pg)) for pg in re.findall(r"بداي[ةه]\s*صفح[ةه]\s*PDF\s*([٠-٩\d]+)", text)}
        m_ep = re.search(r"^episode:\s*([٠-٩\d]+)", text, re.M)
        key = int(ar2en(m_ep.group(1))) if m_ep else i
        eps[key] = {"file": f.name, "end": max(stamps) if stamps else None,
                  "n_plain": norm(body), "n_stamps": norm(text),
                  "paras": paras, "pages": pages,
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

    try:
        eps = load_episodes(playlist)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"✗ تعذر قراءة المصدر: {exc}")
        return 2
    if not eps:
        print(f"✗ لا حلقات في {playlist}")
        return 2

    lessons = sorted(set(course.glob("[0-9][0-9]_*.md")) | set(course.glob("lesson-[0-9][0-9].md")))
    if only:
        lessons = [p for p in lessons if p.name.startswith(only) or p.stem == f"lesson-{only}"]
    if not lessons:
        print("✗ لا دروس (ملفات NN_*.md)")
        return 2

    failures, notes = [], []
    for lesson in lessons:
        text = lesson.read_text(encoding="utf-8")
        lines = text.splitlines()
        name = lesson.name

        # ١) الإحالات (طوابع زمنية، أو فِقرات حيث لا طوابع)
        cites = [(int(ar2en(m.group(1))), m.group(2), i + 1)
                 for i, ln in enumerate(lines) for m in CITE.finditer(ln)]
        pcites = [(int(ar2en(m.group(1))), int(ar2en(m.group(2))), i + 1)
                  for i, ln in enumerate(lines) for m in CITE_P.finditer(ln)]
        gcites = [(int(ar2en(m.group(1))), int(ar2en(m.group(2))), i + 1)
                  for i, ln in enumerate(lines) for m in CITE_G.finditer(ln)]
        lcites = [(m, i + 1) for i, ln in enumerate(lines) for m in CITE_L.finditer(ln)]
        count = len(cites) + len(pcites) + len(gcites) + len(lcites)
        if count < 6:
            failures.append(f"{name}: إحالات قليلة ({count}) — الدرس بلا سند كافٍ")
        for i, ln in enumerate(lines, 1):
            line_cites = list(CITE_L.finditer(ln))
            candidates = list(CITE_L_LIKE.finditer(ln))
            for start_match in re.finditer(r"〔ح[٠-٩\d]+\s+س", ln):
                if not any(candidate.start() == start_match.start() for candidate in candidates):
                    failures.append(f"{name}:{i} — إحالة سطور غير مكتملة")
            for candidate in candidates:
                if not CITE_L.fullmatch(candidate.group()):
                    failures.append(f"{name}:{i} — إحالة سطور غير صالحة أو بلا بصمة SHA-256 كاملة")
            if not line_cites:
                continue
            quotes = list(QUOTE.finditer(ln))
            if len(line_cites) != 1 or len(quotes) != 1:
                failures.append(f"{name}:{i} — يجب إحالة سطور واحدة واقتباس واحد في السطر نفسه")
                continue
            m = line_cites[0]
            n, start = int(ar2en(m.group(1))), int(ar2en(m.group(2)))
            end = int(ar2en(m.group(3))) if m.group(3) else start
            e = eps.get(n)
            if not e or 'source_lines' not in e:
                failures.append(f"{name}:{i} — الحلقة النصية {n} غير موجودة")
                continue
            if m.group(4) != e['sha256']:
                failures.append(f"{name}:{i} — بصمة الحلقة {n} لا تطابق بايتات المصدر")
            if start < 1 or end < start or end > len(e['source_lines']) or end - start + 1 > 10:
                failures.append(f"{name}:{i} — نطاق سطور غير صالح للحلقة {n}")
                continue
            quote = quotes[0].group(1)
            if not 3 <= len(quote.split()) <= 30 or quote not in ''.join(e['source_lines'][start - 1:end]):
                failures.append(f"{name}:{i} — الاقتباس ليس حرفيًا داخل السطور أو ليس 3–30 كلمة")
        for n, para, ln in pcites:
            e = eps.get(n)
            if not e:
                failures.append(f"{name}:{ln} — الحلقة {n} غير موجودة (القائمة {len(eps)} حلقة)")
            elif not (1 <= para <= len(e["paras"])):
                failures.append(f"{name}:{ln} — الفقرة {para} خارج نطاق الحلقة {n} ({len(e['paras'])} فقرة)")
        for n, pg, ln in gcites:
            e = eps.get(n)
            if not e:
                failures.append(f"{name}:{ln} — الحلقة {n} غير موجودة (القائمة {len(eps)} حلقة)")
            elif not e["pages"]:
                failures.append(f"{name}:{ln} — الحلقة {n} بلا علامات صفحات، استعمل 〔ح{n} فM〕")
            elif pg not in e["pages"]:
                failures.append(f"{name}:{ln} — الصفحة {pg} غير موجودة في الحلقة {n}")
        for n, ts, ln in cites:
            e = eps.get(n)
            if not e:
                failures.append(f"{name}:{ln} — الحلقة {n} غير موجودة (القائمة {len(eps)} حلقة)")
                continue
            if 'source_lines' in e:
                failures.append(f"{name}:{ln} — الحلقة النصية {n} بلا توقيتات؛ استخدم إحالة السطور")
            elif e["end"] and to_secs(ts) > e["end"]:
                failures.append(f"{name}:{ln} — {ts} بعد آخر الحلقة ({e['end'] // 60}:{e['end'] % 60:02d})")

        # ٢) الاقتباسات — كل اقتباس يُنسب لأقرب إحالة قبله في نفس الفقرة
        for i, ln in enumerate(lines):
            # A line citation has already been checked literally against its
            # exact source span above, not against a normalized whole episode.
            if CITE_L_LIKE.search(ln):
                continue
            for m in QUOTE.finditer(ln):
                q = norm(m.group(1))
                if len(q) < 4:
                    continue
                # الإحالة تُنسب للاقتباس إن سبقته أو لحقته في نفس السطر (الأقرب مسافةً)
                cands = [(abs(c.start() - m.start()), int(ar2en(c.group(1))), c.group(0)) for c in CITE.finditer(ln)]
                cands += [(abs(c.start() - m.start()), int(ar2en(c.group(1))), c.group(0)) for c in CITE_P.finditer(ln)]
                cands += [(abs(c.start() - m.start()), int(ar2en(c.group(1))), c.group(0)) for c in CITE_G.finditer(ln)]
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

        # ٤) أرقام لاتينية في المحتوى، لا بصمات أو إحالات أو وجهات روابط.
        # Keep the visible link label: a number in it can still be a claim.
        number_text = CITE_L.sub(' ', text)
        number_text = CITE.sub(' ', number_text)
        number_text = CITE_P.sub(' ', number_text)
        number_text = CITE_G.sub(' ', number_text)
        number_text = re.sub(r'\]\([^\n)]*\)', ']', number_text)
        # Structural numbers are metadata, not claims: the H1 lesson number and
        # the number inside the standard source-link label. Other visible link
        # labels are kept, so a numeric claim in a link is still flagged.
        number_text = re.sub(r'(?m)^#\s*الدرس\s+[^\s—]+\s+—', ' ', number_text)
        number_text = re.sub(r'\[التفريغ النصي للحلقة [٠-٩\d]+\]', ' ', number_text)
        number_text = re.sub(r'https?://\S+', ' ', number_text)
        number_text = re.sub(r'(?<![\w])[0-9a-f]{64}(?![\w])', ' ', number_text)
        number_text = re.sub(r'\bSHA-?256\b', ' ', number_text, flags=re.IGNORECASE)
        alltext = " ".join(e["n_stamps"] for e in eps.values())
        for tok in dict.fromkeys(re.findall(r"(?<![\w/])\d{2,}(?![\w])", number_text)):
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
