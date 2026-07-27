from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_common import read_jsonl  # noqa: E402

QUESTIONS = ROOT / "data/generated/question_candidates.jsonl.gz"


class FormalRemapSpanTests(unittest.TestCase):
    def test_all_generated_highlights_are_valid_and_ordered(self) -> None:
        count = 0
        for item in read_jsonl(QUESTIONS):
            count += 1
            previous_end = -1
            self.assertTrue(item["target_spans"], item["question_id"])
            for span in item["target_spans"]:
                self.assertLessEqual(0, span["start"])
                self.assertLess(span["start"], span["end"])
                self.assertLessEqual(span["end"], len(item["sentence"]))
                self.assertGreaterEqual(span["start"], previous_end)
                previous_end = span["end"]
        self.assertEqual(119_261, count)


if __name__ == "__main__":
    unittest.main()
