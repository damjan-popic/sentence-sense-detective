from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from formal_remap_engine import FormalRemapEngine  # noqa: E402
from replay_gold_contract import replay  # noqa: E402


class FormalRemapGoldReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results, cls.report = replay(FormalRemapEngine())

    def test_all_106_reviewed_cases_match(self) -> None:
        self.assertEqual(106, len(self.results))
        self.assertEqual({"matched": 106}, self.report["status_counts"])

    def test_reviewed_decision_split_is_exact(self) -> None:
        self.assertEqual(
            {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20},
            self.report["decision_counts"],
        )

    def test_no_manual_case_is_auto_published(self) -> None:
        self.assertEqual(0, self.report["manual_cases_auto_published"])


if __name__ == "__main__":
    unittest.main()
