"""Has the course text changed since the visuals were planned or built?

    python3 07_الهوية_البصرية_والتفاعل/tools/check_drift.py            # all weeks
    python3 07_الهوية_البصرية_والتفاعل/tools/check_drift.py 1 2 3 4    # only these weeks

For every drifted week it lists what to revisit: the plan row, the hook image prompt,
the restyled concept SVG and any built week page. Exits 1 if anything drifted.
Week pages carry "source_sha" in their JSON block; a page whose sha differs from the
current script section is stale.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sources import ROOT, UNITS, fingerprint  # noqa: E402
from visual_plan_data import WEEKS, UNIT_DIR  # noqa: E402

AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def built_pages():
    out = {}
    for page in UNITS.glob("*/04_التفاعلي/week-*.html"):
        m = re.search(r'<script type="application/json" id="week">(.*?)</script>', page.read_text(encoding="utf-8"), re.S)
        if m:
            data = json.loads(m.group(1))
            out[data.get("week")] = (page, data.get("source_sha"))
    return out


def main(argv):
    only = {int(a) for a in argv[1:]}
    lock = json.loads((HERE.parent / "source-lock.json").read_text(encoding="utf-8"))["weeks"]
    pages = built_pages()
    drift = 0
    for w in WEEKS:
        n = w["w"]
        if only and n not in only:
            continue
        now = fingerprint(UNIT_DIR.get(w["u"]), n, w["svg"])
        was = lock.get(str(n), {})
        notes = []
        if was.get("script_sha") != now["script_sha"]:
            notes.append("نص الأسبوع تغيّر → راجع صف الأسبوع في visual_plan_data.py (الأنماط والتغذية الراجعة)"
                         + (f"، وبرومبت الخطاف {', '.join(h[0] for h in w['hooks'])} إن تغيّرت القصة الافتتاحية" if w["hooks"] else ""))
        if was.get("svg_sha") != now["svg_sha"]:
            notes.append(f"المشجر {w['svg']} تغيّر → أعد مهمة A2 لهذا الأسبوع")
        if n in pages and pages[n][1] != now["script_sha"]:
            notes.append(f"صفحة الأسبوع {pages[n][0].relative_to(ROOT)} مبنية على نص أقدم → أعد مهمة B لهذا الأسبوع")
        if notes:
            drift += 1
            print(f"الأسبوع {str(n).translate(AR)} — {w['title']}")
            for x in notes:
                print("   ·", x)
    if not drift:
        print("ok: لا تغيير منذ آخر مراجعة" + (f" (الأسابيع {sorted(only)})" if only else ""))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
