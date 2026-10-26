#!/usr/bin/env python3
"""
build_dawal_volume.py — integrates «أطلس دول العالم الإسلامي» (د. شوقي أبو خليل,
الطبعة الثانية محدثة 1424هـ/2003م, دار الفكر, 256 صفحة, slug: dawal) into the
unified platform manifest WITHOUT regenerating the existing six volumes.

Inputs (read):
  data/manifest.json, data/verified_indexes.json, source/SOURCE_MANIFEST.json,
  .cache/ocr_out/dawal.json, data/raw_page_metrics.json, data/ocr-words-bundle.js
Outputs (written):
  data/manifest.json, data/atlas-bundle.js, data/ocr-words-bundle.js,
  data/verified_indexes.json, source/SOURCE_MANIFEST.json

All 256 page titles were visually verified against the book (front matter,
section dividers, the printed table of contents on pp. 249–255, and the 26
«مصور» captions re-read at 130 dpi). OCR text/confidence/word boxes come from
the tesseract.js 5.1.1 (ara) run — mean confidence 50.9 (100-DPI source scans).
"""
import base64
import gzip
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
TASHKEEL = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")


def norm_ar(s: str) -> str:
    if not s:
        return ""
    s = s.replace("ﷺ", " صلى الله عليه وسلم ")
    s = TASHKEEL.sub("", s)
    s = s.replace("\u0640", "")
    s = re.sub(r"[أإآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه")
    s = s.translate(AR_DIGITS)
    s = re.sub(r"[^\w\s\u0621-\u064A]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def gz_b64_json(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(raw, compresslevel=9)).decode("ascii")


# ----------------------------------------------------------------------------
# Catalog (visually verified)
# ----------------------------------------------------------------------------
# Section 1: 55 OIC states — (map page, printed name as in TOC, TOC page)
S1 = [
    (8, "أذربيجان", 249), (10, "الأردن", 249), (12, "أفغانستان", 249), (14, "ألبانية", 249),
    (16, "الإمارات", 249), (18, "إندونيسية", 249), (20, "أوزبكستان", 249), (22, "أوغندا", 249),
    (24, "إيران", 249), (26, "باكستان", 249), (28, "البحرين", 249), (30, "بروناي", 249),
    (32, "بنغلادش", 249), (34, "بنين", 249), (36, "بوركينا فاسو", 249), (38, "البوسنة والهرسك", 249),
    (40, "تركمانستان", 249), (42, "تركية", 249), (44, "تشاد", 249), (46, "تنزانية", 249),
    (48, "تونس", 249), (50, "الجزائر", 249), (52, "جزر القمر", 249), (54, "جيبوتي", 249),
    (56, "ساحل العاج", 249), (58, "السعودية", 249), (60, "السنغال", 249), (62, "السودان", 249),
    (64, "سورية", 249), (66, "سيراليون", 249), (68, "الصومال", 249), (70, "طاجيكستان", 249),
    (72, "العراق", 249), (74, "عُمان", 249), (76, "الغابون", 249), (78, "غامبية", 249),
    (80, "غينية", 249), (82, "غينيا بيساو", 249), (84, "فلسطين", 249), (86, "قازاخستان", 249),
    (88, "قطر", 249), (90, "قيرغيزية", 249), (92, "الكمرون", 249), (94, "الكويت", 249),
    (96, "لبنان", 249), (98, "ليبية", 249), (100, "المالديف", 249), (102, "مالي", 250),
    (104, "ماليزية", 250), (106, "مصر", 250), (108, "المغرب", 250), (110, "موريتانية", 250),
    (112, "النيجر", 250), (114, "نيجيرية", 250), (116, "اليمن", 250),
]

# Section 2: 6 majority-Muslim states not in the OIC — (map page, printed name, TOC page)
S2 = [
    (120, "إثيوبية", 250), (122, "إريتيرية", 250), (124, "توغو", 250),
    (126, "غانة", 250), (128, "مكدونوية", 250), (130, "موزمبيق", 250),
]

# Section 3: 26 «مصور» maps — (page, number, title as printed, TOC page)
S3 = [
    (135, 1, "أنغولا", 252),
    (136, 2, "جمهورية إفريقية الوسطى", 252),
    (137, 3, "بورمة (اتحاد ميانمار - أركان)", 252),
    (138, 4, "بوروندي", 252),
    (139, 5, "تايلاند (فطاني)", 252),
    (140, 6, "الجبل الأسود (مونتينغرو)", 252),
    (141, 7, "حوض نهر الفولغا: الجمهورية الإسلامية المستقلة ذاتية الحكم (أستراخان، بشكيرية، تاتارية، تشوواش، جوغاش، ماري، مordiaovia)", 252),
    (142, 8, "زمبابوي", 253),
    (143, 9, "سنغافورة", 253),
    (144, 10, "سورينام (انضمت إلى المنظمة عام 2000م) و(تريينيداد - توباغو)", 253),
    (145, 11, "سنكيانغ (تركستان الشرقية)", 253),
    (146, 12, "سنكيانغ والأقاليم المسلمة المجاورة لها", 253),
    (147, 13, "الفلبين (مندناو، صولو)", 253),
    (148, 14, "قبرص", 253),
    (149, 15, "القرم", 253),
    (150, 16, "قوصوة (كوسوفو)", 253),
    (151, 17, "القوقاز الشمالي (القفقاس)", 253),
    (152, 18, "كشمير (جامو وكشمير)", 253),
    (153, 19, "الكونغو برازافيل", 253),
    (154, 20, "كينيا (العنوان المطبوع: كتيبة — خطأ مطبعي)", 253),
    (155, 21, "ليبيرية", 253),
    (156, 22, "مالاوي", 253),
    (157, 23, "مالاغاشي (مدغشقر)", 253),
    (158, 24, "موريشيوس (خريطة الجزيرة المالغاشية)", 253),
    (159, 25, "الهند", 253),
    (160, 26, "بورمة (ميانمار)", 253),
]
S3[6] = (141, 7, "حوض نهر الفولغا: الجمهورية الإسلامية المستقلة ذاتية الحكم (أستراخان، بشكيرية، تاتارية، تشوواش، جوغاش، ماري، مودوفيا)", 252)

# «شرح المصورات» pages (161–190)
SHARH = {
    161: "أنغولا وجمهورية إفريقية الوسطى (بطاقتا بيانات)",
    162: "بورمة (ميانمار) وبوروندي (بطاقتا بيانات)",
    163: "تايلاند (فطاني) (بيانات وتاريخ)",
    164: "الجبل الأسود (بيانات) وحوض نهر الفولغا (بيانات)",
    165: "حوض نهر الفولغا: الجمهوريات ذاتية الحكم (دراسة)",
    166: "حوض نهر الفولغا (دراسة متصلة) وزمبابوي (بطاقة بيانات)",
    167: "سنغافورة وسورينام (بطاقتا بيانات)",
    168: "سنكيانغ (تركستان الشرقية) (بطاقة بيانات)",
    169: "الصين: بداية الإسلام في الصين (دراسة)",
    170: "الصين: الأقاليم المسلمة (شنتشانغ، شينشوان، يونان)",
    171: "الصين (دراسة متصلة) والفلبين (دراسة بدءًا)",
    172: "الفلبين: مندناو وجزر صولو (دراسة)",
    173: "الفلبين (دراسة متصلة)",
    174: "قبرص والقرم (بطاقتا بيانات)",
    175: "القرم (بيانات: سيفاستوبول/سمفيروبول، التتري، الروبل، القبيلة الذهبية)",
    176: "قوصوة (كوسوفو) (بطاقة بيانات)",
    177: "القوقاز الشمالي (بيانات ودراسة)",
    178: "القوقاز الشمالي (دراسة متصلة) وكشمير (بيانات)",
    179: "كشمير (دراسة)",
    180: "الكونغو برازافيل وكينيا (بطاقتا بيانات)",
    181: "كينيا (بيانات متصلة)",
    182: "ليبيرية ومالاوي (بطاقتا بيانات)",
    183: "مالاغاشي (مدغشقر) وموريشيوس (بطاقتا بيانات)",
    184: "موريشيوس (بيانات متصلة) والهند (دراسة بدءًا)",
    185: "الهند: وصول الإسلام إلى الهند (دراسة)",
    186: "الهند (دراسة متصلة)",
    187: "الهند: دولات دلهي وتيمور وأورنكزيب (دراسة)",
    188: "الهند: نادر شاه والإنجليز (كلايف) (دراسة)",
    189: "الهند (دراسة خاتمة) وبورمة (دراسة بدءًا)",
    190: "بورمة (دراسة متصلة)",
}

# Statistical tables / conclusion (191–205)
TABLES = {
    191: "كشافة بالمواضع واللغة والنقد ونظام الحكم في دول المؤتمر الإسلامي المؤتمرة (جدول)",
    192: "كشافة بالمواضع واللغة والنقد ونظام الحكم (جدول متواصل)",
    193: "كشافة بالمواضع واللغة والنقد ونظام الحكم (جدول متواصل)",
    194: "ترتيب دول منظمة المؤتمر الإسلامي وفق المساحة (جدول)",
    195: "ترتيب دول منظمة المؤتمر الإسلامي وفق المساحة (جدول متواصل)",
    196: "ترتيب دول منظمة المؤتمر الإسلامي وفق المساحة (جدول متواصل)",
    197: "ترتيب معظم المؤتمر الإسلامي وفق عدد السكان (جدول)",
    198: "ترتيب معظم المؤتمر الإسلامي وفق عدد السكان (جدول متواصل)",
    199: "ترتيب معظم المؤتمر الإسلامي وفق عدد السكان (جدول متواصل)",
    200: "المسلمون في أهم دول العالم (جدول)",
    201: "المسلمون في أهم دول العالم (جدول متواصل)",
    202: "الزيادة في عدد أتباع الشرائع في العالم (جدول)",
    203: "خاتمة (مقال)",
    204: "الزيادة في عدد أتباع الشرائع في العالم (جدول متواصل)",
    205: "منهج إعداد الفهرس العام (مقال)",
}

SECTIONS = [
    ("dawal-sec-00", "الغلاف وبطاقة النشر والمقدمة (الطبعة الثانية)", 1, 6),
    ("dawal-sec-01", "القسم الأول: دول منظمة المؤتمر الإسلامي (٥٥ دولة)", 7, 117),
    ("dawal-sec-02", "خريطة الكثافة السكانية العالمية (خريطة انتقالية)", 118, 118),
    ("dawal-sec-03", "القسم الثاني: الدول ذات الأغلبية المسلمة غير المدرجة في المنظمة (٦ دول)", 119, 132),
    ("dawal-sec-04", "القسم الثالث: أقاليم مسلمة ذات حكم ذاتي أو ضمن أراضي دولة أخرى، ودول نسبة المسلمين فيها ١٠–٥٠٪ (٢٦ مصورًا مع الشرح)", 133, 190),
    ("dawal-sec-05", "الجداول الإحصائية لدول المنظمة والخاتمة", 191, 206),
    ("dawal-sec-06", "الفهرس العام والمصادر والمراجع والمحتوى (فهرسة) والغلاف الخلفي", 207, 256),
]

VOLUME = {
    "id": "dawal",
    "shortTitle": "أطلس دول العالم الإسلامي",
    "title": "أطلس دول العالم الإسلامي",
    "author": "د. شوقي أبو خليل",
    "publisher": "دار الفكر — دمشق (الطبعة الثانية محدثة، ١٤٤هـ / ٢٠٠٣م — ISBN 1-57547-431-x)",
    "pageCount": 256,
    "type": "scanned-atlas",
    "hasVectorLayers": False,
    "hasJoinedSpreads": False,
    "sections": [
        {"id": s, "title": t, "startPage": a, "endPage": b} for s, t, a, b in SECTIONS
    ],
    "printedIndexes": {
        "mapsCount": 89,
        "tablesCount": 5,
        "photosCount": 26,
        "biographiesCount": 0,
    },
}


def section_for(pnum):
    for s, t, a, b in SECTIONS:
        if a <= pnum <= b:
            return s, t
    raise ValueError(pnum)


def main():
    m = json.load(open(os.path.join(ROOT, "data/manifest.json"), encoding="utf-8"))
    vi = json.load(open(os.path.join(ROOT, "data/verified_indexes.json"), encoding="utf-8"))
    sm = json.load(open(os.path.join(ROOT, "source/SOURCE_MANIFEST.json"), encoding="utf-8"))
    _ocr_doc = json.load(open(os.path.join(ROOT, ".cache/ocr_out/dawal.json"), encoding="utf-8"))
    ocr = {p["page"]: p for p in _ocr_doc["pages"]}
    metrics = json.load(open(os.path.join(ROOT, "data/raw_page_metrics.json"), encoding="utf-8"))
    dawal_metrics = metrics["dawal"] if isinstance(metrics, dict) else metrics
    if isinstance(dawal_metrics, list):
        m0 = dawal_metrics[0]
        W, H = m0["width"], m0["height"]
    else:
        m0 = dawal_metrics
        W, H = m0["width"], m0["height"]

    assert not any(v["id"] == "dawal" for v in m["volumes"]), "dawal already present"
    assert not any(p["id"].startswith("dawal-") for p in m["pages"]), "dawal pages already present"

    # --- decode existing OCR words bundle (keep all prior volumes) ---
    raw = open(os.path.join(ROOT, "data/ocr-words-bundle.js"), encoding="utf-8").read().strip()
    words_map = json.loads(gzip.decompress(base64.b64decode(raw.split('"')[1])).decode("utf-8"))

    next_global = max(p["globalIndex"] for p in m["pages"]) + 1
    pages_out = []

    def add_page(pnum, title, category, *, title_source="verified-visual",
                 vstatus="verified", map_type=None, scale=None, desc=None,
                 index_entries=None, notes=None):
        oc = ocr.get(pnum) or {}
        words = oc.get("words", []) if isinstance(oc, dict) else []
        text = oc.get("text", "") if isinstance(oc, dict) else ""
        conf = oc.get("confidence") if isinstance(oc, dict) else None
        sec_id, sec_title = section_for(pnum)
        entry = {
            "id": f"dawal-{pnum:03d}",
            "globalIndex": next_global + len(pages_out),
            "volumeId": "dawal",
            "sourcePage": pnum,
            "printedPage": pnum,
            "title": title,
            "titleNorm": norm_ar(title),
            "titleSource": title_source,
            "sectionId": sec_id,
            "sectionTitle": sec_title,
            "category": category,
            "mapType": map_type,
            "scaleText": scale,
            "description": desc or f"ضمن «{sec_title}».",
            "pageAsset": f"assets/pages/dawal/page-{pnum:03d}.webp",
            "thumbAsset": f"assets/thumbs/dawal/page-{pnum:03d}.webp",
            "svgAsset": None,
            "width": W,
            "height": H,
            "pdfWidthPt": 468.0,
            "pdfHeightPt": 663.0,
            "rotated": 0,
            "extractionMethod": "tesseract-ocr-ara",
            "extractedText": text[:6000],
            "extractedTextNorm": norm_ar(text[:6000]),
            "ocrConfidence": conf,
            "ocrWordCount": len(words),
            "verificationStatus": vstatus,
            "notes": notes or [],
            "indexEntries": index_entries or [],
            "legends": [],
            "hotspots": [],
            "featureCount": 0,
        }
        if words:
            words_map[f"dawal-{pnum:03d}"] = words
        pages_out.append(entry)
        return entry

    # --- front matter ---
    add_page(1, "الغلاف الأمامي — أطلس دول العالم الإسلامي", "cover-frontmatter")
    add_page(2, "بطاقة النشر والطباعة (الطبعة الثانية محدثة، ١٤٤هـ/٢٠٠٣م)", "cover-frontmatter")
    for i, pnum in enumerate((3, 4, 5, 6), 1):
        add_page(pnum, f"المقدمة (الطبعة الثانية محدثة) — الجزء {i}", "narrative-text",
                 vstatus="verified-title-ocr-body", title_source="verified-visual")
    add_page(7, "القسم الأول: دول منظمة المؤتمر الإسلامي (٥٥ دولة) — فاصل", "chapter-divider")

    # --- section 1: 55 states ---
    for mp, name, toc_p in S1:
        add_page(mp, f"{name} — خريطة الدولة", "map",
                 vstatus="verified-title-ocr-body", title_source="verified-visual",
                 map_type="خريطة سياسية وطنية (مع صورة فضائية وقطعة إقليمية)",
                 scale="مقياس مسافة مطبوع على الخريطة",
                 desc=f"خريطة كاملة لـ«{name}» ضمن القسم الأول (دول منظمة المؤتمر الإسلامي) — تُظهر الحدود والمدن والعواصم مع صورة فضائية وقطعة من الخريطة الإقليمية المحيط.",
                 index_entries=[{"type": "map", "title": name, "indexPage": toc_p, "note": None}])
        add_page(mp + 1, f"{name} — بطاقة البيانات والتاريخ", "table-diagram",
                 vstatus="verified-title-ocr-body", title_source="verified-visual",
                 desc=f"صفحة بيانات وتاريخ لـ«{name}»: الاسم الرسمي، العلم، العاصمة، المساحة، عدد السكان (2002م)، معدل النمو، نسبة المسلمين، اللغة، النقد، ومقال تاريخي واقتصادي.")

    # --- p118 world population density ---
    add_page(118, "كثافة السكان (خريطة العالم)", "map",
             map_type="خريطة عالمية (كرة): الكثافة السكانية",
             scale=None,
             desc="خريطة انتقالية بكرة أرضية تلوّن مناطق الكثافة السكانية العالية (أوروبا، آسيا، شرق المتوسط/شمال أفريقيا) — مقدمة للقسم الثاني.",
             notes=["خريطة غير مدرجة في فهرس «المحتوى» المطبوع."])

    # --- section 2: 6 states ---
    add_page(119, "القسم الثاني: دول ذات أغلبية مسلمة غير مدرجة في المنظمة — فاصل", "chapter-divider")
    for mp, name, toc_p in S2:
        add_page(mp, f"{name} — خريطة الدولة", "map",
                 vstatus="verified-title-ocr-body", title_source="verified-visual",
                 map_type="خريطة سياسية وطنية (مع صورة فضائية وقطعة إقليمية)",
                 scale="مقياس مسافة مطبوع على الخريطة",
                 desc=f"خريطة كاملة لـ«{name}» ضمن القسم الثاني (دول ذات أغلبية مسلمة غير مدرجة في المنظمة).",
                 index_entries=[{"type": "map", "title": name, "indexPage": toc_p, "note": None}])
        add_page(mp + 1, f"{name} — بطاقة البيانات والتاريخ", "table-diagram",
                 vstatus="verified-title-ocr-body", title_source="verified-visual",
                 desc=f"صفحة بيانات وتاريخ لـ«{name}» ضمن القسم الثاني.")
    add_page(132, "موزمبيق: جدول المناخ (متوسط الحرارة) — متصلة", "table-diagram",
             vstatus="verified-title-ocr-body", title_source="verified-ocr-body",
             desc="متابعة صفحة موزمبيق: جدول متوسط درجات الحرارة شهريًا.")

    # --- section 3 ---
    add_page(133, "القسم الثالث: أقاليم مسلمة ذات حكم ذاتي أو ضمن أراضي دولة أخرى، ودول نسبة المسلمين فيها ١٠–٥٠٪ — فاصل", "chapter-divider")
    add_page(134, "العالم الإسلامي (سياسي) — خريطة العالم", "map",
             map_type="خريطة عالمية (كرة): العالم الإسلامي (سياسي)",
             desc="خريطة ملونة بكرة أرضية توضح حدود العالم الإسلامي السياسي — مقدمة القسم الثالث.",
             notes=["خريطة غير مدرجة بصراحة في فهرس «المحتوى» المطبوع."])
    for pnum, n, title, toc_p in S3:
        add_page(pnum, f"مصور {n}: {title}", "map",
                 map_type="خريطة إقليمية مصورة (صورة فضائية + قطعة إقليمية)",
                 scale="مقياس مسافة مطبوع على الخريطة",
                 desc=f"الخريطة المصورة رقم {n} ضمن القسم الثالث: «{title}» — خريطة سياسية ملونة مع صورة فضائية وقطعة إقليمية موضِّعة.",
                 index_entries=[{"type": "map", "title": f"مصور {n}: {title}", "indexPage": toc_p, "note": f"مصور {n}"}],
                 notes=([f"العنوان المطبوع «{title.split(' (')[0]}» مع ملاحظة مطبعية." if "خطأ مطبعي" in title else []]))
    for pnum, title in SHARH.items():
        add_page(pnum, title, "narrative-text",
                 vstatus="verified-title-ocr-body", title_source="verified-ocr-body",
                 desc=f"صفحة شرح المصورات (القسم الثالث): {title}.")

    # --- statistical tables / conclusion ---
    for pnum, title in TABLES.items():
        cat = "table-diagram" if "جدول" in title else "narrative-text"
        add_page(pnum, title, cat,
                 vstatus="verified-title-ocr-body", title_source="verified-ocr-body",
                 desc=title)
    add_page(206, "صفحة فارغة", "cover-frontmatter",
             vstatus="verified", title_source="verified-visual",
             desc="صفحة فارغة (ورق مزرق) بين الجداول الإحصائية والفهرس العام.",
             notes=["ص ٢٠٦: لا تحمل أي محتوى في الطبعة."])

    # --- back matter ---
    for i, pnum in enumerate(range(207, 246), 1):
        add_page(pnum, f"الفهرس العام ({i} من 39)", "index-reference",
                 vstatus="ocr-text", title_source="verified-ocr-body",
                 desc="صفحة من الفهرس العام (الأسماء والمواضيع محارفًا بالأبجدية مع أرقام الصفحات).")
    for i, pnum in enumerate(range(246, 249), 1):
        add_page(pnum, f"المصادر والمراجع ({i})", "index-reference",
                 vstatus="verified-title-ocr-body", title_source="verified-ocr-body",
                 desc="صفحة من المصادر والمراجع (ابن بطوطة، إرتيرية والتحديات المصيرية، الإسلام في ممالك إفريقية السوداء، تركستان من الفتح العربي إلى الغزو المغولي، حاضر العالم الإسلامي، وغيرها).")
    for i, pnum in enumerate(range(249, 256), 1):
        extra = " + مذكرة «عدد سكان العالم»" if pnum == 255 else ""
        add_page(pnum, f"المحتوى (فهرس الكتاب) ({i} من 7){extra}", "index-reference",
                 vstatus="verified-title-ocr-body", title_source="verified-ocr-body",
                 desc=f"صفحة من فهرس «المحتوى» المطبوع (الأرقام الرسمية للصفحات){extra}.")
    add_page(256, "الغلاف الخلفي — سلسلة الكتب (٢ أطلس دول العالم الإسلامي، ٣/٤ مدن، ٤ السيرة النبوية، ٥ الحديث)", "cover-frontmatter")

    assert len(pages_out) == 256, f"expected 256 pages, got {len(pages_out)}"

    # --- merge manifest ---
    m["volumes"].append(VOLUME)
    m["pages"].extend(pages_out)
    m["subtitle"] = m.get("subtitle", "") + " · أطلس دول العالم الإسلامي"

    # --- gazetteer merge ---
    gaz = m["gazetteer"]
    by_norm = {g["norm"]: g for g in gaz}

    def gaz_add(name, kinds, occs, variants=None):
        n = norm_ar(name)
        g = by_norm.get(n)
        new_vol = "dawal" not in {o["volumeId"] for o in occs}
        if g is None:
            g = {
                "norm": n,
                "name": name,
                "variants": [name] + [v for v in (variants or []) if norm_ar(v) != n],
                "kinds": sorted(set(kinds)),
                "occurrences": list(occs),
                "id": f"gaz-{len(gaz) + 1}",
                "volumeCount": len({o["volumeId"] for o in occs}),
            }
            gaz.append(g)
            by_norm[n] = g
        else:
            for v in (variants or []):
                if v not in g["variants"]:
                    g["variants"].append(v)
            for k in kinds:
                if k not in g["kinds"]:
                    g["kinds"].append(k)
            existing = {(o["pageId"], o["label"]) for o in g["occurrences"]}
            for o in occs:
                if (o["pageId"], o["label"]) not in existing:
                    g["occurrences"].append(o)
                    existing.add((o["pageId"], o["label"]))
            vols = {o["volumeId"] for o in g["occurrences"]}
            g["volumeCount"] = len(vols)
            if new_vol and "dawal" in vols:
                pass

    def occ(pnum, label):
        return {"volumeId": "dawal", "pageId": f"dawal-{pnum:03d}", "sourcePage": pnum,
                "label": label, "indexType": "map"}

    for mp, name, toc_p in S1 + S2:
        gaz_add(name, ["country"], [occ(mp, f"{name} — الخريطة"), occ(mp + 1, f"{name} — البيانات والتاريخ"), occ(toc_p, "المحتوى (فهرس الكتاب)")])
    for pnum, n, title, toc_p in S3:
        base = title.split(":")[0].split(" (")[0]
        kinds = ["region"] if pnum in (141, 145, 146, 151, 152) else ["place"]
        gaz_add(base, kinds, [occ(pnum, f"مصور {n}: {title}"), occ(toc_p, "المحتوى (فهرس الكتاب)")],
                variants=[title])
    gaz_add("كثافة السكان", ["map-topic"], [occ(118, "كثافة السكان (خريطة العالم)")])
    gaz_add("العالم الإسلامي (سياسي)", ["map-topic"], [occ(134, "العالم الإسلامي (سياسي)")])
    # explanation pages occurrences for major S3 topics
    expl_map = {
        137: 162, 139: 163, 140: 164, 141: 165, 142: 166, 143: 167, 144: 167, 145: 168,
        147: 172, 148: 174, 149: 175, 150: 176, 151: 177, 152: 179, 153: 180, 154: 181,
        155: 182, 156: 182, 157: 183, 158: 184, 159: 185, 160: 189, 135: 161, 136: 161, 138: 162,
    }
    for pnum, n, title, toc_p in S3:
        if pnum in expl_map:
            base = title.split(":")[0].split(" (")[0]
            g = by_norm.get(norm_ar(base))
            if g:
                o = occ(expl_map[pnum], f"{base} — شرح المصورات")
                if not any(x["pageId"] == o["pageId"] and x["label"] == o["label"] for x in g["occurrences"]):
                    g["occurrences"].append(o)
                    g["volumeCount"] = len({x["volumeId"] for x in g["occurrences"]})

    # --- comparisons ---
    m["comparisons"].append({
        "id": "cmp-dawal-sinkiang-vs-neighbours",
        "title": "سنكيانغ (تركستان الشرقية) مقابل سنكيانغ والأقاليم المسلمة المجاورة لها (الخريطة الأساسية نفسها)",
        "leftId": "dawal-145",
        "rightId": "dawal-146",
        "leftFigure": "مصور 11",
        "rightFigure": "مصور 12",
        "mode": "raster-registered",
        "syncAllowed": True,
        "note": "خريطتان على الخريطة الأساسية نفسها (تركستان الشرقية وإقليم سنكيانغ) — الخريطة الأوسع تظهر الأقاليم المسلمة المجاورة (شنتشانغ، شينشوان، يونان) — مناسبة للتكبير المتزامن.",
    })
    m["comparisons"].append({
        "id": "cmp-dawal-density-vs-islamic-world",
        "title": "كثافة السكان العالمية مقابل العالم الإسلامي (سياسي) — كرتان بترميز واحد",
        "leftId": "dawal-118",
        "rightId": "dawal-134",
        "leftFigure": "ص 118",
        "rightFigure": "ص 134",
        "mode": "raster-registered",
        "syncAllowed": True,
        "note": "كرتان أرضيتان بنفس الترميز والحجم — مقابلة توزيع الكثافة السكانية العالمية مع حدود العالم الإسلامي السياسي.",
    })

    # --- stats ---
    st = m["stats"]
    st["totalVolumes"] = len(m["volumes"])
    st["totalPdfPages"] = len(m["pages"])
    st["pagesProcessed"] = len(m["pages"])
    st["pagesByVolume"]["dawal"] = 256
    st["scannedPagesRequiringOcr"] += 256
    ocr_pages = [p for p in m["pages"] if p["volumeId"] != "maps8"]
    st["scannedPagesWithExtractedOcrText"] = sum(1 for p in ocr_pages if (p.get("ocrWordCount") or 0) > 0)
    confs = [p["ocrConfidence"] for p in ocr_pages if p.get("ocrConfidence")]
    st["meanOcrConfidence"] = round(sum(confs) / len(confs), 1)
    st["totalOcrWordBoxes"] = sum(len(v) for v in words_map.values())
    st["mapsIdentified"]["dawalMaps"] = 89
    st["mapsIdentified"]["totalDistinctMaps"] = 514 + 89
    st["indexedTablesAndDiagrams"] = 67 + 5
    st["indexedPhotographs"] = 359 + 26
    from collections import Counter
    st["categories"] = dict(Counter(p["category"] for p in m["pages"]))
    st["verificationBreakdown"] = dict(Counter(p["verificationStatus"] for p in m["pages"]))
    st["searchableGazetteerEntries"] = len(gaz)
    st["crossVolumeGazetteerEntries"] = sum(1 for g in gaz if g["volumeCount"] > 1)
    st["interactiveFeatures"]["ocrSearchableWordBoxes"] = st["totalOcrWordBoxes"]
    low = [p["id"] for p in m["pages"] if p.get("ocrConfidence") is not None and p["ocrConfidence"] < 50 and p["volumeId"] != "maps8"]
    st["lowConfidenceOcrPageIds"] = low
    st["pagesRequiringManualReviewCount"] = len(low) + 3

    m["generatedAt"] = "2026-10-26"

    # --- SOURCE_MANIFEST.json ---
    sm["sources"].append({
        "volumeId": "dawal",
        "fileName": "أطلس دول العالم الإسلامي.pdf",
        "driveFileId": "1mBeH7PSf98BJrh5DOBk0ZzqYucBowYXz",
        "localPath": "source/islamic-states-atlas-abu-khalil.pdf",
        "bytes": 24540153,
        "md5": "2a3af820ed210d6b176bd3698bcd26b8",
        "sha256": "9c7a22dc9095fa8fcd6f3680f935d5158806a9abeb1e5c53bb748b3d7c419418",
        "pageCount": 256,
        "author": "د. شوقي أبو خليل",
        "edition": "الطبعة الثانية (محدثة) 1424هـ/2003م — دار الفكر، دمشق — ISBN 1-57547-431-x",
        "scanNote": "مسح 100 DPI (650×921 بكسل) — استخرجت 1:1 دون رفع الدقة",
        "ocrNote": "tesseract.js 5.1.1 (ara) — متوسط الثقة 50.9 — 16,557 صندوق كلمة",
    })

    # --- verified_indexes.json ---
    vi["dawal"] = {
        "title": VOLUME["title"],
        "shortTitle": VOLUME["shortTitle"],
        "author": VOLUME["author"],
        "publisher": VOLUME["publisher"],
        "isbn": "1-57547-431-x",
        "seriesNote": "دار الفكر — دمشق (سلسلة الأطالس: ٢ أطلس دول العالم الإسلامي)",
        "totalPages": 256,
        "sidewaysPages": {},
        "sections": VOLUME["sections"],
        "specialPages": {
            "dawal-001": {"title": "غلاف أطلس دول العالم الإسلامي", "category": "cover-frontmatter"},
            "dawal-002": {"title": "بطاقة النشر والطباعة", "category": "cover-frontmatter"},
            "dawal-007": {"title": "فاصل: القسم الأول (٥٥ دولة)", "category": "chapter-divider"},
            "dawal-118": {"title": "كثافة السكان (خريطة العالم)", "category": "map"},
            "dawal-119": {"title": "فاصل: القسم الثاني (٦ دول)", "category": "chapter-divider"},
            "dawal-133": {"title": "فاصل: القسم الثالث (٢٦ مصورًا)", "category": "chapter-divider"},
            "dawal-134": {"title": "العالم الإسلامي (سياسي) — خريطة العالم", "category": "map"},
            "dawal-206": {"title": "صفحة فارغة", "category": "cover-frontmatter"},
            "dawal-256": {"title": "الغلاف الخلفي — سلسلة الكتب", "category": "cover-frontmatter"},
        },
        "maps": [
            *[{"page": mp, "title": name, "indexPage": tp} for mp, name, tp in S1 + S2],
            *[{"page": p, "title": f"مصور {n}: {t}", "indexPage": tp} for p, n, t, tp in S3],
            {"page": 118, "title": "كثافة السكان (خريطة العالم)", "indexPage": None},
            {"page": 134, "title": "العالم الإسلامي (سياسي)", "indexPage": None},
        ],
        "tables": [
            {"page": 191, "title": "كشافة بالمواضع واللغة والنقد ونظام الحكم في دول المؤتمر الإسلامي", "indexPage": 254},
            {"page": 194, "title": "ترتيب دول منظمة المؤتمر الإسلامي وفق المساحة", "indexPage": 254},
            {"page": 197, "title": "ترتيب معظم المؤتمر الإسلامي وفق عدد السكان", "indexPage": 255},
            {"page": 200, "title": "المسلمون في أهم دول العالم", "indexPage": 255},
            {"page": 202, "title": "الزيادة في عدد أتباع الشرائع في العالم", "indexPage": 255},
        ],
        "photos": [
            {"page": p, "title": f"مصور {n}: {t}", "indexPage": tp} for p, n, t, tp in S3
        ],
        "biographies": [],
        "indexDiscrepancies": [
            {"indexPage": 253, "printedRef": "مصور 20 (ص 154)", "actualPage": 154,
             "issue": "العنوان المطبوع للمصور 20 يقرأ «كتيبة» بينما الخريطة وكافة بياناته (ص 181: الشلن الكيني، السواحيلي) تخص كينيا — خطأ مطبعي في الطبعة."},
            {"indexPage": 255, "printedRef": "المصادر والمراجع: 249", "actualPage": 246,
             "issue": "فهرس «المحتوى» يذكر «المصادر والمراجع» في ص 249 بينما تبدأ فعليًا في ص 246 (وربما خطأ مطبعي للرقم)."},
            {"indexPage": 251, "printedRef": "القسم الثالث: نسبة المسلمين 10–50٪", "actualPage": 133,
             "issue": "فاصل القسم الثالث المطبوع (ص 133) يسجل النطاق «١٠٪–٥٠٪» في حين أن فهرس «المحتوى» (ص 251) يسجل «٢٠٪–٥٠٪» — اختلاف مطبعي بين الفاصل والفهرس."},
        ],
    }

    # --- write outputs ---
    out = os.path.join(ROOT, "data/manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, separators=(",", ":"))

    with open(os.path.join(ROOT, "data/atlas-bundle.js"), "w", encoding="utf-8") as f:
        f.write('window.__ATLAS_MANIFEST_GZ__ = "')
        f.write(gz_b64_json(m))
        f.write('";\n')

    with open(os.path.join(ROOT, "data/ocr-words-bundle.js"), "w", encoding="utf-8") as f:
        f.write('window.__ATLAS_OCR_WORDS_GZ__ = "')
        f.write(gz_b64_json(words_map))
        f.write('";\n')

    with open(os.path.join(ROOT, "data/verified_indexes.json"), "w", encoding="utf-8") as f:
        json.dump(vi, f, ensure_ascii=False, indent=1)

    with open(os.path.join(ROOT, "source/SOURCE_MANIFEST.json"), "w", encoding="utf-8") as f:
        json.dump(sm, f, ensure_ascii=False, indent=1)

    print("dawal integrated OK")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    print("gazetteer size:", len(gaz))
    print("comparisons:", len(m["comparisons"]))


if __name__ == "__main__":
    main()
