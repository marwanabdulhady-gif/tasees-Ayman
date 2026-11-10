# -*- coding: utf-8 -*-
"""The owner-decision record is the single source of approval status."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / '08_دورات_القوائم'
DECISIONS_JSON = PKG / '00_قرارات_المالك.json'
DECISIONS_MD = PKG / '00_قرارات_المالك.md'
GENERATOR = PKG / 'tools' / 'apply_owner_decisions.py'


class OwnerDecisionTests(unittest.TestCase):
    def test_recorded_decisions_and_caveats(self):
        data = json.loads(DECISIONS_JSON.read_text(encoding='utf-8'))
        self.assertEqual(data['decisions'], {
            'approval_scope': 'approve_and_publish',
            'q1_voice': 'ayman_style_named',
            'ayn_al_tariq': 'start_after_q1',
        })
        self.assertEqual(data['labels']['publication'], 'approved')
        self.assertEqual(data['labels']['q1_status'], 'decided')
        self.assertEqual(data['labels']['verification'], 'owner_accepted_unverified')
        self.assertTrue(any('فحص آلي' in c for c in data['caveats']))
        self.assertTrue(any('المراجعة السريرية' in c for c in data['caveats']))
        self.assertTrue(any('دمج طلبات السحب' in c for c in data['caveats']))
        md = DECISIONS_MD.read_text(encoding='utf-8')
        self.assertIn('أين الطريق؟', md)
        self.assertIn('مرشد محايد بفصحى مبسطة', md)
        self.assertIn('لا يثبت آليًا', md)

    def test_status_generator_is_reproducible(self):
        r = subprocess.run([sys.executable, str(GENERATOR), '--check'], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('ok:', r.stdout)


if __name__ == '__main__':
    unittest.main()
