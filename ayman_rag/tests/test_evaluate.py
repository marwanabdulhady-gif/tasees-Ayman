import unittest
from ayman_rag.evaluate import target_rank


class EvaluationTests(unittest.TestCase):
    def test_hit_requires_correct_source_and_containing_line(self):
        case = {'source_id': 'a', 'line': 10}
        results = [
            {'source_id': 'b', 'start_line': 1, 'end_line': 10},
            {'source_id': 'a', 'start_line': 1, 'end_line': 9},
            {'source_id': 'a', 'start_line': 10, 'end_line': 12},
        ]
        self.assertEqual(target_rank(results, case), 3)
        self.assertIsNone(target_rank(results[:2], case))
        case['line'] = 12
        self.assertEqual(target_rank(results, case), 3)


if __name__ == '__main__':
    unittest.main()
