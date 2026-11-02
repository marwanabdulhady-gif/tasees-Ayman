#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single source of truth for the owner's recorded approval decisions."""
from __future__ import annotations

import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
DECISIONS_PATH = PKG / '00_قرارات_المالك.json'


def load() -> dict:
    return json.loads(DECISIONS_PATH.read_text(encoding='utf-8'))


DECISIONS = load()
APPROVED = DECISIONS['decisions']['approval_scope'] == 'approve_and_publish'
Q1_DECIDED = DECISIONS['decisions']['q1_voice'] == 'neutral_named'
START_AYN = DECISIONS['decisions']['ayn_al_tariq'] == 'start_after_q1'
LABELS = DECISIONS['labels']
CAVEATS = DECISIONS['caveats']
APPROVED_STATUS = LABELS['status']
SHORT_STATUS = LABELS['short_status']
PUBLICATION_STATUS = LABELS['publication']
Q1_STATUS = LABELS['q1_status']
VERIFICATION_STATUS = LABELS['verification']
APPROVED_GATE = 'approved by owner for publication' if APPROVED else 'approval pending'
Q1_GATE = 'Q1 decided: neutral named guide' if Q1_DECIDED else 'Q1 pending'
REVIEWER = 'owner'
DECISION_ID = 'approve_and_publish'
EVIDENCE = '00_قرارات_المالك.json'


def status() -> str:
    return APPROVED_STATUS if APPROVED else 'مسودة تعليمية غير معتمدة'


def publication() -> str:
    return PUBLICATION_STATUS if APPROVED else 'blocked'


def gate_for(voice: str | None) -> str:
    return Q1_GATE if voice == 'owner-decision' else APPROVED_GATE


def review_gate_for(voice: str | None) -> str:
    return Q1_STATUS if voice == 'owner-decision' else PUBLICATION_STATUS


if __name__ == '__main__':
    print(json.dumps({'approved': APPROVED, 'q1_decided': Q1_DECIDED,
                      'start_ayn': START_AYN, 'status': status()}, ensure_ascii=False))
