"""L1 — يبني فهرس مشغّل الدورة `templates/course-index.js` من الخطة والملفات الموجودة.

    python3 07_الهوية_البصرية_والتفاعل/tools/build_course_index.py
    python3 07_الهوية_البصرية_والتفاعل/tools/build_course_index.py --check   # فحص بلا كتابة

مصادر الحقيقة (لا يُكتب شيء بيد):
  · `visual_plan_data.py`  — الوحدة والمرحلة والعنوان و`ATLAS` (صفحات الأطلس) و`COURSE_LINKS` (قرار Q2)
  · `source-lock.json`     — بصمة نص الأسبوع: بها نعرف هل الأسبوع انحرف
  · وجود الملفات على القرص — مسار صفحة الأسبوع، وملف تصميم دورة القائمة

الناتج: لكل أسبوع — الوحدة، المرحلة، العنوان، مسار `week-NN.html` إن وُجد، حجم الصفحة (شاشات)،
حالة الانحراف (نص تغيّر أو الصفحة بُنيت على نص أقدم)، معرّفات صفحات الأطلس، ورابط دورة القائمة.

أداة الفحص الذاتي: كل رابط يولّده لا بد أن يفتح ملفًا موجودًا، وإلا خرجت بـ1.
الملف مولَّد — لا يُعدَّل يدويًا (انظر قائمة «لا تُعدّل يدويًا» في 04_تعليمات).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sources import ROOT, UNITS, fingerprint  # noqa: E402
from visual_plan_data import WEEKS, UNIT_DIR, ATLAS, COURSE_LINKS  # noqa: E402

PKG = HERE.parent
TPL = PKG / "templates"
OUT = TPL / "course-index.js"
COLUMN = TPL / "column-progress.svg"
COLUMN_OUT = TPL / "course-column.js"
PLAYLISTS = ROOT / "08_دورات_القوائم"
PAGE_RE = re.compile(r'<script type="application/json" id="week">(.*?)</script>', re.S)
WEEK_FILE = re.compile(r"^week-(\d\d)\.html$")

PHASE_NAME = {1: "بناء المتلقي", 2: "بناء الخريطة التاريخية", 3: "التاريخ والحاضر والممارسة"}


def phase_of(u):
    """نفس قاعدة صفحات الأسابيع: 1 للوحدات 1–4 والتنفس 17، 2 للوحدات 5–6 والتنفس 26، وإلا 3."""
    return 1 if u in (1, 2, 3, 4, 17) else 2 if u in (5, 6, 0) else 3


def built_pages():
    """أسبوع → (مسار نسبي للجذر، بيانات كتلة JSON)."""
    out = {}
    for page in UNITS.glob("*/04_التفاعلي/week-*.html"):
        m = WEEK_FILE.match(page.name)
        if not m:
            continue
        data = {}
        j = PAGE_RE.search(page.read_text(encoding="utf-8"))
        if j:
            try:
                data = json.loads(j.group(1))
            except json.JSONDecodeError:
                data = {}
        out[int(m.group(1))] = (page.relative_to(ROOT).as_posix(), data)
    return out


def atlas_ids(picks):
    ids = []
    for c in picks:
        if c.get("compare"):
            ids.append(c["compare"])
        elif c.get("page"):
            ids.append(c["page"])
        else:
            ids += [pid for _, pid in c.get("stations", [])]
    return ids


def main(argv):
    check = "--check" in argv
    pages = built_pages()
    lock = json.loads((PKG / "source-lock.json").read_text(encoding="utf-8"))["weeks"]

    rows, problems = [], []
    for w in WEEKS:
        n, u = w["w"], w["u"]
        page, data = pages.get(n, (None, {}))
        now = fingerprint(UNIT_DIR.get(u), n, w["svg"])
        was = lock.get(str(n), {})
        drift = []
        if was.get("script_sha") and was["script_sha"] != now["script_sha"]:
            drift.append("نص الأسبوع تغيّر")
        if page and data.get("source_sha") and data["source_sha"] != now["script_sha"]:
            drift.append("الصفحة مبنية على نص أقدم")
        course = COURSE_LINKS.get(n)
        link = None
        if course:
            design = PLAYLISTS / course["dir"] / course["design"]
            if design.exists():
                link = dict(title=course["dir"].replace("_", " "), path=design.relative_to(ROOT).as_posix())
            else:
                problems.append(f"أسبوع {n}: دورة القائمة {course['dir']} بلا ملف {course['design']}")
        rows.append(dict(
            week=n, unit=u, phase=phase_of(u), phase_name=PHASE_NAME[phase_of(u)],
            title=(data.get("title") or w["title"]),
            subtitle=data.get("subtitle", ""),
            question=data.get("question", ""),
            page=page,
            screens=len(data.get("screens") or []) or None,
            drift=drift,
            atlas=atlas_ids(ATLAS.get(n, [])),
            course=link,
        ))
        if page and not (ROOT / page).exists():
            problems.append(f"أسبوع {n}: مسار الصفحة غير موجود {page}")

    missing = [r["week"] for r in rows if not r["page"]]
    if missing:
        problems.append("أسابيع بلا صفحة: " + "، ".join(map(str, missing)))

    payload = {
        "generated_by": "07_الهوية_البصرية_والتفاعل/tools/build_course_index.py",
        "weeks": rows,
    }
    text = ("/* مولَّد بـtools/build_course_index.py — لا يُعدَّل يدويًا.\n"
            "   فهرس مشغّل الدورة: كل أسبوع وحالته ومسار صفحته وصفحات أطلسه ودورة القائمة المرتبطة. */\n"
            "window.TaseesCourse = " + json.dumps(payload, ensure_ascii=False, indent=0) + ";\n")

    # العمود يُرسم مرة واحدة في templates/column-progress.svg؛ هنا ننسخه نصًّا ليعمل عبر file://
    # (لا fetch على file://)، ويبقى المصدر الوحيد للرسم هو الـSVG نفسه.
    column = ("/* مولَّد بـtools/build_course_index.py من templates/column-progress.svg — لا يُعدَّل يدويًا. */\n"
              "window.TaseesColumn = " + json.dumps({"svg": COLUMN.read_text(encoding="utf-8")}, ensure_ascii=False) + ";\n")

    if check:
        for path, want in ((OUT, text), (COLUMN_OUT, column)):
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            if old != want:
                print(f"FAIL {path.name} قديم — شغّل build_course_index.py")
                return 1
    else:
        OUT.write_text(text, encoding="utf-8")
        COLUMN_OUT.write_text(column, encoding="utf-8")

    if problems:
        for p in problems:
            print("✗ " + p)
        return 1
    built = sum(1 for r in rows if r["page"])
    drifted = [r["week"] for r in rows if r["drift"]]
    print(f"ok: course-index · {len(rows)} أسبوعًا · {built} صفحة مبنية · "
          f"{len(rows) - built} قيد البناء · {len(drifted)} منحرف · "
          f"{sum(1 for r in rows if r['atlas'])} بأطلس · {sum(1 for r in rows if r['course'])} بدورة قائمة")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
