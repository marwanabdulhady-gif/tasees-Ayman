#!/usr/bin/env python3
"""Generates docs/PAGE-INVENTORY.md from data/manifest.json for all 393 pages across the 3 atlases."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
manifest = json.load(open(os.path.join(ROOT, "data/manifest.json"), encoding="utf-8"))

CAT_AR = {
    "spread-map": "خريطة متجهية مزدوجة",
    "map": "خريطة جغرافية/تاريخية",
    "table-diagram": "جدول / شكل تنظيمي",
    "photo-landmark": "صورة / معلم أثري",
    "narrative-text": "سرد تاريخي ونصوص",
    "chapter-divider": "فاصل باب / فصل",
    "cover-frontmatter": "غلاف / مقدمات",
    "index-reference": "مراجع وفهارس",
}

VER_AR = {
    "verified": "محقق بصريًا ومصدريًا",
    "partially-verified": "محقق جزئيًا",
    "verified-title-ocr-body": "عنوان مفهرس محقق + نص OCR",
    "ocr-text": "نص مستخرج ضوئيًا (OCR)",
    "ocr-needs-review": "OCR منخفض الثقة (للمراجعة)",
}

lines = [
    "# الجرد الكامل لصفحات الأطالس الثلاثة (393 صفحة)",
    "",
    "يوثّق هذا الملف الجرد البنيوي الكامل لجميع صفحات ملفات PDF الثلاثة (دون أي حذف أو إسقاط لأي صفحة):",
    "- **المجلد الأول (`maps8`):** خرائط التاريخ الإسلامي مجمع — **8 صفحات** (4 خرائط مزدوجة متجهية).",
    "- **المجلد الثاني (`seerah`):** الأطلس التاريخي لسيرة الرسول ﷺ — **264 صفحة**.",
    "- **المجلد الثالث (`abubakr`):** أطلس الخليفة أبي بكر الصديق رضي الله عنه — **121 صفحة**.",
    "",
]

for vol in manifest["volumes"]:
    vid = vol["id"]
    vpages = [p for p in manifest["pages"] if p["volumeId"] == vid]
    lines.append(f"## {vol['title']} (`{vid}` — {len(vpages)} صفحة)")
    lines.append("")
    lines.append("| المعرّف | ص | العنوان الموثّق | التصنيف | حالة التحقيق | ثقة OCR | معالم تفاعلية |")
    lines.append("|---|---:|---|---|---|---:|---:|")
    for p in vpages:
        conf = f"{p['ocrConfidence']}%" if p["ocrConfidence"] is not None else "متجهي"
        hs_count = len(p.get("hotspots") or [])
        if vid == "maps8":
            # Feature count from description or vector hotspots
            hs_str = "متجهي مفصول"
        else:
            hs_str = str(hs_count) if hs_count else "—"
        title = p["title"].replace("|", "\\|")
        lines.append(
            f"| `{p['id']}` | {p['sourcePage']} | {title} | {CAT_AR.get(p['category'], p['category'])} | {VER_AR.get(p['verificationStatus'], p['verificationStatus'])} | {conf} | {hs_str} |"
        )
    lines.append("")

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
out_path = os.path.join(ROOT, "docs/PAGE-INVENTORY.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Wrote {out_path} ({len(lines)} lines)")
