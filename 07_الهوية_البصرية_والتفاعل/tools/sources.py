"""Fingerprints of the course text each week's visuals are built on.

The course is still being edited. Every visual decision (patterns, hook images, week pages)
is tied to a hash of the week's script section and its concept SVG, so an edit shows up as
drift instead of silently leaving stale visuals behind.
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "02_الوحدات_التعليمية"


def script_file(unit_dir):
    hits = sorted((UNITS / unit_dir / "01_الأصول_النصية").glob("10_session_scripts*.md"))
    return hits[0] if hits else None


def week_section(unit_dir, week):
    """The week's part of the session script: from its '# الأسبوع N' heading to the next '# '."""
    f = script_file(unit_dir)
    if f is None:
        return None, None
    text = f.read_text(encoding="utf-8")
    if "breathing" in f.name:
        return f, text
    m = re.search(rf"^# *(?:الأسبوع|أسبوع)\s*{week}\b[^\n]*\n", text, re.M)
    if not m:
        return f, None
    nxt = re.search(r"^# ", text[m.end():], re.M)
    return f, text[m.start(): m.end() + nxt.start() if nxt else len(text)]


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16] if s is not None else None


def fingerprint(unit_dir, week, svg_name):
    f, sec = week_section(unit_dir, week) if unit_dir else (None, None)
    svg = UNITS / unit_dir / "03_المواد_البصرية" / svg_name if unit_dir and svg_name else None
    return {
        "script": str(f.relative_to(ROOT)) if f else None,
        "script_sha": sha(sec),
        "svg_sha": sha(svg.read_text(encoding="utf-8")) if svg and svg.exists() else None,
    }
