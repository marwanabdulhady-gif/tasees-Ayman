"""Checks one playlist course against its episodes. Run before every commit (task D).

    python3 08_دورات_القوائم/tools/check_playlist_course.py <slug>
    python3 08_دورات_القوائم/tools/check_playlist_course.py <slug> --map other.json   (check another map file)

Reads <slug>/00_خريطة_الدورة.json and playlists.json. Fails (exit 1) if:
  · (status «للمراجعة» or «مكتملة») an episode is neither in a lesson nor in "excluded" with a reason
  · a lesson has fewer than 3 ideas, or fewer than 2 interactive patterns besides P14/P15
  · an idea cites an episode outside its lesson, or a citation cannot be found:
      timestamp "mm:ss"  → the episode must have a stamp within ±90 s
      paragraph "¶N"     → N must exist; and a "quote", if given, must appear in that paragraph
      line "L12" or "L12-L14" → original lines, exact quote and full source_sha256 required
      a "quote" is always searched in the episode text (spelling-normalised)
  · an atlas pick names a page, hotspot or comparison that the atlas manifest does not have
  · an episode changed since the course was built from it ("built_from" fingerprints)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ROOT = PKG.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_playlist_registry import body_of, norm, secs, TS  # noqa: E402

PATTERNS = {f"P{i:02d}" for i in range(1, 21)}


def squash(t):
    return re.sub(r"[^\w]+", " ", norm(t)).strip()


def check_line_citation(data, cite, quote, source_sha256):
    """Validate a literal quote against 1-based lines of the exact source bytes."""
    match = re.fullmatch(r"L([1-9]\d*)(?:-L([1-9]\d*))?", cite)
    if not match:
        raise ValueError("invalid line citation")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("line citation requires a full lowercase source_sha256")
    if hashlib.sha256(data).hexdigest() != source_sha256:
        raise ValueError("source_sha256 does not match source bytes")
    if not isinstance(quote, str) or not 3 <= len(quote.split()) <= 30:
        raise ValueError("line citation requires an exact quote of 3–30 words")
    lines = data.decode("utf-8").splitlines(keepends=True)
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start > end or end > len(lines) or end - start + 1 > 10:
        raise ValueError("invalid or overlong source line range")
    if quote not in "".join(lines[start - 1:end]):
        raise ValueError("exact quote not found in cited source lines")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    slug = argv[1]
    reg = {p["slug"]: p for p in json.loads((PKG / "playlists.json").read_text(encoding="utf-8"))["playlists"]}
    if slug not in reg:
        print(f"FAIL unknown slug {slug}; known: {', '.join(reg)}"); return 1
    map_path = Path(argv[argv.index("--map") + 1]) if "--map" in argv else PKG / reg[slug]["course_dir"] / "00_خريطة_الدورة.json"
    pl, cmap = reg[slug], json.loads(map_path.read_text(encoding="utf-8"))
    final = cmap.get("status") in ("للمراجعة", "مكتملة")
    eps = {e["n"]: e for e in pl["items"]}
    texts = {}

    def text(n):
        if n not in texts:
            texts[n] = body_of((ROOT / eps[n]["file"]).read_text(encoding="utf-8"))
        return texts[n]

    fails, notes = [], []
    lessons = cmap.get("lessons", [])
    if not lessons:
        print(f"ok {slug}: no lessons yet (status «{cmap.get('status', '')}») — nothing to check"); return 0

    covered = {n for l in lessons for n in l.get("episodes", [])}
    excluded = {x["ep"]: x.get("why", "") for x in cmap.get("excluded", [])}
    for n in eps:
        if n not in covered and n not in excluded:
            (fails if final else notes).append(f"episode {n} «{eps[n]['title'][:40]}» is in no lesson and not in \"excluded\"")
    for n, why in excluded.items():
        if not why.strip():
            fails.append(f"excluded episode {n} has no reason")
    for n in covered - set(eps):
        fails.append(f"lesson cites episode {n}, which does not exist")

    manifest = None
    for l in lessons:
        tag = f"lesson {l.get('n')}"
        ideas, pats = l.get("ideas", []), l.get("patterns", [])
        if len(ideas) < 3:
            fails.append(f"{tag}: {len(ideas)} ideas (need ≥ 3)")
        if len([p for p in pats if p not in ("P14", "P15")]) < 2:
            fails.append(f"{tag}: needs ≥ 2 interactive patterns besides P14/P15")
        for p in pats:
            if p not in PATTERNS:
                fails.append(f"{tag}: unknown pattern {p}")
        if len(l.get("episodes", [])) > 4:
            notes.append(f"{tag}: {len(l['episodes'])} episodes in one lesson — consider splitting")
        for i, idea in enumerate(ideas, 1):
            ep, cite, quote = idea.get("ep"), str(idea.get("cite", "")).strip(), idea.get("quote", "")
            where = f"{tag} idea {i}"
            if ep not in l.get("episodes", []):
                fails.append(f"{where}: cites episode {ep}, not one of this lesson's episodes"); continue
            if ep not in eps:
                continue
            body = text(ep)
            if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", cite):
                if not eps[ep]["timestamps"]:
                    fails.append(f"{where}: episode {ep} has no timestamps — cite ¶N instead")
                elif not any(abs(secs(s) - secs(cite)) <= 90 for s in TS.findall(body)):
                    fails.append(f"{where}: no stamp near {cite} in episode {ep}")
            elif re.fullmatch(r"L[1-9]\d*(?:-L[1-9]\d*)?", cite):
                try:
                    data = (ROOT / eps[ep]["file"]).read_bytes()
                    check_line_citation(data, cite, quote, idea.get("source_sha256"))
                    if hashlib.sha256(data).hexdigest()[:16] != eps[ep]["sha"]:
                        raise ValueError("episode registry is stale; rebuild it before checking")
                except (ValueError, OSError, UnicodeDecodeError) as exc:
                    fails.append(f"{where}: {exc}")
            elif re.fullmatch(r"¶\d+", cite):
                paras = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith("---")]
                k = int(cite[1:])
                if k < 1 or k > len(paras):
                    fails.append(f"{where}: {cite} but episode {ep} has {len(paras)} paragraphs")
                elif quote and squash(quote) not in squash(paras[k - 1]):
                    fails.append(f"{where}: quote not found in {cite} of episode {ep}")
            else:
                fails.append(f"{where}: cite «{cite}» is neither mm:ss, ¶N, nor L<n>[-L<n>]")
            if quote and not cite.startswith("L") and squash(quote) not in squash(body):
                fails.append(f"{where}: quote not found anywhere in episode {ep}")
        for pick in l.get("atlas", []):
            if manifest is None:
                manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
                pages = {p["id"]: p for p in manifest["pages"]}
                comps = {c["id"] for c in manifest.get("comparisons", [])}
            ids = ([pick["page"]] if pick.get("page") else []) + [pid for _, pid in pick.get("stations", [])]
            if pick.get("compare") and pick["compare"] not in comps:
                fails.append(f"{tag}: unknown atlas comparison {pick['compare']}")
            for pid in ids:
                if pid not in pages:
                    fails.append(f"{tag}: unknown atlas page {pid}"); continue
                hs = {h["id"] for h in pages[pid].get("hotspots") or []}
                for hid in pick.get("find", []):
                    if hid not in hs:
                        fails.append(f"{tag}: page {pid} has no hotspot {hid}")
        txt = l.get("text")
        if txt and not (PKG / reg[slug]["course_dir"] / txt).exists():
            fails.append(f"{tag}: lesson text {txt} does not exist")
        page = l.get("page")
        if page and not (PKG / reg[slug]["course_dir"] / page).exists():
            fails.append(f"{tag}: page file {page} does not exist")

    built = cmap.get("built_from", {})
    for n, sha in built.items():
        if int(n) in eps and eps[int(n)]["sha"] != sha:
            fails.append(f"episode {n} changed since the course was built from it — re-read it, then update built_from")

    for n in notes:
        print("note", n)
    for f in fails:
        print("FAIL", f)
    if not fails:
        print(f"ok {slug}: {len(lessons)} lessons cover {len(covered & set(eps))}/{len(eps)} episodes"
              + (f" ({len(excluded)} excluded with reasons)" if excluded else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
