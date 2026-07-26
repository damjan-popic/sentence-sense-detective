from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_public_shards  # noqa: E402
from build_question_bank import apply_corrections, build_questions  # noqa: E402
from ingest_sentences import validate_and_transform  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


SENTENCES = read_jsonl(ROOT / "data/corpus/en/sentences-0001.jsonl")
ANNOTATIONS = read_jsonl(ROOT / "data/annotations/en/pedagogical-annotations.jsonl")
PROVISIONAL = read_jsonl(ROOT / "data/questions/en/provisional-0001.jsonl")


class PipelineTests(unittest.TestCase):
    def test_ingestion_preserves_text_and_reports_exact_duplicates(self) -> None:
        source_rows = []
        for sentence in SENTENCES[:2]:
            source_rows.append(
                {
                    "sentence_id": sentence["id"],
                    "language": sentence["language"],
                    "text": sentence["text"],
                    "source_id": sentence["source"]["source_id"],
                    "document_id": "",
                    "licence": sentence["source"]["licence"],
                    "attribution": sentence["source"]["attribution"],
                }
            )
        duplicate = dict(source_rows[0])
        duplicate["sentence_id"] = f"{source_rows[0]['sentence_id']}-duplicate-test"
        records, audit = validate_and_transform(source_rows + [duplicate])
        self.assertEqual([row["text"] for row in source_rows] + [duplicate["text"]],
                         [record["text"] for record in records])
        self.assertEqual(1, len(audit["exact_duplicate_groups"]))
        self.assertEqual(0, len(audit["near_duplicate_groups"]))

    def test_ingestion_rejects_missing_rights_metadata(self) -> None:
        sentence = SENTENCES[0]
        row = {
            "sentence_id": sentence["id"],
            "language": "en",
            "text": sentence["text"],
            "source_id": sentence["source"]["source_id"],
            "licence": "",
            "attribution": sentence["source"]["attribution"],
        }
        with self.assertRaisesRegex(ValueError, "licence"):
            validate_and_transform([row])

    def test_preannotation_dry_run_never_requires_package_or_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "corpus"
            input_dir.mkdir()
            (input_dir / "sentences-0001.jsonl").write_text(
                json.dumps(SENTENCES[0], ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/preannotate_stanza.py"),
                    "--input-dir", str(input_dir),
                    "--output", str(root / "machine.jsonl"),
                    "--dry-run",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("No package, model, or resource was installed or downloaded.", result.stdout)
            self.assertFalse((root / "machine.jsonl").exists())

    def test_provisional_question_build_uses_stable_candidate_ids(self) -> None:
        sentence = SENTENCES[0]
        candidate = {
            "id": "en-pa-test",
            "sentence_id": sentence["id"],
            "language": "en",
            "mode": "parts-of-speech",
            "subskill": "Parts of speech",
            "dimension": "word_class",
            "target_spans": [{"start": 0, "end": 5}],
            "label": "Proper noun",
            "review_status": "provisional",
            "source_question_id": "POS-AUTO-TEST",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentences_path = root / "sentences.jsonl"
            annotations_path = root / "annotations.jsonl"
            sentences_path.write_text(json.dumps(sentence) + "\n", encoding="utf-8")
            annotations_path.write_text(json.dumps(candidate) + "\n", encoding="utf-8")
            first = build_questions(sentences_path, annotations_path)
            second = build_questions(sentences_path, annotations_path)
        self.assertEqual(first, second)
        self.assertEqual("POS-AUTO-TEST", first[0]["id"])
        self.assertIn(first[0]["answer"], first[0]["options"])

    def test_candidate_builder_uses_checked_sentence_and_offsets(self) -> None:
        sentence = SENTENCES[0]
        machine = {
            "id": "en-ma-test",
            "sentence_id": sentence["id"],
            "language": "en",
            "engine": "checked-test-fixture",
            "engine_version": "1",
            "model": "checked-test-fixture",
            "payload": {
                "sentences": [
                    {
                        "text": sentence["text"],
                        "words": [
                            {
                                "id": 1,
                                "text": sentence["text"][0:5],
                                "lemma": sentence["text"][0:5],
                                "upos": "PROPN",
                                "xpos": None,
                                "head": 0,
                                "deprel": "root",
                                "start_char": 0,
                                "end_char": 5,
                            }
                        ],
                    }
                ]
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentences_path = root / "sentences.jsonl"
            machine_path = root / "machine.jsonl"
            output_path = root / "candidates.jsonl"
            review_path = root / "review.json"
            sentences_path.write_text(json.dumps(sentence) + "\n", encoding="utf-8")
            machine_path.write_text(json.dumps(machine) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_pedagogical_candidates.py"),
                    "--sentences", str(sentences_path),
                    "--machine-annotations", str(machine_path),
                    "--output", str(output_path),
                    "--review-queue", str(review_path),
                    "--max-per-sentence", "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            candidates = read_jsonl(output_path)
            review = json.loads(review_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(candidates))
        self.assertEqual("Proper noun", candidates[0]["label"])
        self.assertEqual([{"start": 0, "end": 5}], candidates[0]["target_spans"])
        self.assertEqual(0, review["manual_review_count"])

    def test_review_correction_is_idempotent_and_promotes_status(self) -> None:
        question = copy.deepcopy(PROVISIONAL[0])
        annotation = copy.deepcopy(
            next(record for record in ANNOTATIONS if record["id"] == question["annotation_id"])
        )
        correction = {
            "id": question["id"],
            "review_status": "teacher-reviewed",
            "rationale": "Checked against the supplied pilot sentence and accepted unchanged.",
        }
        questions, annotations, changes = apply_corrections(
            [question], [annotation], [correction]
        )
        self.assertEqual(1, len(changes))
        self.assertEqual("teacher-reviewed", questions[0]["review_status"])
        self.assertEqual("teacher-reviewed", annotations[0]["review_status"])
        again_questions, again_annotations, again_changes = apply_corrections(
            copy.deepcopy(questions), copy.deepcopy(annotations), [correction]
        )
        self.assertEqual([], again_changes)
        self.assertEqual(questions, again_questions)
        self.assertEqual(annotations, again_annotations)

    def test_public_build_is_byte_deterministic(self) -> None:
        first = build_public_shards.build_files()
        second = build_public_shards.build_files()
        self.assertEqual(first, second)

    def test_capacity_report_materializes_no_corpus(self) -> None:
        report = json.loads(
            (ROOT / "reports/capacity-10000.json").read_text(encoding="utf-8")
        )
        self.assertEqual(10_000, report["hypothetical_sentence_count"])
        self.assertEqual(20, report["hypothetical_sentence_shards"])
        self.assertFalse(report["corpus_materialized"])
        self.assertFalse(report["corpus_supplied"])
        self.assertIsNone(report["hypothetical_question_count"])


if __name__ == "__main__":
    unittest.main()
