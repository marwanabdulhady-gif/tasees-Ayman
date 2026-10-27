#!/usr/bin/env python3
"""A4 — snapshots of the progress column for the four breathing/closing weeks.

    python3 07_الهوية_البصرية_والتفاعل/tools/build_column_snapshots.py

The column is drawn once, in `templates/column-progress.svg` (32 bricks + 2 breathing
rows + base/cap stones). These snapshots reuse that same drawing — they never redraw a
column — and only add: the `is-laid` state for the weeks finished by that point, the
stone bond of the finished phase, and one live Arabic caption.

Output (register `target_path`, hand-authored SVG — task A4):
  tas-w17-ix-column  · tas-w26-ix-column · tas-w35-ix-column · tas-w36-ix-column
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / "07_الهوية_البصرية_والتفاعل" / "templates" / "column-progress.svg"

U = "02_الوحدات_التعليمية"
TARGETS = {
    17: f"{U}/v0_4_تغليف_المرحلة_١_وأسبوع_التنفس_17/03_المواد_البصرية/interactive/tas-w17-ix-column.svg",
    26: f"{U}/v0_4_تغليف_المرحلة_٢_وأسبوع_التنفس_26/03_المواد_البصرية/interactive/tas-w26-ix-column.svg",
    35: f"{U}/v0_4_تغليف_المرحلة_٣_وأسبوع_التنفس_35/03_المواد_البصرية/interactive/tas-w35-ix-column.svg",
    36: f"{U}/v0_4_المشروع_الختامي_36_المحكمة_والمشروع_الشخصي/03_المواد_البصرية/interactive/tas-w36-ix-column.svg",
}

# The bond stones sit exactly on the breathing rows — those weeks *are* the bonds between
# phases. Phase 3 has no breathing row under unit 8, so its bond is the cap stone, lit up.
BOND = {
    1: ('<g class="bond"><title>الرباط الحجري الأول — إغلاق المرحلة ١</title>'
        '<path class="stone" d="M52,324 h196 M52,338 h196 M52,324 v14 M248,324 v14"/></g>'),
    2: ('<g class="bond"><title>الرباط الحجري الثاني — إغلاق المرحلة ٢</title>'
        '<path class="stone" d="M52,266 h196 M52,280 h196 M52,266 v14 M248,266 v14"/></g>'),
    3: ('<g class="bond"><title>الرباط الحجري الثالث — إضاءة تاج الختام</title>'
        '<path d="M46,218 h208 M54,218 q96.0,-26 192,0" fill="#2E7D57" fill-opacity="0.3" '
        'stroke="#2E7D57" stroke-width="2.4" stroke-linecap="round"/></g>'),
}
LAST_WEEK = {1: 17, 2: 26, 3: 35}
CAPTIONS = {
    17: "١٦ طوبة في العمود — المرحلة ١ مكتملة والرباط الأول في مكانه",
    26: "٢٤ طوبة ورباطان — المرحلة ٢ مكتملة",
    35: "٣٢ طوبة — المرحلة ٣ مكتملة والرباط الثالث مضاء",
    36: "العمود كامل: ٣٢ طوبة ورباطاتها الثلاثة — والجملة الأخيرة للقارئ",
}
WEEK_RE = re.compile(r'<g class="(brick|breath)([^"]*)"((?:[^>])*?)>(.*?)</g>', re.S)


def week_of(group_html):
    m = re.search(r'data-week="(\d+)"', group_html)
    return int(m.group(1)) if m else None


def snapshot(week, template):
    laid = set(range(1, week + 1))

    def repl(m):
        kind, extra, attrs, body = m.groups()
        w = week_of(attrs)
        if w is None or w not in laid:
            return m.group(0)
        body = body.replace("قيد الإنتاج", "مكتمل — صفحة الأسبوع جاهزة")
        if kind == "breath":
            body = body.replace("<title>أسبوع", "<title>مكتمل — أسبوع")
        cls = (kind + " is-laid " + extra.strip()).strip()
        return f'<g class="{cls}"{attrs}>{body}</g>'

    svg = WEEK_RE.sub(repl, template)

    # the bond of every phase this week has closed
    bonds = "".join(mark for phase, mark in BOND.items() if week >= LAST_WEEK[phase])
    svg = svg.replace('<text class="cap"', bonds + '\n<text class="cap"', 1)

    caption = CAPTIONS[week]
    svg = svg.replace("</svg>",
                      '<text class="cap" x="150.0" y="464" text-anchor="middle" '
                      f'style="font-size:11px">{caption}</text>\n</svg>')
    svg = svg.replace('viewBox="0 160 300 310"', 'viewBox="0 160 300 320"')
    return svg


def main():
    tpl = TPL.read_text(encoding="utf-8")
    wrote = 0
    for week, rel in TARGETS.items():
        out = ROOT / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(snapshot(week, tpl), encoding="utf-8")
        laid = len(re.findall(r'class="brick is-laid"', out.read_text(encoding="utf-8")))
        bonds = len(re.findall(r'class="stone"', out.read_text(encoding="utf-8")))
        print(f"✓ {rel.split('/')[-1]}: {laid} طوبة مكتملة · {bonds} حجر ربط")
        wrote += 1
    print(f"\nتم بناء {wrote} لقطة عمود")
    return 0


if __name__ == "__main__":
    sys.exit(main())
