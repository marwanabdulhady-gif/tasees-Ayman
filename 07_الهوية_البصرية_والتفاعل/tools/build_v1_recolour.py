"""A2 — إعادة تلوين مشجرات الأسابيع ١–٢٦ إلى هوية «الكراسة» (v1).

    python3 07_الهوية_البصرية_والتفاعل/tools/build_v1_recolour.py            # يبني النسخ
    python3 07_الهوية_البصرية_والتفاعل/tools/build_v1_recolour.py --check     # يفحص النسخ القائمة

المدخل: كل صف `kind = مشجر/إنفوجراف` في السجل وحالته «موجود — يحتاج إعادة تلوين»
        (أي نسخة `v1_هوية/` غير موجودة بعد). **الأصل لا يُمس.**
المخرج: `<الوحدة>/03_المواد_البصرية/v1_هوية/<الاسم>.svg`.

القاعدة: **لا تتغير كلمة، ولا يتحرك صندوق، ولا يتغير `viewBox`.**
يتغير فقط ما في جدول A2 (`04_تعليمات…`): الخلفية ورق + شبكة ٢٤px، الصناديق بيضاء بإطار
بلون المرحلة، النصوص بحبر الهوية، الأسهم بلون المرحلة، `rx=6`، خط الهوية، ولاحقة
«· هوية v1» في سطر التذييل.

الفحص الذاتي بعد البناء (يفشل البناء إن أخفق شيء):
  · لا يبقى أي لون من لوحة الطراز القديم
  · لا نص أبيض (يصير غير مقروء على الورق)
  · `viewBox` كما هو · النص مطابق للأصل (`check_svg.py` يتحقق منه أيضًا)
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROOT = HERE.parents[1]
PKG = HERE.parent
REGISTER = PKG / "03_سجل_الأصول_البصرية.csv"

PHASE_COLOR = {1: "#2440A0", 2: "#8A5A2B", 3: "#2E7D57"}
PHASE_OF_UNIT = {1: 1, 2: 1, 3: 1, 4: 1, 17: 1, 5: 2, 6: 2, 0: 2, 7: 3, 8: 3, 35: 3, 36: 3}

INK, SOFT, RULE, PAPER, CARD = "#19213A", "#4A5470", "#D7DDE8", "#F7F8F3", "#FFFFFF"
RED, BLACK, GREEN = "#C23B30", "#20242C", "#2E7D57"

# ---- لوحة الطراز القديم (المصدر: جدول A2) -------------------------------------
# نص: يُستبدل بلون الحبر أو النص الثانوي. #ffffff نصًّا كان على صناديق ملوّنة، وبعد
# تحويلها إلى صناديق بيضاء صار اللون الأبيض غير مقروء — فيصير حبرًا.
OLD_TEXT = {
    "#ffffff": INK, "#e8f1f8": INK, "#2b2b2b": INK, "#0e7c6b": INK,
    "#bcd6e6": SOFT, "#6b6b6b": SOFT, "#7fa3bb": SOFT, "#9a9a9a": SOFT, "#d9d2c0": SOFT,
    "#b3423a": RED, "#e05252": RED,
    "#8a5a02": BLACK, "#5c4a2e": BLACK,   # نص التمييز/المثال (كان بنّيًا داكنًا)
}
# تعبئة الأشكال: صندوق مُلوّن ← أبيض (وإطاره يصير لون المرحلة أو الرمادي)
OLD_FILL = {
    "#0e1b2e": PAPER, "#fdf8ee": PAPER,              # خلفية الصفحة
    "#123a5c": CARD, "#0e7c6b": CARD,                 # الصندوق الأساسي
    "#0f2740": CARD, "#e8f4f1": CARD, "#d9d2c0": CARD,  # الصف الثانوي
    "#f9e9e7": CARD, "#fbeadb": CARD, "#d98e04": CARD, "#f2b134": CARD,  # تنبيه/تمييز
    "#ffffff": CARD,
}
OLD_STROKE = {
    "#39c0ba": None, "#0e7c6b": None, "#123a5c": None,   # None = لون المرحلة
    "#2b2b2b": None,
    "#0f2740": RULE, "#d9d2c0": RULE, "#7fa3bb": RULE,
    "#e05252": RED, "#b3423a": RED,
    "#f2b134": BLACK, "#d98e04": BLACK,
}
# صندوق داكن قوي (كان نصّه أبيض): يصير أبيض بإطار من لون المرحلة
BOX_STRONG = {"#2b2b2b"}
# تعبئة المسارات: رؤوس الأسهم كانت داكنة/فيروزية → لون المرحلة
PATH_FILL = {"#2b2b2b": None, "#39c0ba": None, "#b3423a": RED}
# الألوان التي كانت تعبئة تنبيه/تمييز صريحة → إطار أسود منقّط (بطاقة أو مصدر)
DASHED_FROM = {"#d98e04", "#f2b134", "#fbeadb"}
SELF_FILLED = {"#0f2740", "#e8f4f1", "#d9d2c0", "#f9e9e7"}   # صفوف ثانوية: إطار رمادي رفيع
FONT_STACK = "'IBM Plex Sans Arabic', 'Noto Sans Arabic', Tahoma, sans-serif"
GRID = ('<pattern id="v1grid" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<path d="M24 0 H0 V24" fill="none" stroke="#D7DDE8" stroke-width="0.7"/></pattern>')
MARK = "· هوية v1"
TAG_RE = re.compile(r"<(\w+)\b([^>]*?)(/?)>", re.S)
ATTR_RE = re.compile(r'\b(fill|stroke)="(#[0-9a-fA-F]{3,6})"')


def rows_to_build():
    out = []
    with open(REGISTER, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["kind"].strip() != "مشجر/إنفوجراف":
                continue
            if r["status"].strip() != "موجود — يحتاج إعادة تلوين":
                continue
            tgt = ROOT / r["target_path"]
            src = tgt.parent.parent / tgt.name
            out.append((int(r["week"]), int(r["unit"] or 0), src, tgt))
    return out


def phase_for(unit, week):
    return PHASE_COLOR[PHASE_OF_UNIT.get(unit, 1)]


def fix_attrs(tag, attrs, colour):
    """يعيد كتابة fill/stroke داخل وسم واحد حسب جدوله (نصّ/شكل). يرجّع (attrs, is_dashed)."""
    seen = set()

    def sub(m):
        attr, val = m.group(1), m.group(2).lower()
        seen.add(val)
        if tag in ("text", "tspan"):
            new = OLD_TEXT.get(val, "keep")
        elif tag == "g":
            # في المجموعة: fill يلوّن نصوصها، وstroke يلوّن خطوطها/أسهمها
            new = (OLD_STROKE if attr == "stroke" else OLD_TEXT).get(val, "keep")
        elif attr == "stroke":
            new = OLD_STROKE.get(val, "keep")
        elif tag == "path":
            new = PATH_FILL.get(val, OLD_FILL.get(val, "keep"))
        else:
            new = OLD_FILL.get(val, "keep")
        if new == "keep":
            return m.group(0)
        if new is None:
            new = colour
        return f'{attr}="{new}"'

    attrs = ATTR_RE.sub(sub, attrs)
    strong = tag in ("rect", "circle") and "#2b2b2b" in seen
    dashed = bool(seen & DASHED_FROM) and tag == "rect"
    if strong:
        attrs = re.sub(r'fill="#2b2b2b"', 'fill="#FFFFFF"', attrs)   # صندوق داكن → أبيض + إطار المرحلة
        attrs += f' stroke="{colour}" stroke-width="2"'
        return re.sub(r'\\brx="(?:[89]|1[0-9])"', 'rx="6"', attrs)

    # صندوق صار أبيض: إمّا إطار منقّط (تمييز/بطاقة) أو رمادي رفيع، ولا يبقى بلا إطار
    if tag in ("rect", "circle", "path") and 'fill="#FFFFFF"' in attrs and 'stroke="' not in attrs:
        attrs += ' stroke="#D7DDE8" stroke-width="1.5"'
    if dashed:
        if 'stroke="' in attrs:
            attrs = re.sub(r'stroke="#[0-9A-Fa-f]{6}"', 'stroke="#20242C"', attrs, count=1)
        else:
            attrs += ' stroke="#20242C"'
        if "stroke-dasharray" not in attrs:
            attrs += ' stroke-dasharray="4 3"'
    if tag == "rect":
        attrs = re.sub(r'\brx="(?:[89]|1[0-9])"', 'rx="6"', attrs)
    return attrs


def recolour(src: Path, dst: Path, colour: str) -> dict:
    raw = src.read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', raw)
    dashed = set()

    def tag_sub(m):
        tag, attrs, close = m.group(1), m.group(2), m.group(3)
        if tag == "svg":
            attrs = re.sub(r'font-family="[^"]*"', f'font-family="{FONT_STACK}"', attrs)
            return f"<{tag}{attrs}{close}>"
        if tag not in ("text", "tspan", "g", "rect", "path", "circle", "line", "polygon"):
            return m.group(0)
        return f"<{tag}{fix_attrs(tag, attrs, colour)}{close}>"

    text_body, defs_added = raw, False
    body = raw
    # 1) الخلفية + الشبكة
    bg = re.search(r'<rect width="\d+" height="\d+" fill="#(?:0e1b2e|fdf8ee)"\s*/>', body)
    if bg:
        w_h = re.search(r'width="(\d+)" height="(\d+)"', bg.group(0))
        w, h = w_h.group(1), w_h.group(2)
        grid_rect = f'<rect width="{w}" height="{h}" fill="url(#v1grid)"/>'
        body = body[:bg.start()] + f'<rect width="{w}" height="{h}" fill="{PAPER}"/>' + grid_rect + body[bg.end():]
        if "<defs>" in body:
            body = body.replace("<defs>", "<defs>" + GRID, 1)
        else:
            body = re.sub(r"(<svg\b[^>]*>)", r"\1<defs>" + GRID + "</defs>", body, count=1)
        defs_added = True

    # 2) الألوان والأنماط على كل وسم
    body = TAG_RE.sub(tag_sub, body)

    # 3) لاحقة الهوية في سطر التذييل (آخر <text>)
    texts = list(re.finditer(r"<text\b[^>]*>(.*?)</text>", body, re.S))
    if texts:
        last = texts[-1]
        inner = last.group(1)
        if MARK not in inner:
            body = body[: last.start(1)] + inner + " " + MARK + body[last.end(1):]

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(body, encoding="utf-8")

    # ---- فحص ذاتي ----
    left = {c.lower() for c in re.findall(r'#[0-9a-fA-F]{6}', body)} & {
        c for c in list(OLD_TEXT) + list(OLD_FILL) + list(OLD_STROKE) if c != "#ffffff"}
    white_text = re.findall(r'<text\b[^>]*fill="#(?:FFFFFF|ffffff)"', body)
    vb2 = re.search(r'viewBox="([^"]+)"', body)
    return dict(file=dst.name, leftovers=sorted(left), white_text=len(white_text),
                viewbox_ok=bool(vb and vb2 and vb.group(1) == vb2.group(1)),
                grid=defs_added or "v1grid" in body)


def main(argv):
    check = "--check" in argv
    rows = rows_to_build()
    if not rows:
        print("ok: لا صفوف تحتاج إعادة تلوين"
              + (" (كل نسخ v1 موجودة)" if not check else ""))
        return 0
    bad = 0
    for week, unit, src, dst in rows:
        if check:
            if not dst.exists():
                print(f"✗ الأسبوع {week}: نسخة v1 مفقودة {dst.relative_to(ROOT)}")
                bad += 1
            continue
        if not src.exists():
            print(f"✗ الأسبوع {week}: الأصل مفقود {src.relative_to(ROOT)}")
            bad += 1
            continue
        res = recolour(src, dst, phase_for(unit, week))
        problems = []
        if res["leftovers"]:
            problems.append("ألوان قديمة: " + ", ".join(res["leftovers"]))
        if res["white_text"]:
            problems.append(f"نص أبيض {res['white_text']}")
        if not res["viewbox_ok"]:
            problems.append("viewBox تغيّر")
        if not res["grid"]:
            problems.append("لا شبكة ورق")
        if problems:
            print(f"✗ الأسبوع {week}: " + " · ".join(problems))
            bad += 1
        else:
            print(f"✓ الأسبوع {week}: {dst.relative_to(ROOT)}")
    if check:
        print(("ok" if not bad else "FAIL") + f": {len(rows) - bad}/{len(rows)} نسخة v1 موجودة")
    else:
        print(("ok" if not bad else "FAIL") + f": بُنيت {len(rows) - bad}/{len(rows)} نسخة v1")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
