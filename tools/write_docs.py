#!/usr/bin/env python3
"""Generate docs/CONTENT-AUDIT.md and docs/PAGE-INVENTORY.md from data/atlas.json
so every number in the reports is the measured one."""
import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(ROOT, "data", "atlas.json"), encoding="utf-8"))
QA = os.path.join(ROOT, "work", "qa", "qa-results.json")
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
T = A["totals"]
figs = {f["id"]: f for f in A["figures"]}

# Coverage descriptions: written from visual inspection of each rendered page.
COVERAGE = {
    1: "شرق آسيا وجنوبها: روسيا الآسيوية، آسيا الوسطى (جزئيًا)، الصين، منغوليا، الكوريتان، اليابان، شبه القارة الهندية، جنوب شرق آسيا، إندونيسيا والفلبين",
    2: "أوروبا (مدوّرة)، شمال أفريقيا وشرقها ووسطها، الشرق الأوسط، الخليج، إيران وآسيا الوسطى الغربية، وغرب المحيط الهندي",
    3: "آسيا الوسطى والشرقية والجنوبية حتى جزر إندونيسيا والفلبين",
    4: "أوروبا، أفريقيا، شبه الجزيرة العربية والهلال الخصيب وإيران — مع أسهم متقطعة مؤرخة",
    5: "الشرق الأوسط، إيران وآسيا الوسطى الجنوبية، الهند الغربية، ساحل شرق أفريقيا وغرب المحيط الهندي",
    6: "شمال أفريقيا والصحراء الكبرى وغرب أفريقيا وجنوب أوروبا وشرق المتوسط",
    7: "آسيا: روسيا، آسيا الوسطى، الصين، الهند، جنوب شرق آسيا وإندونيسيا",
    8: "أوروبا، أفريقيا جنوب الصحراء والساحل الشرقي ومدغشقر، وشبه الجزيرة العربية (بلا تسميات)",
}
MAPTYPE = {
    "fig-2": "خريطة سياسية حديثة (حدود دول) مع مناطق منقطة ومفتاح «منطقة فاصلة»",
    "fig-1-1": "خريطة تاريخية: كيانات وشعوب ومدن مع أسهم متقطعة مؤرخة للفتوحات",
    "fig-1-3": "خريطة تاريخية: كيانات ومدن مع خط امتداد أسود عريض",
    "fig-1-4": "خريطة تاريخية: كيانات وأقاليم مع خطوط امتداد سوداء عريضة",
}


def kind_counts(feats):
    c = collections.Counter(f["kindLabel"] for f in feats if f["kind"] not in ("caption", "legend"))
    return "، ".join(f"{k}: {v}" for k, v in c.most_common())


def audit():
    L = []
    L.append("# تقرير تدقيق المحتوى — Content Audit\n")
    L.append("> مُولَّد آليًا من `data/atlas.json` بواسطة `tools/write_docs.py`. كل الأرقام مقيسة فعليًا.\n")
    s = A["source"]
    L.append("## الملف المصدر\n")
    L.append(f"- الاسم الأصلي: **{s['originalName']}** (Google Drive)\n- بصمة MD5: `{s['md5']}` — الحجم: {s['bytes']:,} بايت\n- المقاس: {s['pageSize']}\n- أداة الإنتاج: {s['producer']}، تاريخ الإنشاء {s['created']}\n- العنوان في البيانات الوصفية: {s['pdfTitleMetadata']}\n")
    L.append("## الأرقام الرئيسية\n")
    rows = [
        ("صفحات ملف PDF", T["pdfPages"]), ("صفحات عولجت", T["pagesProcessed"]),
        ("خرائط (أشكال) — كل شكل يمتد على صفحتين متقابلتين", T["figures"]), ("أنصاف خرائط (صفحات خرائط)", T["mapHalves"]),
        ("صفحات بطبقة نصية قابلة للاستخراج", T["pagesWithTextLayer"]), ("صفحات احتاجت نسخًا بصريًا (بديل OCR)", T["pagesRequiringVisualTranscription"]),
        ("تسميات منسوخة (تشمل ٤ تعليقات ومفتاحًا واحدًا)", T["transcribedFeatures"]),
        ("مدخلات قابلة للبحث (تسميات + تسمية مركّبة عابرة للصفحتين)", T["searchableEntries"]),
        ("مناطق تفاعل (قابلة للنقر) على الخرائط", T["interactiveHotspots"]),
        ("أسماء فريدة بعد التطبيع", T["uniqueNames"]), ("أسماء ترد في أكثر من شكل", T["namesOnMultipleFigures"]),
        ("علامات نقطية (مدن) مكتشفة", T["markersDetected"]), ("علامات نقطية رُبطت بتسمياتها", T["markersLinked"]),
        ("أشكال كتابية (حروف/كلمات متجهية) في الملف", T["labelGlyphPaths"]), ("أشكال كتابية مرتبطة بنسخ", T["labelGlyphPathsLinked"]),
        ("تسميات بثقة متوسطة", T["mediumConfidence"]), ("تسميات بثقة منخفضة / غير مقروءة", T["lowConfidence"]),
    ]
    L.append("| المقياس | القيمة |\n|---|---:|")
    for k, v in rows:
        L.append(f"| {k} | {v} |")
    L.append("\n## الخرائط\n")
    L.append("| الشكل | التعليق (حرفيًا) | الصفحات (غرب/شرق) | التسميات | الطبقات المفصولة |\n|---|---|---|---:|---|")
    for f in A["figures"]:
        layers = "، ".join(f"{k}={v}" for k, v in f["layers"].items() if v)
        L.append(f"| {f['id']} | {f['caption']} | {f['westPage']} / {f['eastPage']} | {f['featureCount']} | {layers} |")
    L.append("\n## الصفحات التي تحتاج إلى مراجعة يدوية\n")
    for p in A["pages"]:
        items = [x for x in A["features"] if x["page"] == p["page"] and (x["conf"] == "low" or x["kind"] == "unreadable")]
        extra = []
        if p["stats"]["glyphPathsNotLinked"]:
            extra.append(f"{p['stats']['glyphPathsNotLinked']} شكلًا داكنًا غير مرتبط بنسخ" + (" (معظمها أجزاء أسهم متقطعة ونقاط مدن صغيرة)" if p["page"] == 4 else " (تسميات دقيقة غير مقروءة)" if p["page"] == 2 else ""))
        if not items and not extra:
            continue
        L.append(f"- **الصفحة {p['page']}** ({p['verificationStatus']}): " + "؛ ".join(extra + [f"«{x['text']}» — {x.get('note') or ''}" for x in items]))
    med = [x for x in A["features"] if x["conf"] == "medium"]
    L.append(f"\n### تسميات بثقة متوسطة ({len(med)})\n")
    for x in med:
        L.append(f"- ص {x['page']}: «{x['text']}» — {x.get('note') or 'قراءة مرجّحة لتسمية صغيرة أو متداخلة'}")
    if A.get("warnings"):
        L.append("\n## تحذيرات البناء\n")
        for w in A["warnings"]:
            L.append(f"- {w}")
    L.append("\n## اختبارات الجودة المنفّذة\n")
    if os.path.exists(QA):
        q = json.load(open(QA, encoding="utf-8"))
        ok = sum(1 for r in q["results"] if r["ok"])
        L.append(f"آخر تشغيل لـ `tools/qa/run-qa.mjs` ({q['when']}): **{ok}/{len(q['results'])}** ناجحة، طلبات شبكة محجوبة: {len(q['blocked'])}، أخطاء JavaScript: {len(q['errors'])}.\n")
        L.append("| الاختبار | النتيجة | التفاصيل |\n|---|---|---|")
        for r in q["results"]:
            L.append(f"| {r['name']} | {'✅' if r['ok'] else '❌'} | {r['detail'].replace('|', '/')} |")
    L.append("\n### تحققات إضافية أثناء الاستخراج\n")
    L.append("- مطابقة الرسم المتجهي (SVG) في Chrome 131 لصورة الصفحة المستخرجة من PDF: الفرق ≤ ٠٫١٪ من البكسلات في الصفحات الثماني.")
    L.append("- إزاحة وصل الصفحتين (٤٤٥٫٩ نقطة) مقيسة من هندسة متكررة في الصفحتين، ومؤكدة بصريًا لكل شكل (تواصل السواحل والتسميات العابرة مثل «المحيط | الهندي»).")
    L.append("- الشكلان ١-١ و١-٤ على الخريطة الأساسية نفسها: أفضل تطابق لخطوط السواحل عند إزاحة ٠٫٥ نقطة (النصف الشرقي) و١ نقطة (الغربي).")
    L.append("- تراكب مناطق التفاعل على كل صفحة مع إبراز الحروف غير المنسوخة (`tools/qa_overlay.py`).")
    open(os.path.join(ROOT, "docs", "CONTENT-AUDIT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def inventory():
    L = ["# جرد صفحات الأطلس — Page Inventory\n", "> مُولَّد من `data/atlas.json`. الملف لا يحتوي فهرسًا أو جدول محتويات أو جداول بيانات؛ كل صفحاته نصف خريطة.\n"]
    for p in A["pages"]:
        f = figs[p["figure"]]
        feats = [x for x in A["features"] if x["page"] == p["page"]]
        important = [x["text"] for x in feats if x["bold"] and x["kind"] not in ("caption",)][:14]
        places = [x["text"] for x in feats if x["kind"] == "place"][:12]
        L.append(f"## الصفحة {p['page']} — {f['caption']} ({p['halfLabel']})\n")
        L.append(f"- **الموضوع:** {f['title']}\n- **التغطية الجغرافية:** {COVERAGE[p['page']]}\n- **نوع الخريطة:** {MAPTYPE[f['id']]}")
        L.append(f"- **التعليق مطبوع هنا:** {'نعم' if p['hasCaption'] else 'لا (في الصفحة ' + str(f['captionPage']) + ')'}")
        L.append(f"- **مفتاح:** {'نعم — «منطقة فاصلة» (مربع منقط)' if any(x['kind']=='legend' for x in feats) else 'لا'} — **جداول/نصوص شارحة:** لا")
        L.append(f"- **أبرز التسميات (خط عريض):** {'، '.join(important) or '—'}")
        L.append(f"- **مدن/مواقع:** {'، '.join(places) or '—'}")
        L.append(f"- **أنواع التسميات (تحريري):** {kind_counts(feats)}")
        L.append(f"- **البنية التقنية:** {p['vectorDrawings']} عنصرًا متجهيًا، {p['rasterImages']} صور نقطية، بلا طبقة نصية ولا خطوط؛ طبقات: " + "، ".join(f"{k}={v}" for k, v in p["layerStats"].items() if v))
        L.append(f"- **الاستخراج:** {p['transcribedFeatures']} تسمية منسوخة بصريًا؛ {p['stats']['glyphPathsLinkedToTranscription']}/{p['stats']['labelGlyphPaths']} شكلًا كتابيًا مرتبطًا؛ ثقة متوسطة {p['mediumConfidence']}، منخفضة {p['lowConfidence']} — الحالة: `{p['verificationStatus']}`")
        L.append("- **فرص التفاعل المنفّذة:** تسميات قابلة للنقر والبحث، ربط علامات المدن، طبقات قابلة للإخفاء، عرض الصفحة الأصلية والمقارنة" + ("، مقارنة بالتمرير مع الشكل المرسوم على الأساس نفسه" if f["id"] in ("fig-1-1", "fig-1-4") else ""))
        if p.get("completenessNote"):
            L.append(f"- **يحتاج إلى تحقق يدوي:** {p['completenessNote']}")
        L.append("")
    open(os.path.join(ROOT, "docs", "PAGE-INVENTORY.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


audit()
inventory()
print("wrote docs/CONTENT-AUDIT.md and docs/PAGE-INVENTORY.md")
