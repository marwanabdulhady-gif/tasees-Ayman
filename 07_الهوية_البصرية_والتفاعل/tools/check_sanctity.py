#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""فحص حرمة المقام النبوي في النصوص المؤلَّفة (لا في التفريغات).

    python3 07_الهوية_البصرية_والتفاعل/tools/check_sanctity.py
    python3 07_الهوية_البصرية_والتفاعل/tools/check_sanctity.py --all     # يعرض كل المواضع لا أول ٣

قرار المالك (2026-10-26) — قاعدة ثابتة في كل محتوى الدورة:

  ١) كل ذكر للنبي محمد ﷺ يُتبع بالصلاة والسلام عليه: «النبي ﷺ» · «الرسول ﷺ» ·
     «محمد ﷺ» · «صلى الله عليه وسلم». لا يُكتب «النبي» أو «الرسول» مجرَّدًا في نص
     من تأليفنا.
  ٢) لا يُوصف ﷺ بوصف يُنزله منزلة الرجال: ممنوع «الرجل في الغار» · «رجل في الأربعين»
     · «شخص عادي» · «بشر مثلنا» وما شابه؛ ومقامه ﷺ فوق مقام البشر العادي.
  ٣) لا وصف يُنقص أدب الخطاب: لا سخرية ولا تبسيط مبتذل في سياق ذكره ﷺ.

كيف يميّز الفاحص «محمد» النبي عن غيره: يُفحص لفظ «محمد» فقط إذا كان في سياق نبوي
(مسبوقًا بـ«النبي/الرسول/سيدنا/خاتم» أو متبوعًا بـ«رسول الله/صلى»)، ويُستثنى كل اسم
آخر (محمد بن … · محمد علي · محمد الفاتح · محمد إلهامي · محمد قطب · المتنبي ·
ابن نبي…) بقائمة استثناءات صريحة أسفل الملف.

المُستثنى من الفحص: التفريغات (01_تفريغات_ومصادر) والأرشيفات و`node_modules` وملفات
البناء الثنائية — لأن التفريغ نصُّ متحدثٍ يُنقل كما هو، ولا يُعاد صياغته.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# مجلدات لا تُفحص: تفريغات المنبع (نص المتحدث) + مخرجات ثنائية/قديمة مؤرشفة
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__",
    # تفريغات المنبع: نص المتحدث يُنقل كما هو ولا يُعاد صياغته
    "01_تفريغات_ومصادر", "transcripts", "09_تفريغات_أيمن", "99_الأرشيف_الكامل",
    # أرشيفات v0.1–v0.3: لا تُمس
    "الوحدة_01_تعلم_كيف_نعرف",
    "v0_2_الوحدة_01_الاستعداد_والتشخيص_والتفكير",
    "v0_3_الوحدة_01_الاستعداد_والتشخيص_والتفكير",
}
# نطاق الفحص: المحتوى التعليمي المؤلَّف فقط (لا فهارس بيانات ولا مكتبة بصرية ولا كود الموقع)
SCAN_ROOTS = [
    "02_الوحدات_التعليمية",
    "07_الهوية_البصرية_والتفاعل",
    "08_دورات_القوائم",
    "00_الوثائق_العامة",
]
# سطور هذه طبيعتها مراجع/مسارات/أسماء ملفات لا نصوصًا للقارئ
PATH_LIKE = re.compile(r"(\.md\b|\.json\b|\.csv\b|\.html\b|\.svg\b|\.zip\b|\.docx\b|\.pptx\b|/transcripts/|الدروس/|\"file\"|\"path\"|https?://)")
SKIP_SUFFIX = {".zip", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".webp", ".pdf", ".pyc"}
SCAN_SUFFIX = {".md", ".json", ".html", ".js", ".svg", ".csv", ".py", ".txt"}

# ٢) أوصاف تُنزّل المقام — ممنوعة في أي نص مؤلَّف
BANNED = [
    (re.compile(r"الرجل\s+في\s+الغار"), "«الرجل في الغار» تُنزل المقام — استعمل «النبي ﷺ في الغار»"),
    (re.compile(r"رجل\s+في\s+الغار"), "«رجل في الغار» — استعمل «النبي ﷺ في الغار»"),
    (re.compile(r"الرجل\s+ﷺ"), "«الرجل ﷺ» — استعمل «النبي ﷺ» أو «رسول الله ﷺ»"),
    (re.compile(r"بشر\s*مثلنا"), "«بشر مثلنا» في حق النبي ﷺ — ممنوع"),
    (re.compile(r"شخص(?:ية)?\s+عادي(?:ة)?"), "«شخص عادي» في حق النبي ﷺ — ممنوع"),
]
# سياق يجعل «شخصية عادية» وصفًا لغير النبي ﷺ (أسماء أخرى) — يُستثنى بالسطر
SPARED_LINE = re.compile(r"(المتنبي|بن نبي|ابن خلدون|محمد علي|الفاتح|إلهامي|قطب|الزهري|ابن إسحاق)")

# ١) ألقاب النبي ﷺ التي يجب أن يتبعها ﷺ أو «صلى الله عليه وسلم»
TITLES = re.compile(r"(?<![\u0621-\u064A])(النبي|الرسول|النبيّ|الرسولُ)(?![\u0621-\u064A])")
HONOR = ("ﷺ", "صلى الله عليه وسلم", "صلّى الله عليه وسلّم", "صلي الله عليه وسلم")
# استثناءات: «النبي» في سياق عام (الأنبياء جمعًا، «نبيّ ولا دولة») لا يُطالب بالصلاة
GENERIC = re.compile(r"(الأنبياء|أنبياء|نبيّ|نبي |نبيٌ|نبيًا|نبيين|النبيين|نبي الرحمة|خاتم النبيين)")
# سياق تاريخي منقول عن غيرنا (نص ترجمة/نقل حرفي بين «») — يُترك كما هو
IN_QUOTE = re.compile(r"«[^»]{0,200}»")
IN_BOLD = re.compile(r"\*\*[^*\n]{1,160}\*\*")


def is_prophet_title(text: str, start: int) -> bool:
    """هل هذا «النبي/الرسول» في سياق النبي محمد ﷺ؟"""
    after = text[start:start + 60].lstrip(" \u00a0*_()[]\u060c،:")
    if after.startswith(HONOR):  # سليم
        return False
    # «النبي» في سياق عام أو جمع
    window = text[max(0, start - 25):start + 25]
    if GENERIC.search(window):
        return False
    return True


def files_to_scan():
    for root_name in SCAN_ROOTS:
        for p in (ROOT / root_name).rglob("*"):
            if not p.is_file() or p.suffix not in SCAN_SUFFIX:
                continue
            parts = set(p.parts)
            if parts & SKIP_DIRS:
                continue
            if p.name in {"check_sanctity.py", "04_تعليمات_وكلاء_الذكاء_الاصطناعي.md"}:
                continue
            yield p


def scan_text(text: str, allow_quotes=True):
    hits = []
    masked = text
    if allow_quotes:
        # نحجب النصوص المنقولة حرفيًا بين «» حتى لا نطالب بالصلاة داخل اقتباس
        masked = IN_QUOTE.sub(lambda m: " " * len(m.group(0)), text)
        # الآيات والألفاظ المنقولة بين نجمتين (**…**) — تُحجب من فحص الألقاب
        masked = IN_BOLD.sub(lambda m: " " * len(m.group(0)), masked)

    for pat, why in BANNED:
        for m in pat.finditer(masked):
            line_start = masked.rfind("\n", 0, m.start()) + 1
            line = text[line_start:text.find("\n", m.start())]
            if SPARED_LINE.search(line) or PATH_LIKE.search(line):
                continue
            hits.append((m.start(), "منع", why, line.strip()[:120]))

    for m in TITLES.finditer(masked):
        if not is_prophet_title(masked, m.end()):
            continue
        line_start = masked.rfind("\n", 0, m.start()) + 1
        line = text[line_start:text.find("\n", m.start())]
        if PATH_LIKE.search(line):
            continue
        hits.append((m.start(), "صلاة", f"«{m.group(1)}» بلا ﷺ", line.strip()[:120]))
    return hits


def main(argv):
    show_all = "--all" in argv
    total, bad_files = 0, 0
    for f in sorted(files_to_scan()):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        hits = scan_text(text)
        if not hits:
            continue
        bad_files += 1
        total += len(hits)
        rel = f.relative_to(ROOT)
        print(f"✗ {rel} — {len(hits)} موضعًا")
        shown = hits if show_all else hits[:3]
        for pos, kind, why, line in shown:
            line_no = text.count("\n", 0, pos) + 1
            print(f"   {line_no}: [{kind}] {why}")
            if line:
                print(f"      …{line}…")
        if not show_all and len(hits) > len(shown):
            print(f"   … و{len(hits) - len(shown)} أخرى (--all لعرضها)")
    if total:
        print(f"\nفشل: {total} موضعًا في {bad_files} ملفًا — راجع قاعدة حرمة المقام النبوي في 04_تعليمات.")
        return 1
    print("ok: لا موضعًا يخالف قاعدة حرمة المقام النبوي في النصوص المؤلَّفة")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
