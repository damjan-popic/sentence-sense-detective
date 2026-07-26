from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


SENTENCES = read_jsonl(ROOT / "data/corpus/en/sentences-0001.jsonl")
ANNOTATIONS = read_jsonl(ROOT / "data/annotations/en/pedagogical-annotations.jsonl")
REVIEWED = read_jsonl(ROOT / "data/questions/en/reviewed-core.jsonl")
PROVISIONAL = read_jsonl(ROOT / "data/questions/en/provisional-0001.jsonl")
QUESTIONS = PROVISIONAL + REVIEWED
CONFIG = json.loads((ROOT / "data/questions/en/config.json").read_text(encoding="utf-8"))
SENTENCE_BY_ID = {record["id"]: record for record in SENTENCES}
ANNOTATION_BY_ID = {record["id"]: record for record in ANNOTATIONS}
REVIEWED_CONTRACT_HASH = "a6a15b586f8542e9792194e8f745951ef19c6030abf1fe1c71cdc8f41ff5d9a8"
HIGHLIGHT_CONTRACT_HASH = "3688077b0bf6e345e98ef88e85afc734660a79cf893ff2a1c9ffbe09a92d3a39"
QUESTION_CONTRACT_HASH = "e8a660c6e98830cdd272ccf665e8783b2771788bd27fd11ab05e03052fdb35ca"


def legacy_targets(question: dict) -> list[dict]:
    sentence = SENTENCE_BY_ID[question["sentence_id"]]["text"]
    annotation = ANNOTATION_BY_ID[question["annotation_id"]]
    output = []
    for span in annotation["target_spans"]:
        text = sentence[span["start"]:span["end"]]
        output.append(
            {
                "text": text,
                "occurrence": sentence[:span["start"]].casefold().count(text.casefold()),
            }
        )
    return output


def contract_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class DatasetTests(unittest.TestCase):
    def test_counts(self) -> None:
        self.assertEqual(92, len(SENTENCES))
        self.assertEqual(156, len(QUESTIONS))
        self.assertEqual(156, len(ANNOTATIONS))
        self.assertEqual(
            {"parts-of-speech": 50, "sentence-elements": 44, "clauses": 62},
            dict(Counter(question["mode"] for question in QUESTIONS)),
        )

    def test_reviewed_source_cases_are_complete_and_unique(self) -> None:
        self.assertEqual(106, len(REVIEWED))
        self.assertEqual(106, len({question["source_id"] for question in REVIEWED}))

    def test_offset_migration_preserves_all_legacy_contracts(self) -> None:
        joined = [
            {
                **question,
                "sentence": SENTENCE_BY_ID[question["sentence_id"]]["text"],
                "targets": legacy_targets(question),
            }
            for question in QUESTIONS
        ]
        highlight_contract = [
            {"id": q["id"], "sentence": q["sentence"], "targets": q["targets"]}
            for q in joined
        ]
        full_contract = [
            {
                field: q[field]
                for field in (
                    "id", "source_id", "mode", "subskill", "sentence",
                    "targets", "prompt", "answer",
                )
            }
            for q in joined
        ]
        reviewed_contract = [
            {
                field: q[field]
                for field in (
                    "id", "source_id", "mode", "subskill", "sentence",
                    "targets", "prompt", "answer",
                )
            }
            for q in joined
            if q["review_status"] == "teacher-reviewed"
        ]
        self.assertEqual(HIGHLIGHT_CONTRACT_HASH, contract_hash(highlight_contract))
        self.assertEqual(QUESTION_CONTRACT_HASH, contract_hash(full_contract))
        self.assertEqual(REVIEWED_CONTRACT_HASH, contract_hash(reviewed_contract))

    def test_offsets_are_valid_unicode_code_point_ranges(self) -> None:
        for annotation in ANNOTATIONS:
            sentence = SENTENCE_BY_ID[annotation["sentence_id"]]["text"]
            with self.subTest(annotation=annotation["id"]):
                self.assertTrue(annotation["target_spans"])
                for span in annotation["target_spans"]:
                    self.assertGreaterEqual(span["start"], 0)
                    self.assertGreater(span["end"], span["start"])
                    self.assertLessEqual(span["end"], len(sentence))
                    self.assertTrue(sentence[span["start"]:span["end"]])

    def test_analysis_dimensions_remain_separate(self) -> None:
        expected = {
            "word_class",
            "sentence_element",
            "clause_class",
            "marker_type",
            "clause_structure",
            "clause_function",
        }
        self.assertEqual(expected, {annotation["dimension"] for annotation in ANNOTATIONS})

    def test_operator_and_manual_review_guards(self) -> None:
        operator = next(question for question in QUESTIONS if question["id"] == "SE-P-02")
        self.assertEqual("Operator", operator["answer"])
        self.assertEqual([{"text": "Did", "occurrence": 0}], legacy_targets(operator))
        review = next(question for question in QUESTIONS if question["id"] == "REVIEW-01")
        self.assertEqual("Context needed", review["answer"])
        self.assertIn("More context is needed", review["explanation"])

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
            CONFIG["scoring"],
        )
        self.assertEqual(10, CONFIG["round_size"])


if __name__ == "__main__":
    unittest.main()
