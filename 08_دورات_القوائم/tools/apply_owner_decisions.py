#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Propagate the recorded owner approval into legacy status fields.

    python3 08_دورات_القوائم/tools/apply_owner_decisions.py
    python3 08_دورات_القوائم/tools/apply_owner_decisions.py --check

This is the deterministic bridge for older, hand-maintained files that the
newer course generators do not rewrite: legacy short drafts, ``course.json``
lesson statuses and official structural map notes. New lesson/screen/catalogue
files read ``owner_decisions.py`` directly. Approval is an owner decision; it
does not prove audio, speakers, editions, references or specialist review.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from owner_decisions import APPROVED_STATUS, LABELS, status  # noqa: E402

PKG = HERE.parent
MAP_STATUSES = {
    'خريطة': 'خريطة معتمدة من المالك',
    'نصوص بلا خريطة': 'نصوص بلا خريطة معتمدة من المالك',
    'لم تبدأ': 'لم تبدأ — معتمد من المالك',
}
LEGACY_DRAFT_LINE = re.compile(r'^> \*\*مسودة تعليمية للمراجعة، غير معتمدة\.\*\*.*$', re.M)
LEGACY_DRAFT_REPLACEMENT = (
    LABELS['draft_note'] + ' هذه إعادة صياغة تعليمية؛ أرقام السطور ليست توقيتات. '
    + LABELS['publication_note'] + ' ' + LABELS['verification_note']
)
MAP_NOTE_REPLACEMENT = (
    'تغطية أولية معتمدة من المالك؛ شواهد محدودة من تفريغات غير محققة لا تغني عن قراءة '
    'كاملة، والمتحدث والطبعة غير مؤكدين. أُضيف لكل درس نص بقالب المشروع وعشر شاشات '
    'تفاعلية مولّدة منه. ' + LABELS['publication_note'] + ' ' + LABELS['verification_note']
)


def _walk(value):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == 'text_status' and item == 'مسودة غير معتمدة':
                out[key] = status()
            elif key == 'status' and item in MAP_STATUSES:
                out[key] = MAP_STATUSES[item]
            elif key == 'status' and item in ('مسودة', 'مسودة — تحتاج مراجعة المالك'):
                out[key] = APPROVED_STATUS
            elif key == 'note' and isinstance(item, str) and 'مسودة تغطية أولية غير معتمدة' in item:
                out[key] = MAP_NOTE_REPLACEMENT
            else:
                out[key] = _walk(item)
        return out
    if isinstance(value, list):
        return [_walk(item) for item in value]
    return value


def build() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for path in sorted(PKG.rglob('course.json')) + sorted(PKG.rglob('00_خريطة_الدورة.json')):
        data = _walk(json.loads(path.read_text(encoding='utf-8')))
        out[path] = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    for path in sorted(PKG.rglob('*.md')):
        if '10_مسودات_القوائم' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        if LEGACY_DRAFT_LINE.search(text):
            out[path] = LEGACY_DRAFT_LINE.sub(lambda _m: LEGACY_DRAFT_REPLACEMENT, text)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare without writing')
    args = parser.parse_args(argv)
    generated = build()
    changed = [str(p.relative_to(PKG.parent)) for p, text in generated.items()
               if not p.exists() or p.read_text(encoding='utf-8') != text]
    if args.check:
        if changed:
            print('✗ حالة قرارات المالك تحتاج إعادة توليد:')
            for path in changed[:20]:
                print('  ' + path)
            if len(changed) > 20:
                print(f'  ... و{len(changed) - 20} ملفًا آخر')
            return 1
        print(f'ok: {len(generated)} ملف حالة مطابق لقرار المالك')
        return 0
    for p, text in generated.items():
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} owner-decision status files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
