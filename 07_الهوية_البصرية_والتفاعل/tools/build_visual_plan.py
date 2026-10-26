"""Builds the generated plan files from visual_plan_data.py. Deterministic; rerun after any edit.

    python3 07_الهوية_البصرية_والتفاعل/tools/build_visual_plan.py

Exits non-zero if a referenced library photo or existing SVG is missing.

Source lock: source-lock.json records the script/SVG fingerprint each week's plan was
reviewed against. Existing entries are kept; new weeks are added. After you re-read an
edited week and update visual_plan_data.py, accept the new text with:
    python3 07_الهوية_البصرية_والتفاعل/tools/build_visual_plan.py --relock 3,7     (or --relock all)
"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from visual_plan_data import PATTERNS, WEEKS, UNIT_DIR, UNIT_COVERS, ATLAS  # noqa: E402
from sources import fingerprint  # noqa: E402
from check_svg import palette, HEX  # noqa: E402

PKG = HERE.parent                    # 07_الهوية_البصرية_والتفاعل
ROOT = PKG.parent                    # repo root
LIB = ROOT / "06_المكتبة_البصرية"
UNITS = ROOT / "02_الوحدات_التعليمية"
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

STYLE_SUFFIX = (
    "Style: a hand-drawn illustration in blue ballpoint pen (#2440A0) on off-white squared notebook paper "
    "(#F7F8F3 with faint blue 5 mm grid). Confident single-weight pen lines with light cross-hatching for shade, "
    "like an engineer's sketch on a lecture board. Flat, no 3D, no photorealism, no gradients, no glow. "
    "At most ONE accent colour used sparingly: {accent}. Generous empty paper around the subject; keep the "
    "right third of the frame quiet for on-screen text. 16:9 landscape, 1920x1080. "
    "Absolutely no text, letters, Arabic or Latin script, numbers, logos, signatures or watermarks anywhere. "
    "No human faces: any person is a tiny distant outline silhouette with no facial features. "
    "No religious figures, no prophets, no companions, no real people, no weapons, no blood, no fire, no flags, "
    "no sectarian or national symbols."
)
ACCENT = {1: "brick red #C23B30 for one small detail", 2: "sepia ink #8A5A2B", 3: "green ink #2E7D57"}


def phase_of(u):
    return 1 if u in (1, 2, 3, 4, 17) else 2 if u in (5, 6, 26, 0) else 3


def approved_assets():
    """معرّفات الصور التي اعتمدها المالك — من ملف الاعتماد، لا بتحرير السجل يدويًا."""
    p = PKG / "08_اعتماد_الأصول.json"
    if not p.exists():
        return set()
    return set(json.loads(p.read_text(encoding="utf-8")).get("assets", []))


def lib_license():
    out = {}
    with open(LIB / "00_فهرس_المكتبة_البصرية.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["file"]] = r["license_class"]
    return out


def main():
    relock = set()
    if "--relock" in sys.argv:
        arg = sys.argv[sys.argv.index("--relock") + 1]
        relock = {w["w"] for w in WEEKS} if arg == "all" else {int(x) for x in arg.split(",")}
    lock_path = PKG / "source-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))["weeks"] if lock_path.exists() else {}
    lic = lib_license()
    APPROVED = approved_assets()
    errors, rows, prompts = [], [], []
    add = lambda **k: rows.append(k)

    # programme assets — already made in templates/
    for aid, desc, path in [
        ("tas-prog-logo", "شعار العمود", "07_الهوية_البصرية_والتفاعل/templates/logo-mark.svg"),
        ("tas-prog-column", "عمود التقدم 8×4 + رباطا التنفس", "07_الهوية_البصرية_والتفاعل/templates/column-progress.svg"),
        ("tas-prog-tokens", "رموز التصميم CSS + JSON", "07_الهوية_البصرية_والتفاعل/templates/tasees-tokens.css"),
        ("tas-prog-screens", "قوالب الشاشات السبع + مكونات الأنماط", "07_الهوية_البصرية_والتفاعل/templates/screen-templates.html"),
    ]:
        add(asset_id=aid, week="", unit="", kind="برنامج", route="SVG/HTML يدوي", description=desc,
            prompt_ref="", target_path=path, license="أصلي", status="جاهز", gate="V1–V8")
    icons_dir = ROOT / "07_الهوية_البصرية_والتفاعل" / "templates" / "icons"
    icon_names = ("sanad", "notebook", "brick", "card", "trap", "check",
                  "review", "listen", "predict", "breaker", "scale", "map")
    icon_done = sum((icons_dir / f"icon-{n}.svg").exists() for n in icon_names)
    icon_status = ("جاهز — ١٢ أيقونة ولوحة" if icon_done == len(icon_names)
                   else f"جزئي — {icon_done}/{len(icon_names)}" if icon_done else "مطلوب")
    add(asset_id="tas-prog-pen-icons", week="", unit="", kind="برنامج", route="SVG يدوي",
        description="12 أيقونة بخط القلم: سند، دفتر، طوبة، كارت، مصيدة، صح، راجع، سماعة، توقّع، قاطع، ميزان، خريطة",
        prompt_ref="04 §مهمة A3", target_path="07_الهوية_البصرية_والتفاعل/templates/icons/", license="أصلي",
        status=icon_status, gate="V1, V4")

    for u, name, body in UNIT_COVERS:
        aid = f"tas-u{u}-cover"
        cover_png = ROOT / "07_الهوية_البصرية_والتفاعل" / "assets" / "covers" / f"{aid}.png"
        cover_status = ("معتمد" if aid in APPROVED else "مولود — بانتظار اعتماد المالك") if cover_png.exists() else "مطلوب"
        add(asset_id=aid, week="", unit=u, kind="غلاف وحدة", route="AI still", description=name,
            prompt_ref=aid, target_path=f"07_الهوية_البصرية_والتفاعل/assets/covers/{aid}.png", license="مولد AI",
            status=cover_status, gate="V2, V3, V5")
        prompts.append((aid, f"غلاف الوحدة {str(u).translate(AR)} — {name}", body, phase_of(u)))

    imap = []
    for w in WEEKS:
        u, wk = w["u"], w["w"]
        udir = UNIT_DIR.get(u)
        vis = f"02_الوحدات_التعليمية/{udir}/03_المواد_البصرية" if udir else "(يُنشأ مع الوحدة)"
        if w["svg"]:
            src = UNITS / udir / "03_المواد_البصرية" / w["svg"]
            if not src.exists():
                errors.append(f"missing SVG: {src}")
            native = src.exists() and not ({h.lower() for h in HEX.findall(src.read_text(encoding="utf-8"))} - palette())
            add(asset_id=f"tas-w{wk:02d}-svg", week=wk, unit=u, kind="مشجر/إنفوجراف",
                route="بهوية v1 أصلًا" if native else "SVG إعادة تلوين",
                description=(f"{w['svg']} مرسوم بألوان الهوية من البداية" if native else f"إعادة رسم {w['svg']} بهوية الكراسة (لا تغيير في المحتوى)"),
                prompt_ref="" if native else "04 §مهمة A2",
                target_path=f"{vis}/{w['svg']}" if native else f"{vis}/v1_هوية/{w['svg']}", license="أصلي",
                status="جاهز" if native else "موجود — يحتاج إعادة تلوين", gate="V1, V4, V6")
        for aid, ar, body in w["hooks"]:
            hook_png = UNITS / udir / "03_المواد_البصرية" / "hooks" / f"{aid}.png" if udir else None
            hook_status = ("معتمد" if aid in APPROVED else "مولود — بانتظار اعتماد المالك") \
                if (hook_png and hook_png.exists()) else "مطلوب"
            add(asset_id=aid, week=wk, unit=u, kind="رسم الخطاف", route="AI still", description=ar,
                prompt_ref=aid, target_path=f"{vis}/hooks/{aid}.png", license="مولد AI", status=hook_status, gate="V2, V3, V5")
            prompts.append((aid, f"الأسبوع {str(wk).translate(AR)} — {ar}", body, phase_of(u)))
        for aid, ar in w["authored"]:
            authored_svg = ROOT / vis / "interactive" / f"{aid}.svg"
            add(asset_id=aid, week=wk, unit=u, kind="رسم تفاعل", route="SVG يدوي", description=ar,
                prompt_ref="04 §مهمة A4", target_path=f"{vis}/interactive/{aid}.svg", license="أصلي",
                status="جاهز" if authored_svg.exists() else "مطلوب", gate="V1, V4, V6")
        for i, ph in enumerate(w["photos"], 1):
            if not (LIB / ph).exists():
                errors.append(f"missing photo: {ph}")
            add(asset_id=f"tas-w{wk:02d}-photo-{i}", week=wk, unit=u, kind="صورة مكتبة", route="duotone CSS",
                description=Path(ph).stem.replace("_", " "), prompt_ref="", target_path=f"06_المكتبة_البصرية/{ph}",
                license=lic.get(ph, "غير مفهرس — يُتحقق"), status="موجود" if (LIB / ph).exists() else "مفقود", gate="V5, V7")
        atlas_screens = []
        for c in ATLAS.get(wk, []):
            pat = "P20" if c.get("compare") else "P19"
            ids = [c["compare"]] if c.get("compare") else ([c["page"]] if c.get("page") else [pid for _, pid in c["stations"]])
            atlas_screens.append(dict(pattern=pat, pattern_name=PATTERNS[pat][0], what=c["prompt"], source="الأطلس: " + "، ".join(ids),
                                      data={k: v for k, v in c.items()}))
            for aid in ids:
                add(asset_id=f"tas-w{wk:02d}-atlas-{aid}", week=wk, unit=u, kind="صفحة أطلس", route=f"{pat} من منصة الأطالس",
                    description=c["prompt"], prompt_ref="atlas/00_مرشحو_الأطلس_لكل_أسبوع.md", target_path=f"index.html#{aid}",
                    license="أطالس منشورة (ردمك) — داخلي تعليمي فقط حتى إذن الناشر", status="مربوط", gate="V5, G12")
        imap.append(dict(week=wk, unit=u, phase=phase_of(u), title=w["title"], status=w["status"],
                         concept_svg=w["svg"] or None,
                         screens=[dict(pattern=p, pattern_name=PATTERNS[p][0], what=what, source=src)
                                  for p, what, src in w["ix"]] + atlas_screens,
                         hook_assets=[h[0] for h in w["hooks"]], authored_assets=[a[0] for a in w["authored"]],
                         library_photos=w["photos"]))

    for u in range(1, 9):
        aid = f"tas-u{u}-opener"
        add(asset_id=aid, week="", unit=u, kind="فيديو حركة", route="اختياري — HyperFrames/Remotion",
            description="افتتاحية صامتة 20–30ث: القلم يرسم مشجر الوحدة ثم تنزل طوبات الوحدة في العمود",
            prompt_ref="05 §الحركة", target_path=f"07_الهوية_البصرية_والتفاعل/assets/motion/{aid}.mp4",
            license="أصلي", status="اختياري", gate="V8")

    if errors:
        print("\n".join(errors)); sys.exit(1)

    for w in WEEKS:
        k = str(w["w"])
        if k not in lock or w["w"] in relock:
            lock[k] = fingerprint(UNIT_DIR.get(w["u"]), w["w"], w["svg"])
    json.dump(dict(note="Fingerprints the visual plan was reviewed against. Check with tools/check_drift.py; "
                        "accept edits with build_visual_plan.py --relock N.", weeks=lock),
              open(lock_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    fields = ["asset_id", "week", "unit", "kind", "route", "description", "prompt_ref", "target_path", "license", "status", "gate"]
    with open(PKG / "03_سجل_الأصول_البصرية.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)

    json.dump(dict(generated_by="tools/build_visual_plan.py — do not edit by hand",
                   patterns={k: dict(name=v[0], mechanic=v[1], origin=v[2]) for k, v in PATTERNS.items()},
                   weeks=imap), open(PKG / "interaction-map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    out = ["# برومبتات التوليد — رسوم الخطاف وأغلفة الوحدات", "",
           "> **ملف مولَّد** من `tools/visual_plan_data.py` بالأمر `python3 07_الهوية_البصرية_والتفاعل/tools/build_visual_plan.py`. لا تعدّله يدويًا.",
           "> اقرأ [`04_تعليمات_وكلاء_الذكاء_الاصطناعي.md`](04_تعليمات_وكلاء_الذكاء_الاصطناعي.md) قبل توليد أي صورة.", "",
           "## 1. لاحقة الأسلوب (تُلصق بعد كل برومبت كما هي)", "",
           "استبدل `{accent}` بلون المرحلة المكتوب تحت كل برومبت.", "", "```text", STYLE_SUFFIX, "```", "",
           "## 2. قائمة المنع (Negative prompt) إن كان المولد يدعمها", "", "```text",
           "text, letters, words, arabic script, calligraphy, numbers, logo, watermark, signature, face, facial features, portrait, "
           "prophet, halo, religious figure, crowd close-up, weapon, sword, blood, fire, explosion, flag, 3d render, photorealistic, "
           "gradient, neon, glow, lens flare, stock photo, clip art, emoji, cartoon mascot", "```", "",
           f"## 3. البرومبتات ({len(prompts)} صورة)", ""]
    for aid, ar, body, ph in prompts:
        out += [f"### `{aid}` — {ar}", "", f"لون المرحلة: {ACCENT[ph]}", "", "```text", body + " " + STYLE_SUFFIX.format(accent=ACCENT[ph]), "```", ""]
    out += ["## 4. الحركة (اختياري — بقرار المالك)", "",
            "افتتاحية لكل وحدة `tas-uN-opener` تُصنع **برمجيًا** (HyperFrames أو Remotion) من ملفات SVG، لا بمولد فيديو:", "",
            "1. ورقة الكراسة فارغة (0.5ث) ← 2. القلم الأزرق يرسم مشجر الوحدة خطًا خطًا (`stroke-dashoffset`، 8–12ث) ← "
            "3. يظهر سؤال الوحدة الجامع بخط الرقعة كنص حي (3ث) ← 4. تنزل أربع طوبات بلون المرحلة في صف الوحدة من العمود (2ث) ← 5. سكون 2ث.", "",
            "بلا موسيقى ملحمية، بلا صوت مولّد، بلا وجوه، 1920×1080، 30fps، مدة 20–30ث، ونسخة ثابتة (آخر إطار PNG) لمن يفضل تقليل الحركة.", ""]
    (PKG / "05_برومبتات_التوليد.md").write_text("\n".join(out), encoding="utf-8")
    # week map (human-readable view of interaction-map.json)
    wm = ["# خريطة الأسابيع — الشاشات والأنماط والأصول", "",
          "> **ملف مولَّد** من `tools/visual_plan_data.py`. لا تعدّله يدويًا. الأنماط مشروحة في `02_الخطة_البصرية_والتفاعلية.md` §3.",
          "> كل أسبوع يبدأ بشاشة L1 (الغلاف) وينتهي بـL6 (الدفتر) ثم L7 (القفلة)، ولا يُكرَّر ذلك في الجدول.", "",
          "| الأسبوع | الوحدة | العنوان | الحالة | المشجر الحالي | الأنماط بالترتيب | رسوم الخطاف | صور المكتبة |",
          "|---:|---:|---|---|---|---|---|---:|"]
    for w in imap:
        pats = "<br>".join(f"`{s['pattern']}` {s['pattern_name']}: {s['what']}" for s in w["screens"])
        u = ("تنفس" if w["unit"] in (0, 17, 26, 35) else "ختامي" if w["unit"] == 36
             else str(w["unit"]).translate(AR))
        wm.append(f"| {str(w['week']).translate(AR)} | {u} | {w['title']} | {w['status']} | {w['concept_svg'] or '—'} | {pats} | "
                  f"{'<br>'.join('`'+h+'`' for h in w['hook_assets']) or '—'} | {str(len(w['library_photos'])).translate(AR)} |")
    (PKG / "06_خريطة_الأسابيع.md").write_text("\n".join(wm) + "\n", encoding="utf-8")

    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"ok: {len(rows)} assets {kinds} · {len(imap)} weeks · {len(prompts)} prompts")


if __name__ == "__main__":
    main()
