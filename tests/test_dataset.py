from __future__ import annotations

import json
import hashlib
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
QUESTIONS = DATA["questions"]
REVIEWED_CONTRACT_HASH = "a6a15b586f8542e9792194e8f745951ef19c6030abf1fe1c71cdc8f41ff5d9a8"


class DatasetTests(unittest.TestCase):
    def test_counts(self) -> None:
        self.assertEqual(156, len(QUESTIONS))
        self.assertEqual(
            {"parts-of-speech": 50, "sentence-elements": 44, "clauses": 62},
            dict(Counter(question["mode"] for question in QUESTIONS)),
        )

    def test_reviewed_source_cases_are_complete_and_unique(self) -> None:
        reviewed = [q for q in QUESTIONS if q["status"] == "teacher-reviewed"]
        self.assertEqual(106, len(reviewed))
        self.assertEqual(106, len({q["source_id"] for q in reviewed}))

    def test_reviewed_mapping_contract_has_not_drifted(self) -> None:
        immutable_fields = (
            "id", "source_id", "mode", "subskill",
            "sentence", "targets", "prompt", "answer",
        )
        reviewed_contract = [
            {field: question[field] for field in immutable_fields}
            for question in QUESTIONS
            if question["status"] == "teacher-reviewed"
        ]
        serialized = json.dumps(
            reviewed_contract,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        self.assertEqual(
            REVIEWED_CONTRACT_HASH,
            hashlib.sha256(serialized).hexdigest(),
            "Reviewed IDs, targets, answers, or terminology changed",
        )

    def test_pos_bank_is_provisional(self) -> None:
        pos = [q for q in QUESTIONS if q["mode"] == "parts-of-speech"]
        self.assertEqual(50, len(pos))
        self.assertTrue(all(q["status"] == "provisional-scaffold" for q in pos))

    def test_operator_is_separate(self) -> None:
        question = next(q for q in QUESTIONS if q["id"] == "SE-P-02")
        self.assertEqual("Operator", question["answer"])
        self.assertEqual([{"text": "Did", "occurrence": 0}], question["targets"])
        self.assertIn("Operator", question["options"])

    def test_manual_review_guard_remains_visible(self) -> None:
        question = next(q for q in QUESTIONS if q["id"] == "REVIEW-01")
        self.assertEqual("Context needed", question["answer"])
        self.assertIn("More context is needed", question["explanation"])

    def test_four_unique_options_and_answer_present(self) -> None:
        for question in QUESTIONS:
            with self.subTest(question=question["id"]):
                self.assertEqual(4, len(question["options"]))
                self.assertEqual(4, len(set(question["options"])))
                self.assertIn(question["answer"], question["options"])

    def test_scoring_contract(self) -> None:
        self.assertEqual(
            {
                "first_attempt_correct": 1,
                "retry_correct": 0,
                "show_answer": 0,
                "negative_points": False,
            },
            DATA["metadata"]["scoring"],
        )
        self.assertEqual(10, DATA["metadata"]["round_size"])


if __name__ == "__main__":
    unittest.main()
