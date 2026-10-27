#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""جرد تغطية قوائم أيمن في v0.4 — أي قائمة دخلت أي وحدة وأي أسبوع، وأي قائمة غائبة.

    python3 08_دورات_القوائم/tools/audit_v0_4_coverage.py
    python3 08_دورات_القوائم/tools/audit_v0_4_coverage.py --weeks    (يضيف خريطة الأسابيع ١–٣٦)

القاعدة: **الكاتالوج ≠ التغطية.** وجود القائمة في جدول كتالوج v0.4 لا يعني أنها دخلت
البناء. المصدر الوحيد للحكم هو سجل مصادر كل وحدة
`02_الوحدات_التعليمية/v0_4_*/01_الأصول_النصية/04_resource_registry_*module_NN*.csv`:
كل صف فيه = مادة دخلت وحدة فعلية في أسبوع محدَّد.

فك الإسناد:
  * معرّف الصف (M5V5-Q16 = وحدة ٥ إصدار v5 مادة Q16) يحمل الحرف الدال على الكوربس:
    Q ١٠٠ سؤال · H الأمويون والعباسيون · S السيرة المكية · L الوعي اللغوي ·
    Y رحلة اليقين · T تأسيس وعي المسلم المعاصر (وفي و1/و2 بالحرف T يراد به
    «إعادة تأسيس الوعي» — تمييزه بالمسار `05-reestablishing`) · AT أين الطريق.
  * بعض الصفوف كُتب معرّفها بحرف لا يطابق كوربسها (S في وحدة ٢ وهي من Q، وR في و1
    وهي من رحلة اليقين…) → تُفكّ من `OVERRIDES` أدناه بالمسار أو بالنص، لا بالتخمين.

الخرج: جدول القوائم (حلقات متاحة / صفوف / حلقات مذكورة / الوحدات / الأسابيع / الحكم)،
ثم خريطة الأسابيع ١–٣٦. يُخرج 1 إذا وُجدت قائمة بلا أي صف (فجوة كاملة).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "02_الوحدات_التعليمية"
PLAYLISTS = ROOT / "08_دورات_القوائم" / "playlists.json"

# صفوف معرّفها لا يطابق كوربسها — تُفكّ يدويًا وبمراجعة مسارها (لا تخمين)
OVERRIDES = {
    "M1V2-S01": ("AT", 0), "M1V2-S02": ("AT", 1), "M1V2-S03": ("AT", 4), "M1V2-S04": ("AT", 10),
    "M1V2-S05": ("ayman-tasees", 1),          # youtube_playlist_transcripts/001 — تأسيس مستوى ١/١
    "M1V2-S06": ("q100-history", 1), "M1V2-S07": ("q100-history", 2), "M1V2-S08": ("q100-history", 3),
    "M1V2-S09": ("rihlat-alyaqeen", 20),
    "M1V3-Q01": ("q100-history", 1), "M1V3-Q02": ("q100-history", 4),
    "M1V3-Q03": ("q100-history", 2),          # صف واحد لحلقتين (02 و03)
    "M1V3-R01": ("rihlat-alyaqeen", 1), "M1V3-R02": ("rihlat-alyaqeen", 20),
    "M1V3-T0201": ("ayman-linguistic-awareness", 1), "M1V3-T0202": ("ayman-linguistic-awareness", 2),
    "M1V3-T01": ("ayman-reestablishing-awareness", 1),
    "M1V4-S01": ("q100-history", 3),
    "M2V4-S01": ("AT", 10), "M2V4-S02": ("ayman-reestablishing-awareness", 41),
    "M2V4-S03": ("q100-history", 5), "M2V4-S04": ("q100-history", 6),
    "M2V4-S05": ("q100-history", 7), "M2V4-S06": ("q100-history", 8),
    "M3V4-AT11": ("AT", 11),
    "M8V8-L": ("ayman-linguistic-awareness", None),   # صف واحد للدورة كاملة ١–٩
}

PREFIX = {
    "Q": "q100-history", "H": "ayman-umayyad-abbasid", "S": "ayman-seerah-makkah",
    "L": "ayman-linguistic-awareness", "Y": "rihlat-alyaqeen", "T": "ayman-tasees",
}

AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
UNIT_LABEL = {f"{n:02d}": f"و{str(n).translate(AR)}" for n in range(1, 9)}


def ar(x) -> str:
    return str(x).translate(AR)


def load_rows():
    rows = []
    for f in sorted(UNITS.glob("v0_4_*/01_الأصول_النصية/04_resource_registry_*module_*.csv")):
        m = re.search(r"module_(\d\d)", f.name)
        unit = f"و{ar(int(m.group(1)))}" if m else "?"
        with f.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                r["_unit"] = unit
                r["_registry"] = f.name
                rows.append(r)
    return rows


def attribute(r):
    """(القائمة، رقم الحلقة أو None) لصف سجل واحد."""
    rid = (r.get("resource_id") or "").strip()
    src = " ".join((r.get(k) or "") for k in ("source_file_or_url", "verification_notes"))
    if rid in OVERRIDES:
        return OVERRIDES[rid]
    if "05-reestablishing" in src:
        m = re.search(r"-T(\d+)", rid)
        return "ayman-reestablishing-awareness", int(m.group(1)) if m else None
    if "02-linguistic" in src:
        m = re.search(r"-L(\d+)", rid) or re.search(r"/(\d{1,2})\s*[-–]", src)
        return "ayman-linguistic-awareness", int(m.group(1)) if m else None
    if "04-seerah" in src:
        m = re.search(r"-S(\d+)", rid)
        return "ayman-seerah-makkah", int(m.group(1)) if m else None
    if "01-umayyad" in src:
        m = re.search(r"-H(\d+)", rid)
        return "ayman-umayyad-abbasid", int(m.group(1)) if m else None
    if "100_سؤال" in src or "100_questions" in src:
        m = re.search(r"-Q(\d+)", rid) or re.search(r"/(\d{2})-", src)
        return "q100-history", int(m.group(1)) if m else None
    if "رحلة_اليقين" in src:
        m = re.search(r"-Y(\d+)", rid)
        return "rihlat-alyaqeen", int(m.group(1)) if m else None
    if "تأسيس_وعي" in src:
        m = re.search(r"-T(\d+)", rid)
        return "ayman-tasees", int(m.group(1)) if m else None
    if "ayn_al_tariq" in src or "أين_الطريق" in src:
        m = re.search(r"/(\d{1,2})\s*[-–]", src)
        return "AT", int(m.group(1)) if m else None
    m = re.match(r"M\d+V\d-([QHLSYT])(\d+)", rid)
    if m:
        pre, n = m.group(1), int(m.group(2))
        if pre == "T":
            # T في و1/و2 قد تكون «إعادة تأسيس»؛ ما وصل هنا بلا مسار يُعدّ تأسيسًا
            return "ayman-tasees", n
        return PREFIX[pre], n
    return None, None


def week_numbers(r):
    out = []
    for w in re.split(r"[,،/\s]+", r.get("week") or ""):
        if w.strip().isdigit():
            out.append(int(w))
    return out


def main(argv):
    rows = load_rows()
    pls = json.loads(PLAYLISTS.read_text(encoding="utf-8"))["playlists"]
    totals = {p["slug"]: len(p.get("items", [])) for p in pls}
    titles = {p["slug"]: p["title"] for p in pls}
    titles["AT"] = "أين الطريق؟ (كوربس — ليست في playlists.json)"

    agg = defaultdict(lambda: {"rows": 0, "eps": set(), "units": defaultdict(set), "weeks": set()})
    unattributed = []
    for r in rows:
        slug, ep = attribute(r)
        if not slug:
            unattributed.append(r)
            continue
        a = agg[slug]
        a["rows"] += 1
        if ep is not None:
            a["eps"].add(ep)
        for w in week_numbers(r):
            a["weeks"].add(w)
            a["units"][r["_unit"]].add(w)

    print(f"صفوف السجلات: {len(rows)} · مسندة إلى قائمة/كوربس: {len(rows) - len(unattributed)}"
          f" · غير مسندة (بصريات/أدوات/أهداف جلب): {len(unattributed)}\n")
    head = f"{'القائمة':34} {'حلقات':>6} {'صفوف':>5} {'مذكور':>6}  الوحدات · الأسابيع"
    print(head)
    print("-" * len(head))
    gaps = []
    for slug, total in totals.items():
        a = agg.get(slug)
        if not a:
            print(f"{slug:34} {ar(total):>6} {0:>5} {0:>6}  — غائبة تمامًا ✗")
            gaps.append(slug)
            continue
        eps = len([e for e in a["eps"] if e <= total]) if total else len(a["eps"])
        parts = []
        for u in sorted(a["units"]):
            ws = "، ".join(ar(w) for w in sorted(a["units"][u]))
            parts.append(f"{u}: {ws}")
        print(f"{slug:34} {ar(total):>6} {a['rows']:>5} {ar(eps):>6}  " + " · ".join(parts))
    at = agg.get("AT")
    if at:
        parts = [f"{u}: " + "، ".join(ar(w) for w in sorted(at['units'][u])) for u in sorted(at["units"])]
        print(f"{'AT (أين الطريق)':34} {'—':>6} {at['rows']:>5} {ar(len(at['eps'])):>6}  " + " · ".join(parts))

    if "--weeks" in argv:
        byweek = defaultdict(lambda: defaultdict(int))
        for r in rows:
            slug, _ = attribute(r)
            if not slug:
                continue
            for w in week_numbers(r):
                byweek[w][slug] += 1
        print("\nخريطة الأسابيع ١–٣٦ (عدد صفوف المصدر لكل قائمة):")
        for w in range(1, 37):
            d = byweek.get(w)
            if not d:
                print(f"  الأسبوع {ar(w):>2}: — (أسبوع تنفس/تغليف أو بلا مصدر من قائمة)")
                continue
            cells = " · ".join(f"{s}×{n}" for s, n in sorted(d.items(), key=lambda x: -x[1]))
            print(f"  الأسبوع {ar(w):>2}: {cells}")

    if unattributed:
        print("\nغير مسندة (ليست من قوائم أيمن — بصريات/أدوات/أهداف جلب موثقة):")
        cats = defaultdict(int)
        for r in unattributed:
            cats[r.get("category") or "?"] += 1
        print("  " + " · ".join(f"{k}: {v}" for k, v in sorted(cats.items(), key=lambda x: -x[1])))

    if gaps:
        print(f"\nفجوة: {', '.join(gaps)} — القائمة موجودة في الكتالوج وعلى القرص، وصفر صف في سجلات v0.4.")
        return 1
    print("\nok: كل قائمة في playlists.json دخلت v0.4 بسجل مصدر فعلي.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
