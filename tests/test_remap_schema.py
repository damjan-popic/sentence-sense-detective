from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_remap_rules import compile_profile  # noqa: E402


class FormalRemapSchemaTests(unittest.TestCase):
    def test_profile_compiles_with_complete_reviewed_coverage(self) -> None:
        compiled, matrix, report = compile_profile()
        self.assertEqual("en-1.0.0", compiled["profile_id"])
        self.assertEqual(99, len(compiled["rules"]))
        self.assertEqual(106, len(matrix["rows"]))
        self.assertEqual(106, report["case_count"])
        self.assertEqual(
            {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20},
            report["expected_decision_counts"],
        )

    def test_manual_review_rules_cannot_publish(self) -> None:
        compiled, _, _ = compile_profile()
        for rule in compiled["rules"]:
            with self.subTest(rule_id=rule["rule_id"]):
                if rule["decision_class"] == "manual-review":
                    self.assertNotEqual("publish", rule["action"])

    def test_question_generator_is_presentation_only(self) -> None:
        source = (ROOT / "scripts/generate_questions.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("formal_remap_engine", source)
        self.assertNotIn("pedagogical_remapper", source)
        for graph_signal in ('"nsubj"', '"ccomp"', '"acl:relcl"', '"xcomp"'):
            self.assertNotIn(graph_signal, source)

    def test_formal_matching_does_not_consume_adapter_labels(self) -> None:
        source = (ROOT / "scripts/formal_remap_engine.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('event.get("answer")', source)
        compiled, _, _ = compile_profile()
        for rule in compiled["rules"]:
            with self.subTest(rule_id=rule["rule_id"]):
                self.assertNotIn(
                    "event_label",
                    rule.get("match", {}).get("anchor", {}),
                )

    def test_compiled_profile_hash_matches_materialised_output(self) -> None:
        compiled = json.loads(
            (ROOT / "data/remap/en/compiled_rules.json").read_text(
                encoding="utf-8"
            )
        )
        report = json.loads(
            (ROOT / "data/remap/en/remap_10k_report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            compiled["profile_sha256"],
            report["profile_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
