from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from formal_remap_engine import FormalRemapEngine  # noqa: E402


def match(label: str, rule_id: str) -> dict:
    return {
        "dimension": "sentence_element",
        "answer": label,
        "target_spans": [{"start": 0, "end": 4}],
        "action": "publish",
        "review_status": "auto-high-confidence",
        "review_reason": None,
        "rule_id": rule_id,
        "matched_evidence": {},
    }


class FormalRemapConflictTests(unittest.TestCase):
    def test_incompatible_labels_are_routed_to_review(self) -> None:
        resolved = FormalRemapEngine._resolve_competing_matches(
            [match("S — Subject", "rule-a"), match("DO — Direct Object", "rule-b")]
        )
        self.assertEqual(2, len(resolved))
        for item in resolved:
            self.assertEqual("review", item["action"])
            self.assertEqual("needs-review", item["review_status"])
            self.assertIn("Incompatible formal rules", item["review_reason"])

    def test_compatible_matches_are_merged_deterministically(self) -> None:
        resolved = FormalRemapEngine._resolve_competing_matches(
            [match("S — Subject", "rule-b"), match("S — Subject", "rule-a")]
        )
        self.assertEqual(1, len(resolved))
        self.assertEqual("rule-a", resolved[0]["rule_id"])
        self.assertEqual(
            ["rule-b"],
            resolved[0]["matched_evidence"]["compatible_rule_ids"],
        )


if __name__ == "__main__":
    unittest.main()
