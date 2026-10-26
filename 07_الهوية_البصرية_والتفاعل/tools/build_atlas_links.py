"""Connects the course weeks to the six-atlas platform at the repo root (index.html, data/manifest.json).

    python3 07_الهوية_البصرية_والتفاعل/tools/build_atlas_links.py

Writes (generated — never edit by hand):
  atlas/00_مرشحو_الأطلس_لكل_أسبوع.md   candidate atlas pages per week: places from the gazetteer that the
                                       week's script actually names, ranked, with deep links
  atlas/01_مرشحو_الأطلس_لكل_حلقة.md     the same, per episode, for the history playlists in 08_دورات_القوائم
  templates/atlas-course-bundle.js     window.TaseesAtlas — only the pages and comparisons chosen in
                                       visual_plan_data.ATLAS, with their verified hotspots (used by P19/P20)
Exits non-zero if a chosen page, hotspot or comparison does not exist in the atlas manifest.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sources import ROOT, week_section  # noqa: E402
from visual_plan_data import WEEKS, UNIT_DIR, ATLAS  # noqa: E402

PKG = HERE.parent
MANIFEST = ROOT / "data" / "manifest.json"
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
DIAC = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def norm(t):
    t = DIAC.sub("", t or "")
    t = re.sub("[أإآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه").replace("ﷺ", " ")
    return " " + re.sub(r"[^\w]+", " ", t).strip() + " "


def main():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pages = {p["id"]: p for p in m["pages"]}
    vols = {v["id"]: v for v in m["volumes"]}
    comps = {c["id"]: c for c in m.get("comparisons", [])}
    names = []
    for g in m["gazetteer"]:
        if "table-topic" in g["kinds"] and len(g["kinds"]) == 1:
            continue
        for v in {g["name"], *g.get("variants", [])}:
            n = norm(v)
            if len(n.strip()) >= 4 and len(n.split()) <= 5:
                names.append((n, g))

    out = ["# مرشحو الأطلس لكل أسبوع", "",
           "> **ملف مولَّد** من `tools/build_atlas_links.py`. لا تعدّله يدويًا.",
           "> لكل أسبوع: صفحات الأطالس الستة التي تذكر أماكنَ وردت **فعلًا** في نص الأسبوع (مطابقة مع الموسوعة الجغرافية للأطلس، 1,424 مدخلًا).",
           "> هذا ترشيح آلي لا اختيار: الوكيل يراجع الصفحة بعينه، ثم يضيف المختار إلى `ATLAS` في `visual_plan_data.py`. ✔ = مختار حاليًا.", ""]
    chosen_pages = {c["page"] for picks in ATLAS.values() for c in picks if c.get("page")} | \
                   {pid for picks in ATLAS.values() for c in picks for _, pid in c.get("stations", [])}
    for w in WEEKS:
        udir = UNIT_DIR.get(w["u"])
        _, sec = week_section(udir, w["w"]) if udir else (None, None)
        if not sec:
            continue
        text = norm(sec)
        hits = defaultdict(set)
        for n, g in names:
            if n in text:
                for o in g["occurrences"]:
                    hits[o["pageId"]].add(g["name"])
        ranked = sorted(((pid, nm) for pid, nm in hits.items() if pid in pages and pages[pid]["category"] in ("map", "spread-map", "photo-landmark")),
                        key=lambda x: (-len(x[1]), -len(pages[x[0]].get("hotspots") or []), x[0]))[:8]
        if not ranked:
            continue
        out += [f"## الأسبوع {str(w['w']).translate(AR)} — {w['title']}", "",
                "| | الصفحة | الأطلس · ص | العنوان | معالم محققة | الأماكن المذكورة في النص | الرابط |", "|---|---|---|---|---:|---|---|"]
        for pid, nm in ranked:
            p = pages[pid]
            out.append(f"| {'✔' if pid in chosen_pages else ''} | `{pid}` | {vols[p['volumeId']]['shortTitle']} · {str(p['printedPage']).translate(AR)} | {p['title']} | "
                       f"{str(len(p.get('hotspots') or [])).translate(AR)} | {'، '.join(sorted(nm)[:6])} | `index.html#{pid}` |")
        out.append("")
    (PKG / "atlas").mkdir(exist_ok=True)
    (PKG / "atlas" / "00_مرشحو_الأطلس_لكل_أسبوع.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    # per-episode candidates for the atlas-relevant playlists (08_دورات_القوائم/playlists.json)
    reg_path = ROOT / "08_دورات_القوائم" / "playlists.json"
    if reg_path.exists():
        ep_out = ["# مرشحو الأطلس لكل حلقة — دورات القوائم التاريخية", "",
                  "> **ملف مولَّد** من `07_الهوية_البصرية_والتفاعل/tools/build_atlas_links.py`. ترشيح آلي من أماكن ذُكرت في التفريغ (التفريغ آلي وفيه أخطاء سمعية) — يراجعه الوكيل بعينه.", ""]
        for pl in json.loads(reg_path.read_text(encoding="utf-8"))["playlists"]:
            if not pl.get("atlas"):
                continue
            ep_out += [f"## {pl['title']} (`{pl['slug']}`)", ""]
            for e in pl["items"]:
                text = norm((ROOT / e["file"]).read_text(encoding="utf-8"))
                hits = defaultdict(set)
                for n, g in names:
                    if n in text:
                        for o in g["occurrences"]:
                            hits[o["pageId"]].add(g["name"])
                top = sorted(((pid, nm) for pid, nm in hits.items() if pid in pages and pages[pid]["category"] in ("map", "spread-map")),
                             key=lambda x: (-len(x[1]), -len(pages[x[0]].get("hotspots") or []), x[0]))[:5]
                cells = "؛ ".join(f"`{pid}` {pages[pid]['title'][:45]} ({'، '.join(sorted(nm)[:4])})" for pid, nm in top) or "—"
                ep_out.append(f"- **الحلقة {e['n']}** — {e['title'][:70]}: {cells}")
            ep_out.append("")
        (PKG / "atlas" / "01_مرشحو_الأطلس_لكل_حلقة.md").write_text("\n".join(ep_out) + "\n", encoding="utf-8")

    # bundle of the chosen pages only
    errors, bp, bc = [], {}, {}
    for wk, picks in ATLAS.items():
        for c in picks:
            ids = ([c["page"]] if c.get("page") else []) + [pid for _, pid in c.get("stations", [])]
            if c.get("compare"):
                cmp = comps.get(c["compare"])
                if not cmp:
                    errors.append(f"week {wk}: unknown comparison {c['compare']}")
                    continue
                bc[cmp["id"]] = dict(title=cmp["title"], left=cmp["leftId"], right=cmp["rightId"],
                                     registered=cmp.get("mode") == "vector-registered", note=cmp.get("note", ""))
                ids += [cmp["leftId"], cmp["rightId"]]
            for pid in ids:
                p = pages.get(pid)
                if not p:
                    errors.append(f"week {wk}: unknown page {pid}")
                    continue
                hs = {h["id"]: h for h in p.get("hotspots") or []}
                for hid in c.get("find", []):
                    if hid not in hs:
                        errors.append(f"week {wk}: page {pid} has no hotspot {hid}")
                bp[pid] = dict(title=p["title"], volume=vols[p["volumeId"]]["shortTitle"], printed=p["printedPage"],
                               img=p["pageAsset"], w=p["width"], h=p["height"],
                               hotspots=[dict(id=h["id"], name=h["name"], kind=h.get("kind", ""), x=h["x"], y=h["y"], w=h["w"], h=h["h"],
                                              fact=h.get("fact", "")) for h in p.get("hotspots") or []])
    if errors:
        print("\n".join(errors)); sys.exit(1)
    js = ("/* Generated by tools/build_atlas_links.py — do not edit. Source: data/manifest.json (six-atlas platform).\n"
          "   Atlas page images are from published atlases (ISBN): internal educational use only (gate G12). */\n"
          "window.TaseesAtlas = " + json.dumps(dict(pages=bp, comparisons=bc), ensure_ascii=False, separators=(",", ":")) + ";\n")
    (PKG / "templates" / "atlas-course-bundle.js").write_text(js, encoding="utf-8")
    print(f"ok: {sum(1 for l in out if l.startswith('## '))} weeks with candidates · bundle {len(bp)} pages, {len(bc)} comparisons, "
          f"{sum(len(p['hotspots']) for p in bp.values())} hotspots")


if __name__ == "__main__":
    main()
