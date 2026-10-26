"""Gate V1 + V4 + V6 for restyled concept SVGs (task A2) and authored SVGs (task A4).

    python3 07_الهوية_البصرية_والتفاعل/tools/check_svg.py NEW.svg [ORIGINAL.svg]

Checks, and exits non-zero on any failure:
  V1  every hex colour in fill/stroke/style is in the palette (tokens.json, day + night + photo ink)
  V4  the SVG has live <text> (no text drawn as paths) and no embedded raster <image>
  V6  with ORIGINAL given: the multiset of text strings is identical (restyle may not change a word)
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

TOKENS = Path(__file__).resolve().parent.parent / "templates" / "tokens.json"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def palette():
    t = json.loads(TOKENS.read_text(encoding="utf-8"))
    cols = set()
    for theme in ("day", "night"):
        cols |= {v.lower() for v in t["color"][theme].values()}
    cols |= {v.lower() for k, v in t["color"]["photo_ink"].items() if k.startswith("phase")}
    return cols | {"#ffffff", "#fff"}


def texts(path):
    root = ET.parse(path).getroot()
    out = []
    for el in root.iter():
        if el.tag.split("}")[-1] in ("text", "tspan") and el.text and el.text.strip():
            out.append(" ".join(el.text.split()))
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    new = Path(argv[1])
    raw = new.read_text(encoding="utf-8")
    fails = []

    allowed = palette()
    bad = sorted({h.lower() for h in HEX.findall(raw)} - allowed)
    if bad:
        fails.append(f"V1 colours outside the palette: {', '.join(bad)}")

    if "<image" in raw:
        fails.append("V4 embedded <image> found — concept SVGs carry no raster")
    if not texts(new):
        fails.append("V4 no live <text> found — Arabic must stay editable text")

    if len(argv) > 2:
        a, b = Counter(texts(argv[2])), Counter(texts(new))
        if a != b:
            missing = list((a - b).elements())[:5]
            added = list((b - a).elements())[:5]
            fails.append(f"V6 text changed. missing: {missing} · added: {added}")

    for f in fails:
        print("FAIL", f)
    if not fails:
        print(f"ok {new.name}: {len(texts(new))} text nodes, palette clean" + (", text identical to original" if len(argv) > 2 else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
