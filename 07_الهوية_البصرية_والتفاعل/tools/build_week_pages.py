"""يبني صفحات الأسابيع التفاعلية من القالب + محتوى week_content_data.py.

    python3 07_الهوية_البصرية_والتفاعل/tools/build_week_pages.py 1 2 3
    python3 07_الهوية_البصرية_والتفاعل/tools/build_week_pages.py all
    python3 07_الهوية_البصرية_والتفاعل/tools/build_week_pages.py --check      # فحص بلا كتابة

لكل أسبوع:
  · ينسخ `templates/week-template.html` كما هو (CSS/JS/البنية) — ويستبدل فقط:
    سمات <html> (data-phase/data-week) · <title> · كتلة JSON بالمعرّف "week".
  · يضع `source_sha` من `source-lock.json` (بصمة نص الأسبوع) — فلا تدخل معلومة بلا سند،
    و`check_drift.py` يعرف إن الصفحة صارت قديمة بعد أي تعديل في النص.
  · يتحقق من التسلسل (الخطة البصرية §2) ومن أن الأنماط تتبع ترتيب `visual_plan_data.py`.

لا تُعدّل الصفحات الناتجة يدويًا: عدّل المحتوى ثم أعد البناء.
المحتوى: الأسابيع 1–17 في `week_content_data.py`، وكل أسبوع جديد ملف `week_content/wNN.json`
(نفس الشكل تمامًا — انظر `week_content/_example_w08.json`).
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sources import fingerprint  # noqa: E402
from visual_plan_data import WEEKS, UNIT_DIR, ATLAS  # noqa: E402
from week_content_data import WEEK_CONTENT as _PY_CONTENT  # noqa: E402

PKG = HERE.parent                       # 07_الهوية_البصرية_والتفاعل
ROOT = PKG.parent
UNITS = ROOT / "02_الوحدات_التعليمية"
TEMPLATE = PKG / "templates" / "week-template.html"
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
CONTENT_DIR = PKG / "week_content"      # أسبوع جديد = ملف واحد week_content/wNN.json (لا تعارض بين الوكلاء)


def load_content():
    """الأسابيع 1–17 في week_content_data.py؛ ما بعدها ملف JSON لكل أسبوع. لا يُكتب أسبوع في المكانين."""
    content = dict(_PY_CONTENT)
    for f in sorted(CONTENT_DIR.glob("w[0-9][0-9].json")):
        n = int(f.stem[1:])
        if n in content:
            raise SystemExit(f"الأسبوع {n} موجود في week_content_data.py وفي {f.name} — احذف واحدًا")
        content[n] = json.loads(f.read_text(encoding="utf-8"))
    return content


WEEK_CONTENT = load_content()
LAYOUTS = {"L1", "L2", "L3", "L4", "L5", "L6", "L7"}
TRACKS = {"مستكشف", "ممارس", "متقدم"}


def ar(n):
    return str(n).translate(AR)


def week_plan(n):
    for w in WEEKS:
        if w["w"] == n:
            return w
    return None


def validate(n, c, plan):
    """يرجع قائمة أخطاء (فارغة = سليم)."""
    errs = []
    sc = c.get("screens") or []
    if not 10 <= len(sc) <= 13:
        errs.append(f"{len(sc)} شاشة (المسموح 10–13)")
    if sc and sc[0].get("layout") != "L1":
        errs.append("الشاشة الأولى لازم L1 (الغلاف)")
    if sc and sc[-1].get("layout") != "L7":
        errs.append("الشاشة الأخيرة لازم L7 (القفلة)")
    run = 0
    for i, s in enumerate(sc, 1):
        lay = s.get("layout")
        if lay not in LAYOUTS:
            errs.append(f"شاشة {i}: layout غير معروف «{lay}»")
        run = run + 1 if lay == "L3" else 0
        if run > 2:
            errs.append(f"شاشة {i}: ثلاث شاشات L3 متتالية (الحد اثنتان)")
        if s.get("pattern") and not isinstance(s.get("data"), dict):
            errs.append(f"شاشة {i}: نمط {s['pattern']} بلا data")
        if lay == "L7":
            if len(s.get("lines") or []) != 3:
                errs.append(f"شاشة {i}: L7 تحتاج ثلاث سطور")
            if not s.get("replay"):
                errs.append(f"شاشة {i}: L7 تحتاج replay")
            if set((s.get("task") or {}).keys()) != TRACKS:
                errs.append(f"شاشة {i}: L7 تحتاج task للمسارات الثلاثة")
    for k in ("eyebrow", "title", "subtitle", "question", "audio", "next"):
        if not c.get(k):
            errs.append(f"حقل مشترك ناقص: {k}")
    # الأنماط: مجموعة جزئية من الخطة، وبنفس ترتيبها.
    # استثناءان بنيويان: P15 (الدفتر، L6 دائمًا) وP06 (بطاقة مهمة الأسبوع) — لأن القالب
    # يفرض مهمة أسبوع في كل صفحة، وبعض صفوف الخطة تذكر المهمة نصًّا في القفلة بلا نمط.
    STRUCTURAL = {"P15", "P06", "P19", "P20"}   # P19/P20 تضيفها with_atlas() من ATLAS
    used = [s["pattern"] for s in sc if s.get("pattern") and s["pattern"] not in STRUCTURAL]
    if plan:
        planned = [p for p, _, _ in plan["ix"]]
        outside = [p for p in used if p not in planned]
        if outside:
            errs.append("أنماط خارج خطة الأسبوع: " + ", ".join(dict.fromkeys(outside)))
        expected = [p for p in planned if p in used]
        if used != expected:
            errs.append(f"ترتيب الأنماط مخالف للخطة: {used} بدل {expected}")
    return errs


def with_atlas(n, c):
    """يضيف شاشات الأطلس (P19/P20) من ATLAS[n] قبل شاشة الدفتر/القفلة — ما لم تكن مكتوبة يدويًا."""
    picks = ATLAS.get(n, [])
    screens = list(c["screens"])
    if not picks or any(s.get("pattern") in ("P19", "P20") for s in screens):
        return c
    at = next((i for i, s in enumerate(screens) if s.get("layout") in ("L6", "L7")), len(screens))
    extra = []
    for k in picks:
        pat = "P20" if k.get("compare") else "P19"
        ids = [k["compare"]] if k.get("compare") else ([k["page"]] if k.get("page") else [pid for _, pid in k["stations"]])
        extra.append({"layout": "L4", "pattern": pat,
                      "heading": "قارن الخريطتين" if pat == "P20" else "على الأطلس",
                      "sanad": [["الأطلس", "، ".join(ids)]],
                      "data": {kk: (list(map(list, v)) if kk == "stations" else v) for kk, v in k.items()}})
    return dict(c, screens=screens[:at] + extra + screens[at:])


def render(n, c, sha):
    html = TEMPLATE.read_text(encoding="utf-8")
    plan = week_plan(n) or {}
    phase = 1 if plan.get("u") in (1, 2, 3, 4, 17) else 2 if plan.get("u") in (5, 6, 0) else 3

    # ١) سمات الصفحة والعنوان
    html, k = re.subn(r'<html lang="ar" dir="rtl"[^>]*>',
                      f'<html lang="ar" dir="rtl" data-phase="{phase}" data-week="w{n:02d}" data-root="../../../">', html, count=1)
    if not k:
        raise SystemExit("لم أجد وسم <html> في القالب")
    html = html.replace("<title>تأسيس · الأسبوع ١</title>",
                        f"<title>تأسيس · الأسبوع {ar(n)}</title>", 1)

    # ٢) روابط مكررة محلية كانت تُرجع 404 من داخل مجلد الوحدة — نحذفها (المصدر واحد في 07_)
    html = re.sub(r'<link rel="stylesheet" href="tasees-tokens\.css">\n', "", html)
    html = re.sub(r'<script src="(?:tasees-runtime|atlas-course-bundle)\.js"[^>]*></script>\n', "", html)

    # ٣) كتلة المحتوى
    data = {
        "week": n,
        "unit": plan.get("u"),
        "phase": phase,
        "source_sha": sha,
        "eyebrow": c["eyebrow"],
        "title": c["title"],
        "subtitle": c["subtitle"],
        "question": c["question"],
        "audio": c["audio"],
        "next": c["next"],
        "screens": [],
    }
    for i, s in enumerate(c["screens"], 1):
        scr = {"id": f"w{n:02d}-{i:02d}"}
        scr.update(s)
        data["screens"].append(scr)
    block = json.dumps(data, ensure_ascii=False, indent=2)
    m = re.search(r'(<script type="application/json" id="week">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("لم أجد كتلة JSON في القالب")
    html = html[:m.start(2)] + "\n" + block + "\n" + html[m.end(2):]
    return html


def target_path(n):
    plan = week_plan(n)
    udir = UNIT_DIR.get(plan["u"]) if plan else None
    if not udir:
        raise SystemExit(f"الأسبوع {n}: لا مجلد وحدة معروف في UNIT_DIR")
    return UNITS / udir / "04_التفاعلي" / f"week-{n:02d}.html"


def main(argv):
    args = argv[1:]
    check = "--check" in args
    args = [a for a in args if not a.startswith("--")]
    wanted = sorted(WEEK_CONTENT) if (not args or args == ["all"]) else [int(a) for a in args]
    lock = json.loads((PKG / "source-lock.json").read_text(encoding="utf-8"))["weeks"]
    built, failed = [], []
    for n in wanted:
        if n not in WEEK_CONTENT:
            print(f"— الأسبوع {ar(n)}: لا محتوى بعد في week_content_data.py (تخطّي)")
            continue
        plan = week_plan(n)
        errs = validate(n, WEEK_CONTENT[n], plan)
        # صورة الخطاف: إن كُتب لها مسار فلا بد أن يكون الملف موجودًا من موضع الصفحة.
        # ملاحظة: resolve() قبل الفحص، لأن مجلد الصفحة نفسه قد لا يكون قد أُنشئ بعد،
        # و`(مجلد غير موجود)/../x` يرجع «غير موجود» في POSIX حتى لو كان x موجودًا.
        out_dir = target_path(n).parent
        for s in WEEK_CONTENT[n]["screens"]:
            src = s.get("art_src")
            if src and not (out_dir / src).resolve().exists():
                errs.append(f"صورة الخطاف {s.get('art')}: الملف غير موجود `{src}`")
        if errs:
            failed.append(n)
            print(f"✗ الأسبوع {ar(n)}: " + " · ".join(errs))
            continue
        fp = fingerprint(UNIT_DIR.get(plan["u"]), n, plan.get("svg"))
        sha = fp["script_sha"]
        if not sha:
            failed.append(n)
            print(f"✗ الأسبوع {ar(n)}: لا بصمة نص — راجع UNIT_DIR/نص الأسبوع")
            continue
        if lock.get(str(n), {}).get("script_sha") != sha:
            print(f"⚠ الأسبوع {ar(n)}: النص تغيّر منذ آخر قفل — شغّل build_visual_plan.py --relock {n} بعد المراجعة")
        html = render(n, with_atlas(n, WEEK_CONTENT[n]), sha)
        out = target_path(n)
        if check:
            exists = out.exists()
            fresh = exists and f'"source_sha": "{sha}"' in out.read_text(encoding="utf-8")
            print(("✓ " if fresh else "… ") + f"الأسبوع {ar(n)}: {out.relative_to(ROOT)}"
                  + ("" if fresh else (" غير مبني" if not exists else " قديم (sha مختلف)")))
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(html, encoding="utf-8")
            print(f"✓ الأسبوع {ar(n)}: {out.relative_to(ROOT)} · {len(with_atlas(n, WEEK_CONTENT[n])['screens'])} شاشة · sha {sha}")
        built.append(n)
    if not check:
        print(f"\nتم بناء {len(built)} صفحة" + (f" · فشل {len(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
