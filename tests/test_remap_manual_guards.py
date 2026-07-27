from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FormalRemapManualGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "data/remap/en/martin_contract_106.json").read_text(
                encoding="utf-8"
            )
        )
        cls.profile = json.loads(
            (ROOT / "data/remap/en/compiled_rules.json").read_text(
                encoding="utf-8"
            )
        )

    def test_all_20_manual_cases_have_review_guards(self) -> None:
        manual_ids = {
            case["case_id"]
            for case in self.contract["cases"]
            if case["reference"]["expected_decision"]
            == "Needs manual review"
        }
        self.assertEqual(20, len(manual_ids))
        rule_actions = {
            case_id: {
                rule["action"]
                for rule in self.profile["rules"]
                if case_id in rule["source_case_ids"]
            }
            for case_id in manual_ids
        }
        for case_id, actions in rule_actions.items():
            with self.subTest(case_id=case_id):
                self.assertTrue(actions)
                self.assertNotIn("publish", actions)
                self.assertIn("review", actions)

    def test_zero_marker_is_review_only(self) -> None:
        rules = [
            rule
            for rule in self.profile["rules"]
            if "CL-MARK-10" in rule["source_case_ids"]
        ]
        self.assertEqual(1, len(rules))
        self.assertEqual("review", rules[0]["action"])
        self.assertEqual("Zero marker", rules[0]["output"]["label"])

    def test_materialised_guard_registry_matches_review_rules(self) -> None:
        path = ROOT / "data/remap/en/manual_guards.jsonl"
        guards = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        expected = {
            rule["rule_id"]
            for rule in self.profile["rules"]
            if rule["action"] == "review"
        }
        self.assertEqual(expected, {guard["rule_id"] for guard in guards})
        self.assertTrue(all(guard["guards"] for guard in guards))


if __name__ == "__main__":
    unittest.main()
