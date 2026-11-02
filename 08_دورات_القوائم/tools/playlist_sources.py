#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared, deterministic view of the eleven registered playlist sources.

The legacy ``playlists.json`` registry is authoritative for titles, warnings and
short fingerprints, but its ``n`` field is not a safe episode key everywhere
(``ayman-tasees`` assigns 16 twice). ``check_lesson.py`` instead numbers sorted
Markdown files, or reads ``episode:`` front matter, or reads a leading number
from raw ``.txt`` filenames. This module reproduces exactly that mapping so the
RAG catalogue and generated lesson citations refer to the same episode numbers.

No source file is modified and no speaker, recording, edition or transcript is
verified here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / '08_دورات_القوائم'
REGISTRY = PKG / 'playlists.json'
AR = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
STAMP = re.compile(r'\*\*\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\([^)]*\)\*\*')
EPISODE_FRONT_MATTER = re.compile(r'^episode:\s*([٠-٩\d]+)', re.M)
HEADER_METHOD = re.compile(r'^\s*(?:-\s*)?(?:المصدر|transcript_source|source_file|extraction_method|source_type)\s*:\s*(.+)', re.I)
PDF_PAGE = re.compile(r'<!--\s*بداية صفحة PDF\s+[٠-٩\d]+')


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def source_dir(playlist: dict) -> Path:
    dirs = {(ROOT / item['file']).parent.resolve() for item in playlist['items']}
    if len(dirs) != 1:
        raise ValueError(f"{playlist['slug']}: sources are not in one directory")
    return dirs.pop()


def checker_episode_map(directory: Path) -> dict[str, int]:
    """Reproduce check_lesson.py's episode numbering for one source directory."""
    md = sorted(p for p in directory.glob('*.md') if p.name.lower() != 'readme.md')
    out: dict[str, int] = {}
    if md:
        for i, path in enumerate(md, 1):
            text = path.read_text(encoding='utf-8', errors='replace')
            match = EPISODE_FRONT_MATTER.search(text)
            key = int(match.group(1).translate(AR)) if match else i
            rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
            if key in out.values() or rel in out:
                raise ValueError(f'duplicate episode number {key} in {directory}')
            out[rel] = key
        return out
    for path in sorted(directory.glob('*.txt')):
        match = re.match(r'^(\d+)', path.name)
        if not match:
            continue
        key = int(match.group(1))
        rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
        if key in out.values() or rel in out:
            raise ValueError(f'duplicate text episode number {key} in {directory}')
        out[rel] = key
    if not out:
        raise ValueError(f'no numbered source files in {directory}')
    return out


def ordered_items(playlist: dict) -> list[dict]:
    """Registry items in the same episode order used by check_lesson.py."""
    directory = source_dir(playlist)
    keys = checker_episode_map(directory)
    by_path = {Path(item['file']).as_posix(): item for item in playlist['items']}
    missing = sorted(set(by_path) - set(keys))
    if missing:
        raise ValueError(f"{playlist['slug']}: registry sources missing from disk: {missing[:3]}")
    # Some source folders also contain an index.md or README. check_lesson.py
    # may assign those an extra trailing episode number; ignore them as long as
    # they do not collide with a registered episode key.
    registered_keys = {by_path[p]['n'] for p in by_path}
    for path, key in keys.items():
        if path not in by_path and key in registered_keys:
            raise ValueError(f"{playlist['slug']}: unregistered source collides with episode {key}: {path}")
    rows = []
    for path, episode in sorted(keys.items(), key=lambda kv: kv[1]):
        if path not in by_path:
            continue
        item = by_path[path]
        rows.append(dict(item, path=path, episode=episode,
                         registry_episode=item['n'], source_dir=directory))
    return rows


def citation_kind(path: str) -> str:
    p = ROOT / path
    text = p.read_text(encoding='utf-8', errors='replace')
    if p.suffix.lower() == '.txt':
        return 'line'
    if STAMP.search(text):
        return 'timestamp'
    if PDF_PAGE.search(text):
        return 'pdf'
    return 'paragraph'


def header_method(path: str) -> str:
    lines = (ROOT / path).read_text(encoding='utf-8', errors='replace').splitlines()[:14]
    for line in lines:
        match = HEADER_METHOD.match(line)
        if match:
            return match.group(1).strip()[:180]
    return 'غير موثق في ترويسة الملف؛ يراجع من المصدر'


def catalog_rows():
    for playlist in registry()['playlists']:
        for item in ordered_items(playlist):
            yield playlist, item
