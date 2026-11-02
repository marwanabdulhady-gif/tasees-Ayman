#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the recorded owner-approval queue for the all-playlist course shelf.

    python3 08_دورات_القوائم/tools/build_review_queue.py
    python3 08_دورات_القوائم/tools/build_review_queue.py --check

The queue records the owner's final approval for every registered source,
lesson and generated screen, with the unresolved verification caveats kept
explicit. It records local byte/hash checks only; recording, speaker,
transcription, independent references and specialist review are not proven by
scripts. Publication inside the repository is approved; merging pull requests
and publishing outside it remain separate actions. No official course map is
changed.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from playlist_sources import PKG, ROOT, citation_kind, header_method, ordered_items, registry, source_dir  # noqa: E402
from owner_decisions import (APPROVED_STATUS, CAVEATS, DECISION_ID, EVIDENCE, LABELS,  # noqa: E402
                             PUBLICATION_STATUS, Q1_STATUS, REVIEWER, SHORT_STATUS,
                             VERIFICATION_STATUS, gate_for, status)

OUT = PKG / '10_مسودات_القوائم'
BOARD = OUT / '03_لوحة_المراجعة'
STATE = OUT / '00_حالة_القوائم.json'
CATALOG = ROOT / 'ayman_rag' / 'playlist_inventory.json'
AUDIT_MD = ROOT / 'ayman_rag' / 'playlist_retrieval_audit.md'
AUDIT_JSON = ROOT / 'ayman_rag' / 'playlist_retrieval_audit.json'
QUEUE_JSON = OUT / '00_طابور_المراجعة.json'
QUEUE_MD = OUT / '00_طابور_المراجعة.md'
SOURCE_LINK = re.compile(r'\[التفريغ النصي للحلقة [^\]]+\]\(([^)]+)\)')
SOURCE_ID = re.compile(r'معرّف المصدر `([^`]+)`')
QUOTE_CITE = re.compile(r'«[^»]+»\s*〔[^〕]+〕')

NOTE = (
    'طابور اعتماد موثق لرف الدروس: كل ملفات القوائم الإحدى عشرة وكل درس وشاشة '
    'يشملها قرار المالك. الفحص الآلي يثبت بايتات الملفات ومواضع الاقتباس فقط. '
    'التسجيل والمتحدث والمراجع والمراجعات المتخصصة قيود موثقة، لا نتائج فحص آلي. '
    'أُزيلت بوابة النشر داخل المستودع؛ دمج طلبات السحب والنشر الخارجي إجراء منفصل.'
)

BASE_REVIEWS = [
    'audio_recording_review',
    'speaker_attribution_review',
    'transcription_accuracy_review',
    'independent_reference_review',
    'content_accuracy_review',
    'official_map_approval',
    'owner_content_approval',
]
EXTRA_REVIEWS = {
    'ayman-psychology': ['clinical_safety_review', 'non_diagnosis_review'],
    'ayman-seerah-makkah': ['prophet_and_companions_respect_review', 'sectarian_neutrality_review'],
    'ayman-umayyad-abbasid': ['sectarian_neutrality_review', 'historical_sensitivity_review'],
    'ayman-reestablishing-awareness': ['contemporary_event_safety_review', 'historical_sensitivity_review'],
    'q100-history': ['presenter_attribution_review', 'historical_sensitivity_review', 'owner_q1_decision'],
    'rihlat-alyaqeen': ['presenter_attribution_review', 'theological_reference_review',
                        'scientific_reference_review', 'owner_q1_decision'],
    'ayn-al-tariq': ['pdf_original_verification', 'edition_and_attribution_review',
                     'owner_q1_decision'],
}
SAFETY_NOTES = {
    'ayman-psychology': 'لا تشخيص ولا نصيحة علاجية؛ التمارين عن فهم النص.',
    'ayman-seerah-makkah': 'بلا تجسيد للنبي ﷺ، مع أدب الصحابة وبلا ترجيح طائفي.',
    'ayman-umayyad-abbasid': 'بلا ترجيح طائفي ولا حكم على النيات.',
    'ayman-reestablishing-awareness': 'لا تحريض ولا اتهام لأشخاص أحياء ولا دعوة لفعل غير آمن.',
    'q100-history': 'لا نسبة تفصيلية للمقدّم أو الضيوف قبل توثيق الحلقات؛ قرار Q1 مثبّت بمرشد محايد بالاسم.',
    'rihlat-alyaqeen': 'محتوى عقدي يُنقل بسنده بلا حكم أو فتوى مضافة؛ قرار Q1 مثبّت بمرشد محايد بالاسم.',
    'ayn-al-tariq': 'نص مستخرج من PDF مرفق؛ تُعاد مطابقة الاقتباسات والصفحات مع الأصل قبل أي إسناد نهائي، بلا نسبة إلى أيمن.',
}
REVIEW_DIMENSIONS = [
    {'id': 'local_bytes_and_citation_positions', 'status': 'verified_local_only', 'automated': True,
     'claim': 'مطابقة SHA-256 ومواضع الاقتباس أمام البايتات الحالية فقط.'},
    {'id': 'audio_recording_review', 'status': VERIFICATION_STATUS, 'automated': False,
     'claim': 'قيد موثق: لم يُستمع إلى التسجيل آليًا ولم تُطابق الطوابع.'},
    {'id': 'speaker_attribution_review', 'status': VERIFICATION_STATUS, 'automated': False,
     'claim': 'قيد موثق: المتحدث/المقدّم/الضيوف غير متحققين آليًا.'},
    {'id': 'transcription_accuracy_review', 'status': VERIFICATION_STATUS, 'automated': False,
     'claim': 'قيد موثق: أخطاء التفريغ والطبعة والنسخ لم تُصحّح آليًا.'},
    {'id': 'independent_reference_review', 'status': VERIFICATION_STATUS, 'automated': False,
     'claim': 'قيد موثق: المراجع المستقلة للتاريخ والسيرة والعقيدة والعلوم والطب النفسي غير مراجعة آليًا.'},
    {'id': 'safety_and_red_lines_review', 'status': VERIFICATION_STATUS, 'automated': False,
     'claim': 'قيد موثق: الخطوط الحمراء الخاصة بكل قائمة محفوظة نصيًا، بلا مراجعة متخصصة آلية.'},
    {'id': 'voice_and_owner_q1', 'status': Q1_STATUS, 'automated': False,
     'claim': 'قرار المالك مثبّت: مرشد محايد بفصحى مبسطة مع النسبة بالاسم للقوائم الثلاث غير الأيمانية.'},
    {'id': 'official_map_approval', 'status': VERIFICATION_STATUS, 'automated': False,
     'claim': 'لا يُعدّل أي 00_خريطة_الدورة.json رسمي؛ الاعتماد على رف الدروس منفصل.'},
    {'id': 'owner_content_approval', 'status': PUBLICATION_STATUS, 'automated': False,
     'claim': 'قرار المالك باعتماد النصوص والشاشات موثق في 00_قرارات_المالك.json.'},
    {'id': 'publication', 'status': PUBLICATION_STATUS, 'automated': False,
     'claim': 'معتمد داخل المستودع؛ دمج طلبات السحب والنشر الخارجي إجراء منفصل.'},
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_review_status(voice: str | None = None) -> dict:
    return {
        'local_bytes': 'verified_local_only',
        'audio_recording': VERIFICATION_STATUS,
        'speaker_attribution': VERIFICATION_STATUS,
        'transcription_accuracy': VERIFICATION_STATUS,
        'independent_references': VERIFICATION_STATUS,
        'safety_context': VERIFICATION_STATUS,
        'voice_owner_gate': Q1_STATUS if voice == 'owner-decision' else PUBLICATION_STATUS,
        'owner_approval': PUBLICATION_STATUS,
        'publication': PUBLICATION_STATUS,
        'reviewer': REVIEWER,
        'decision': DECISION_ID,
        'evidence': EVIDENCE,
    }


def lesson_review_status(voice: str | None = None) -> dict:
    return {
        'draft_label': 'present',
        'citation_positions_and_source_hashes': 'verified_local_only',
        'screen_derived_from_lesson_text': 'verified_local_only',
        'content_accuracy': VERIFICATION_STATUS,
        'voice_and_attribution': Q1_STATUS if voice == 'owner-decision' else PUBLICATION_STATUS,
        'clinical_scientific_reference_review': VERIFICATION_STATUS,
        'official_map_approval': VERIFICATION_STATUS,
        'owner_approval': PUBLICATION_STATUS,
        'publication': PUBLICATION_STATUS,
        'reviewer': REVIEWER,
        'decision': DECISION_ID,
        'evidence': EVIDENCE,
    }


def _required_reviews(slug: str, voice: str) -> list[str]:
    reviews = list(BASE_REVIEWS) + list(EXTRA_REVIEWS.get(slug, []))
    if voice == 'owner-decision' and 'owner_q1_decision' not in reviews:
        reviews.append('owner_q1_decision')
    return reviews


def _documented_caveats(voice: str) -> list[str]:
    caveats = list(CAVEATS) + [
        'لم يُعدّل أي `00_خريطة_الدورة.json` رسمي؛ الدروس في رف منفصل معتمد من المالك.',
        'صفحات PDF في «أين الطريق؟» مستخرجة آليًا وتحتاج مطابقة مع الملف الأصلي.',
    ]
    if voice == 'owner-decision':
        caveats.insert(0, 'قرار Q1 مثبّت: مرشد محايد بفصحى مبسطة مع النسبة بالاسم، بلا صوت أيمن.')
    return caveats


def _playlist_entry(playlist: dict, state_row: dict, catalog: dict) -> dict:
    slug = playlist['slug']
    rows = ordered_items(playlist)
    reg_counts = Counter(r['registry_episode'] for r in rows)
    duplicate_eps = sorted(n for n, count in reg_counts.items() if count > 1)
    course = OUT / slug
    map_path = course / '00_خريطة_المسودة.json'
    draft_map = json.loads(map_path.read_text(encoding='utf-8'))
    if draft_map['status'] != status():
        raise ValueError(f'{slug}: draft map approval status changed')
    lessons_meta = draft_map['lessons']
    if len(lessons_meta) != state_row['lessons']:
        raise ValueError(f'{slug}: state/draft-map lesson count mismatch')

    sources = []
    sha_mismatches = []
    episode_mismatches = []
    for row in rows:
        doc = catalog.get(row['path'])
        if not doc:
            raise ValueError(f'{slug}: missing catalogue source {row["path"]}')
        prefix_ok = doc['sha256'].startswith(row.get('sha', '') or '\0')
        if not prefix_ok:
            sha_mismatches.append(row['path'])
        if row['registry_episode'] != row['episode']:
            episode_mismatches.append({'episode': row['episode'],
                                       'registry_episode': row['registry_episode'],
                                       'path': row['path']})
        flags = ['speaker_status_unverified', 'audio_recording_unverified']
        if row['registry_episode'] in duplicate_eps:
            flags.append('duplicate_registry_episode')
        if not prefix_ok:
            flags.append('registry_sha_prefix_mismatch')
        if playlist.get('voice') == 'owner-decision':
            flags.append('owner_q1_decided')
        flags += ['owner_approval_recorded', 'publication_approved']
        sources.append({
            'episode': row['episode'],
            'registry_episode': row['registry_episode'],
            'path': row['path'],
            'title': row['title'],
            'catalog_id': doc['id'],
            'sha256': doc['sha256'],
            'registry_sha_prefix': row.get('sha'),
            'registry_sha_prefix_ok': prefix_ok,
            'citation_kind': doc.get('citation_kind') or citation_kind(row['path']),
            'transcription_method': doc.get('transcription_method') or header_method(row['path']),
            'flags': flags,
            'review_status': source_review_status(playlist.get('voice')),
        })

    lessons = []
    for meta in lessons_meta:
        n = meta['n']
        rel_text = f'{slug}/01_نصوص_الدروس/lesson-{n:02d}.md'
        rel_screen = f'{slug}/02_الشاشات/lesson-{n:02d}.html'
        rel_map = f'{slug}/00_خريطة_المسودة.json'
        text_path = OUT / rel_text
        screen_path = OUT / rel_screen
        if not text_path.is_file() or not screen_path.is_file():
            raise ValueError(f'{slug}/lesson-{n:02d}: text or screen missing')
        text = text_path.read_text(encoding='utf-8')
        ids = SOURCE_ID.findall(text)
        citation_count = len(QUOTE_CITE.findall(text))
        if len(ids) != len(SOURCE_LINK.findall(text)) or not ids:
            raise ValueError(f'{slug}/lesson-{n:02d}: source metadata mismatch')
        lessons.append({
            'n': n,
            'episodes': meta['episodes'],
            'text': rel_text,
            'screen': rel_screen,
            'draft_map': rel_map,
            'text_sha256': _sha(text_path),
            'screen_sha256': _sha(screen_path),
            'source_ids': ids,
            'citation_count': citation_count,
            'review_status': lesson_review_status(playlist.get('voice')),
        })
    if len(lessons) * 10 != state_row['screens']:
        raise ValueError(f'{slug}: screen count mismatch')

    return {
        'slug': slug,
        'title': playlist['title'],
        'voice': playlist.get('voice'),
        'owner_gate': gate_for(playlist.get('voice')),
        'source_dir': str(source_dir(playlist).relative_to(ROOT)),
        'episodes': len(rows),
        'lessons': len(lessons),
        'screens': len(lessons) * 10,
        'citation': playlist.get('citation'),
        'required_reviews': _required_reviews(slug, playlist.get('voice')),
        'blocking_reasons': [],
        'documented_caveats': _documented_caveats(playlist.get('voice')),
        'safety_note': SAFETY_NOTES.get(slug, 'الخطوط الحمراء العامة للمشروع تسري على النص والشاشات معًا.'),
        'registry_integrity': {
            'duplicate_registry_episodes': duplicate_eps,
            'episode_order_mismatches': episode_mismatches,
            'registry_sha_prefix_mismatches': sha_mismatches,
        },
        'sources': sources,
        'lessons': lessons,
    }


def build() -> dict[Path, str]:
    state = json.loads(STATE.read_text(encoding='utf-8'))
    catalog_docs = json.loads(CATALOG.read_text(encoding='utf-8'))['documents']
    catalog = {d['path']: d for d in catalog_docs}
    registry_playlists = registry()['playlists']
    state_by_slug = {x['slug']: x for x in state['playlists']}
    entries = [_playlist_entry(p, state_by_slug[p['slug']], catalog) for p in registry_playlists]

    all_sources = sum(len(e['sources']) for e in entries)
    all_lessons = sum(len(e['lessons']) for e in entries)
    all_screens = sum(e['screens'] for e in entries)
    expected = state['totals']
    if (len(entries), all_sources, all_lessons, all_screens) != (
            expected['playlists'], expected['sources'], expected['lessons'], expected['screens']):
        raise ValueError('review queue totals do not match 00_حالة_القوائم.json')

    q1 = [e['slug'] for e in entries if e['voice'] == 'owner-decision']
    integrity = {
        'duplicate_registry_episode_playlists': [
            {'slug': e['slug'], 'episodes': e['registry_integrity']['duplicate_registry_episodes']}
            for e in entries if e['registry_integrity']['duplicate_registry_episodes']],
        'episode_order_mismatch_count': sum(
            len(e['registry_integrity']['episode_order_mismatches']) for e in entries),
        'registry_sha_prefix_mismatch_count': sum(
            len(e['registry_integrity']['registry_sha_prefix_mismatches']) for e in entries),
        'note': 'أرقام الحلقات المعتمدة في الكتالوج والمسودات هي ترقيم check_lesson.py لا حقل n في السجل.',
    }
    report = {
        'schema_version': 2,
        'status': LABELS['review_queue_title'],
        'note': NOTE,
        'generated_from': {
            'registry': '08_دورات_القوائم/playlists.json',
            'state': '08_دورات_القوائم/10_مسودات_القوائم/00_حالة_القوائم.json',
            'rag_catalog': 'ayman_rag/playlist_inventory.json',
            'rag_audit': 'ayman_rag/playlist_retrieval_audit.json',
            'catalog_sha256': hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        },
        'totals': {'playlists': len(entries), 'sources': all_sources,
                   'lessons': all_lessons, 'screens': all_screens,
                   'owner_accepted_source_reviews': all_sources,
                   'owner_accepted_lesson_reviews': all_lessons,
                   'approved_publications': all_lessons},
        'gates': {
            'owner_q1': {'status': Q1_STATUS, 'playlists': q1,
                         'decision': 'neutral_named', 'blocks': [],
                         'note': LABELS['q1_text']},
            'official_map_approval': {'status': VERIFICATION_STATUS, 'playlists': len(entries),
                                      'note': 'لا يُعدّل أي 00_خريطة_الدورة.json رسمي؛ الاعتماد على رف الدروس منفصل.'},
            'audio_and_speaker': {'status': VERIFICATION_STATUS, 'sources': all_sources},
            'references_and_safety': {'status': VERIFICATION_STATUS, 'sources': all_sources},
            'owner_content_approval': {'status': PUBLICATION_STATUS, 'lessons': all_lessons,
                                       'evidence': EVIDENCE},
            'publication': {'status': PUBLICATION_STATUS, 'lessons': all_lessons,
                            'screens': all_screens, 'note': LABELS['publication_note']},
        },
        'review_dimensions': REVIEW_DIMENSIONS,
        'registry_integrity': integrity,
        'playlists': entries,
        'limits': CAVEATS + [
            'التحقق الآلي محلي للبايتات ومواضع الاقتباس فقط.',
            'التغطية الهيكلية لا تعني قراءة شاملة ولا صحة محتوى.',
            'بدأت دروس «أين الطريق؟» بعد تثبيت قرار Q1؛ صفحات PDF تحتاج مطابقة مع الملف الأصلي.',
        ],
    }
    out: dict[Path, str] = {
        QUEUE_JSON: json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        QUEUE_MD: root_markdown(report),
        BOARD / 'index.html': dashboard(report),
    }
    for e in entries:
        out[OUT / e['slug'] / '00_طابور_المراجعة.md'] = playlist_markdown(e)
    return out


def root_markdown(report: dict) -> str:
    q1 = ', '.join(f'`{slug}`' for slug in report['gates']['owner_q1']['playlists'])
    lines = [
        LABELS['review_queue_title'],
        '',
        '> ' + NOTE,
        '',
        f'**{report["totals"]["playlists"]} قوائم · {report["totals"]["sources"]} ملف مصدر · '
        f'{report["totals"]["lessons"]} درسًا · {report["totals"]["screens"]} شاشة.** '
        f'قرار المالك بالاعتماد والنشر داخل المستودع موثق؛ قيود التحقق غير الثابتة آليًا '
        f'مصنّفة `{VERIFICATION_STATUS}`.',
        '',
        '| البوابة | الحالة | الأثر |',
        '|---|---|---|',
        f'| قرار المالك Q1 | {report["gates"]["owner_q1"]["status"]} | {q1} |',
        f'| الخرائط الرسمية | {report["gates"]["official_map_approval"]["status"]} | {report["gates"]["official_map_approval"]["playlists"]} قوائم، لم تُعدّل |',
        f'| التسجيل والمتحدث | {report["gates"]["audio_and_speaker"]["status"]} | {report["gates"]["audio_and_speaker"]["sources"]} ملفًا |',
        f'| المراجع والسلامة | {report["gates"]["references_and_safety"]["status"]} | {report["gates"]["references_and_safety"]["sources"]} ملفًا |',
        f'| اعتماد المالك للمحتوى | {report["gates"]["owner_content_approval"]["status"]} | {report["gates"]["owner_content_approval"]["lessons"]} درسًا |',
        f'| النشر داخل المستودع | {report["gates"]["publication"]["status"]} | {report["gates"]["publication"]["screens"]} شاشة |',
        '',
        '## أبعاد المراجعة', '',
        '| البعد | الحالة | آلي؟ | ما يثبته / ما ينتظره |', '|---|---|---|---|',
    ]
    for d in report['review_dimensions']:
        lines.append(f'| `{d["id"]}` | {d["status"]} | '
                     f'{"نعم" if d["automated"] else "لا"} | {d["claim"]} |')
    lines += ['', '## القوائم', '',
              '| القائمة | الملفات | الدروس | الشاشات | الصوت / البوابة | طابورها |',
              '|---|---:|---:|---:|---|---|']
    for e in report['playlists']:
        gate = e['owner_gate']
        lines.append(f'| [{e["title"]}]({e["slug"]}/README.md) | {e["episodes"]} | '
                     f'{len(e["lessons"])} | {e["screens"]} | {gate} | '
                     f'[طابور الاعتماد]({e["slug"]}/00_طابور_المراجعة.md) |')
    integ = report['registry_integrity']
    lines += ['', '## سلامة السجل', '',
              f'- قوائم فيها تكرار حقل `n`: '
              f'{len(integ["duplicate_registry_episode_playlists"])} '
              f'({", ".join(x["slug"] for x in integ["duplicate_registry_episode_playlists"]) or "لا شيء"}).',
              f'- اختلافات ترتيب الحلقات عن `check_lesson.py`: {integ["episode_order_mismatch_count"]}.',
              f'- بصمات `sha` قصيرة غير مطابقة للكتالوج: {integ["registry_sha_prefix_mismatch_count"]}.',
              '- ' + integ['note'], '',
              '## حدود', '']
    lines += [f'- {x}' for x in report['limits']]
    lines += ['', '## روابط وأوامر', '',
              '- [لوحة الاعتماد](03_لوحة_المراجعة/index.html) · '
              '[البيانات الكاملة](00_طابور_المراجعة.json) · '
              '[قرار المالك](../00_قرارات_المالك.md) · '
              '[فهرس الشاشات](index.html)',
              '- [تدقيق استرجاع RAG](../../ayman_rag/playlist_retrieval_audit.md) · '
              '[بيانات التدقيق](../../ayman_rag/playlist_retrieval_audit.json)', '',
              '```bash',
              'python3 ayman_rag/audit_playlist_retrieval.py --check',
              'python3 08_دورات_القوائم/tools/build_review_queue.py --check',
              'python3 08_دورات_القوائم/tools/build_playlist_course_drafts.py --check',
              'python3 08_دورات_القوائم/tools/build_playlist_course_screens.py --check',
              '```', '']
    return '\n'.join(lines)


def playlist_markdown(e: dict) -> str:
    lines = [
        f'# طابور اعتماد — {e["title"]}',
        '',
        '> **معتمد من المالك.** هذا طابور اعتماد لرف الدروس، لا خريطة رسمية. '
        f'النشر داخل المستودع `{PUBLICATION_STATUS}`، وقيود التحقق `{VERIFICATION_STATUS}`.',
        '',
        f'- القائمة: `{e["slug"]}`',
        f'- ملفات المصدر: {e["episodes"]} · الدروس: {len(e["lessons"])} · الشاشات: {e["screens"]}',
        f'- الصوت / البوابة: `{e["voice"]}` · {e["owner_gate"]}',
        f'- الإحالات: `{e["citation"]}`',
        f'- مجلد المصادر: `{e["source_dir"]}`',
        '',
        '## المراجعات المطلوبة', '',
    ]
    lines += [f'- `{r}` — {VERIFICATION_STATUS}' for r in e['required_reviews']]
    lines += ['', '## قيود موثقة', '']
    lines += [f'- {r}' for r in e['documented_caveats']]
    lines += ['', '## الخط الأحمر الخاص', '', e['safety_note'],
              '', '## سلامة السجل', '',
              f'- تكرار حقل `n`: {e["registry_integrity"]["duplicate_registry_episodes"] or "لا شيء"}',
              f'- اختلافات ترتيب الحلقات: {len(e["registry_integrity"]["episode_order_mismatches"])}',
              f'- بصمات قصيرة غير مطابقة: {len(e["registry_integrity"]["registry_sha_prefix_mismatches"])}',
              '', '## ملفات المصدر', '',
              '| حلقة | n في السجل | معرّف الكتالوج | SHA-256 (مختصر) | الإحالة | بصمة السجل | علامات | المراجعة |',
              '|---:|---:|---|---|---|---|---|---|']
    for s in e['sources']:
        lines.append(f'| {s["episode"]} | {s["registry_episode"]} | `{s["catalog_id"]}` | '
                     f'`{s["sha256"][:12]}` | {s["citation_kind"]} | '
                     f'{"✓" if s["registry_sha_prefix_ok"] else "✗"} | '
                     f'{", ".join(s["flags"])} | {PUBLICATION_STATUS} / {VERIFICATION_STATUS} |')
    lines += ['', '## الدروس والشاشات', '',
              '| الدرس | الحلقات | النص | الشاشة | اقتباسات | بصمة النص | بصمة الشاشة | المراجعة |',
              '|---:|---|---|---|---:|---|---|---|']
    for l in e['lessons']:
        eps = '، '.join(str(x) for x in l['episodes'])
        lines.append(f'| {l["n"]} | {eps} | [نص]({Path(l["text"]).name}) | '
                     f'[شاشات]({Path(l["screen"]).name}) | {l["citation_count"]} | '
                     f'`{l["text_sha256"][:12]}` | `{l["screen_sha256"][:12]}` | '
                     f'{PUBLICATION_STATUS} / {VERIFICATION_STATUS} |')
    lines += ['', '## حدود', '',
              LABELS['verification_note'] + ' الفحص الآلي يثبت مواضع الاقتباس وبصمات البايتات الحالية فقط.', '',
              '[الطابور الجذري](../00_طابور_المراجعة.md) · '
              '[لوحة الاعتماد](../03_لوحة_المراجعة/index.html) · '
              '[قرار المالك](../../00_قرارات_المالك.md) · '
              '[README القائمة](README.md)', '']
    return '\n'.join(lines)


def dashboard(report: dict) -> str:
    esc = html.escape
    rows = []
    for e in report['playlists']:
        gate = 'Q1 مثبّت' if e['voice'] == 'owner-decision' else SHORT_STATUS
        rows.append(
            '<tr>'
            f'<td><a href="../{esc(e["slug"])}/README.md">{esc(e["title"])}</a><br>'
            f'<code>{esc(e["slug"])}</code></td>'
            f'<td>{e["episodes"]}</td><td>{len(e["lessons"])}</td><td>{e["screens"]}</td>'
            f'<td><span class="badge">{gate}</span></td>'
            f'<td>{len(e["required_reviews"])}</td>'
            f'<td><a href="../{esc(e["slug"])}/00_طابور_المراجعة.md">الطابور</a> · '
            f'<a href="../{esc(e["slug"])}/02_الشاشات/index.html">الشاشات</a></td>'
            '</tr>')
    t = report['totals']
    css = '''
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 2rem 1rem 4rem; background: var(--paper); color: var(--ink);
           font-family: var(--f-body); line-height: 1.7; }
    main { max-width: var(--stage-max); margin: 0 auto; }
    h1 { font-family: var(--f-display); font-size: var(--t-h2); margin: 0 0 .5rem; }
    h2 { font-size: 1.3rem; margin: 2rem 0 .75rem; }
    p.lead { color: var(--ink-soft); max-width: 70ch; }
    .note { background: var(--wash-blue); border-inline-start: 4px solid var(--pen-blue);
            padding: 1rem; margin: 1.5rem 0; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; }
    .card { background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
            padding: 1rem; }
    .card strong { display: block; font-size: 1.8rem; color: var(--pen-blue); }
    .card span { color: var(--ink-soft); font-size: var(--t-small); }
    table { width: 100%; border-collapse: collapse; background: var(--card);
            border: 1px solid var(--rule); }
    th, td { padding: .65rem .75rem; border-bottom: 1px solid var(--rule); text-align: start;
             vertical-align: top; font-size: var(--t-small); }
    th { background: var(--wash-blue); }
    code { font-size: .85em; color: var(--ink-soft); }
    a { color: var(--pen-blue); }
    .badge { display: inline-block; background: var(--wash-blue); color: var(--pen-blue);
             border: 1px solid var(--pen-blue); border-radius: var(--radius);
             padding: .1rem .45rem; font-size: var(--t-tag); }
    ul { color: var(--ink-soft); }
    '''
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(LABELS['dashboard_title'])}</title>
<link rel="stylesheet" href="../../../07_الهوية_البصرية_والتفاعل/templates/tasees-tokens.css">
<style>{css}</style>
</head>
<body>
<main>
  <h1>{esc(LABELS['dashboard_title'])}</h1>
  <p class="lead">{esc(NOTE)}</p>
  <div class="note"><strong>قرار المالك موثق.</strong> النشر داخل المستودع
  <code>{PUBLICATION_STATUS}</code>؛ والتسجيل والمتحدث والمراجع والمراجعات المتخصصة
  <code>{VERIFICATION_STATUS}</code>. الخرائط الرسمية
  <code>00_خريطة_الدورة.json</code> لم تُعدّل.</div>
  <div class="cards">
    <div class="card"><strong>{t['playlists']}</strong><span>قوائم مسجلة</span></div>
    <div class="card"><strong>{t['sources']}</strong><span>ملفات مصدر</span></div>
    <div class="card"><strong>{t['lessons']}</strong><span>دروس معتمدة</span></div>
    <div class="card"><strong>{t['screens']}</strong><span>شاشات مولّدة</span></div>
    <div class="card"><strong>{t['owner_accepted_source_reviews']}</strong><span>مصادر بقيود موثقة</span></div>
    <div class="card"><strong>{t['approved_publications']}</strong><span>دروس معتمدة للنشر</span></div>
  </div>
  <h2>القوائم ({t['playlists']})</h2>
  <table>
    <thead><tr><th>القائمة</th><th>الملفات</th><th>الدروس</th><th>الشاشات</th>
    <th>القرار</th><th>قيود موثقة</th><th>روابط</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>القرار والقيود الموثقة</h2>
  <ul>
    <li>قرار المالك Q1: <code>{esc(', '.join(report['gates']['owner_q1']['playlists']))}</code> — {Q1_STATUS}.</li>
    <li>الخرائط الرسمية: {report['gates']['official_map_approval']['playlists']} قوائم — {VERIFICATION_STATUS}، لم تُعدّل.</li>
    <li>التسجيل والمتحدث: {report['gates']['audio_and_speaker']['sources']} ملفًا — {VERIFICATION_STATUS}.</li>
    <li>اعتماد المالك للمحتوى: {report['gates']['owner_content_approval']['lessons']} درسًا — {PUBLICATION_STATUS}.</li>
    <li>النشر داخل المستودع: {report['gates']['publication']['screens']} شاشة — {PUBLICATION_STATUS}.</li>
  </ul>
  <h2>روابط</h2>
  <ul>
    <li><a href="../00_طابور_المراجعة.md">الطابور الجذري (Markdown)</a> ·
        <a href="../00_طابور_المراجعة.json">البيانات الكاملة (JSON)</a></li>
    <li><a href="../index.html">فهرس شاشات الدروس</a> ·
        <a href="../../index.html">فهرس دورات القوائم</a> ·
        <a href="../../00_قرارات_المالك.md">قرار المالك</a></li>
    <li><a href="../../../{AUDIT_MD.relative_to(ROOT).as_posix()}">تدقيق استرجاع RAG</a> ·
        <a href="../../../{AUDIT_JSON.relative_to(ROOT).as_posix()}">بيانات التدقيق</a></li>
  </ul>
  <p class="lead">الفحص الآلي يثبت البايتات ومواضع الاقتباس فقط. التغطية الهيكلية لا تعني
  قراءة شاملة ولا صحة محتوى. قرار المالك بالاعتماد موثق، لكن المراجعات المتخصصة
  والنشر الخارجي ودمج طلبات السحب تبقى إجراءات منفصلة.</p>
</main>
</body>
</html>
'''


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare without writing')
    args = parser.parse_args(argv)
    try:
        generated = build()
    except (OSError, ValueError, KeyError) as exc:
        print(f'error: {exc}')
        return 1
    changed = [str(p.relative_to(ROOT)) for p, text in generated.items()
               if not p.exists() or p.read_text(encoding='utf-8') != text]
    if args.check:
        if changed:
            print('✗ طابور المراجعة يحتاج إعادة توليد:')
            for path in changed[:20]:
                print('  ' + path)
            if len(changed) > 20:
                print(f'  ... و{len(changed) - 20} ملفًا آخر')
            return 1
        print(f'ok: {len(generated)} ملف طابور/لوحة مطابق للمسودات والكتالوج')
        return 0
    for p, text in generated.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    print(f'wrote {len(generated)} review files '
          f'({sum(1 for p in generated if p.parent != OUT and p.name == "00_طابور_المراجعة.md")} '
          'playlist queues, 1 dashboard, root JSON/Markdown)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
