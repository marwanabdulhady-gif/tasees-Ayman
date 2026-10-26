"""One command for every agent: runs all the repo checks and prints PASS or FAIL.

    python3 07_الهوية_البصرية_والتفاعل/tools/check_all.py             (everything)
    python3 07_الهوية_البصرية_والتفاعل/tools/check_all.py --week 18   (also open week 18 in the browser)

Run it before every commit. If the last line is not «PASS», do not commit: read the FAIL lines.
Rebuilding the generated files is part of the check — commit the files it rewrites.
"""
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ROOT = PKG.parent
T = PKG / "tools"
STEPS = [
    ("plan builds", ["python3", str(T / "build_visual_plan.py")]),
    ("atlas links", ["python3", str(T / "build_atlas_links.py")]),
    ("course text unchanged (drift)", ["python3", str(T / "check_drift.py")]),
    ("week pages up to date", ["python3", str(T / "build_week_pages.py"), "--check"]),
    ("playlist registry builds", ["python3", str(ROOT / "08_دورات_القوائم" / "tools" / "build_playlist_registry.py")]),
]


def browser_available():
    """Chromium من Playwright قد لا يكون قابلًا للتنزيل في بعض البيئات (بلا صلاحية root أو شبكة محجوبة)."""
    try:
        import subprocess as sp
        r = sp.run(["node", "-e", "require('playwright'); const {chromium}=require('playwright');"
                    "chromium.launch().then(b=>b.close()).then(()=>process.exit(0)).catch(()=>process.exit(1))"],
                   cwd=ROOT, capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def main(argv):
    steps = list(STEPS)
    if "--week" in argv:
        wk = argv[argv.index("--week") + 1]
        if browser_available():
            steps.append((f"week {wk} in the browser", ["node", str(T / "check_week_page.cjs"), wk]))
        else:
            # بديل موثّق: jsdom يشغّل الصفحة ويمشي على الشاشات — بلا لقطات ولا فحص عرض.
            print("ملاحظة: Chromium غير متاح هنا — فحص الصفحة يعمل بـjsdom (بلا لقطات).")
            steps.append((f"week {wk} in jsdom (بديل)", ["node", str(T / "check_week_page_dom.cjs"), wk]))
    failed = 0
    for name, cmd in steps:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip().splitlines()
        bad = r.returncode != 0 or any(l.startswith(("✗", "FAIL", "… ")) or "انحراف" in l for l in out)
        failed += bad
        print(("FAIL " if bad else "ok   ") + name)
        if bad:
            for l in out[-8:]:
                print("     " + l)
    print("PASS" if not failed else f"FAIL ({failed} step{'s' if failed > 1 else ''})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
