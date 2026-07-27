from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_public_shards  # noqa: E402
import select_sentences  # noqa: E402
from build_question_bank import apply_corrections, build_questions  # noqa: E402
from formal_remap_engine import FormalRemapEngine  # noqa: E402
from generate_questions import contiguous_span  # noqa: E402
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
TAGSET = json.loads(
    (ROOT / "config/pedagogical_tagset_en.json").read_text(encoding="utf-8")
)
REMAPPING_CONTRACT = json.loads(
    (ROOT / "data/gold/remapping_contract_106.json").read_text(encoding="utf-8")
)
REMAPPING_FIXTURES = {
    record["sentence"]: record
    for record in read_jsonl(ROOT / "data/gold/remapping_stanza_1.14.0.jsonl")
}
FORMAL_ENGINE = FormalRemapEngine()


class PipelineTests(unittest.TestCase):
    @staticmethod
    def generated_sentence(sentence_id: str, text: str) -> dict:
        return {
            "sentence_id": sentence_id,
            "text": text,
            "source": {"genre": "test", "corpus": "MASC"},
            "selection": {"difficulty": "intermediate"},
        }

    def test_nominal_relative_subject_is_not_mislabeled_as_postmodifier(self) -> None:
        text = "What tomorrow will bring will come."
        words = [
            {"id": 1, "text": "What", "lemma": "what", "upos": "PRON",
             "xpos": "WP", "head": 6, "deprel": "nsubj",
             "start_char": 0, "end_char": 4},
            {"id": 2, "text": "tomorrow", "lemma": "tomorrow", "upos": "NOUN",
             "xpos": "NN", "head": 4, "deprel": "nsubj",
             "start_char": 5, "end_char": 13},
            {"id": 3, "text": "will", "lemma": "will", "upos": "AUX",
             "xpos": "MD", "head": 4, "deprel": "aux",
             "start_char": 14, "end_char": 18},
            {"id": 4, "text": "bring", "lemma": "bring", "upos": "VERB",
             "xpos": "VB", "head": 1, "deprel": "acl:relcl",
             "start_char": 19, "end_char": 24},
            {"id": 5, "text": "will", "lemma": "will", "upos": "AUX",
             "xpos": "MD", "head": 6, "deprel": "aux",
             "start_char": 25, "end_char": 29},
            {"id": 6, "text": "come", "lemma": "come", "upos": "VERB",
             "xpos": "VB", "head": 0, "deprel": "root",
             "start_char": 30, "end_char": 34},
            {"id": 7, "text": ".", "lemma": ".", "upos": "PUNCT",
             "xpos": ".", "head": 6, "deprel": "punct",
             "start_char": 34, "end_char": 35},
        ]
        candidates = FORMAL_ENGINE.clause_specs(
            words,
            text,
            {},
        )
        candidates = [
            candidate
            for candidate in candidates
            if candidate["dimension"] == "clause_type"
            and candidate["answer"] == "Nominal relative clause — function: S"
        ]
        self.assertEqual(1, len(candidates))
        self.assertEqual(
            "Nominal relative clause — function: S",
            candidates[0]["answer"],
        )
        span = candidates[0]["target_spans"][0]
        self.assertEqual(
            "What tomorrow will bring",
            text[span["start"]:span["end"]],
        )

    def test_non_subject_fused_relative_is_not_called_a_postmodifier(self) -> None:
        text = "I bought what she recommended."
        words = [
            {"id": 1, "text": "I", "lemma": "I", "upos": "PRON",
             "xpos": "PRP", "head": 2, "deprel": "nsubj",
             "start_char": 0, "end_char": 1},
            {"id": 2, "text": "bought", "lemma": "buy", "upos": "VERB",
             "xpos": "VBD", "head": 0, "deprel": "root",
             "start_char": 2, "end_char": 8},
            {"id": 3, "text": "what", "lemma": "what", "upos": "PRON",
             "xpos": "WP", "head": 2, "deprel": "obj",
             "start_char": 9, "end_char": 13},
            {"id": 4, "text": "she", "lemma": "she", "upos": "PRON",
             "xpos": "PRP", "head": 5, "deprel": "nsubj",
             "start_char": 14, "end_char": 17},
            {"id": 5, "text": "recommended", "lemma": "recommend",
             "upos": "VERB", "xpos": "VBD", "head": 3,
             "deprel": "acl:relcl", "start_char": 18, "end_char": 29},
            {"id": 6, "text": ".", "lemma": ".", "upos": "PUNCT",
             "xpos": ".", "head": 2, "deprel": "punct",
             "start_char": 29, "end_char": 30},
        ]
        candidates = FORMAL_ENGINE.clause_specs(
            words,
            text,
            {},
        )
        self.assertFalse(
            any(
                candidate["answer"] == "PostM — Postmodifier"
                or "relative clause — function: PostM" in candidate["answer"]
                for candidate in candidates
            )
        )
        direct_object = [
            candidate
            for candidate in candidates
            if candidate["dimension"] == "clause_function"
            and candidate["answer"] == "DO — Direct Object"
        ]
        self.assertEqual(1, len(direct_object))
        self.assertEqual("needs-review", direct_object[0]["review_status"])
        self.assertTrue(direct_object[0]["review_reason"])

    def test_relative_that_is_not_also_labeled_complementizer(self) -> None:
        text = "The gift that ensures that people learn helps."
        words = [
            {"id": 1, "text": "The", "lemma": "the", "upos": "DET",
             "xpos": "DT", "head": 2, "deprel": "det",
             "start_char": 0, "end_char": 3},
            {"id": 2, "text": "gift", "lemma": "gift", "upos": "NOUN",
             "xpos": "NN", "head": 8, "deprel": "nsubj",
             "start_char": 4, "end_char": 8},
            {"id": 3, "text": "that", "lemma": "that", "upos": "SCONJ",
             "xpos": "IN", "head": 4, "deprel": "nsubj",
             "start_char": 9, "end_char": 13},
            {"id": 4, "text": "ensures", "lemma": "ensure", "upos": "VERB",
             "xpos": "VBZ", "head": 2, "deprel": "acl:relcl",
             "start_char": 14, "end_char": 21},
            {"id": 5, "text": "that", "lemma": "that", "upos": "SCONJ",
             "xpos": "IN", "head": 7, "deprel": "mark",
             "start_char": 22, "end_char": 26},
            {"id": 6, "text": "people", "lemma": "person", "upos": "NOUN",
             "xpos": "NNS", "head": 7, "deprel": "nsubj",
             "start_char": 27, "end_char": 33},
            {"id": 7, "text": "learn", "lemma": "learn", "upos": "VERB",
             "xpos": "VBP", "head": 4, "deprel": "ccomp",
             "start_char": 34, "end_char": 39},
            {"id": 8, "text": "helps", "lemma": "help", "upos": "VERB",
             "xpos": "VBZ", "head": 0, "deprel": "root",
             "start_char": 40, "end_char": 45},
            {"id": 9, "text": ".", "lemma": ".", "upos": "PUNCT",
             "xpos": ".", "head": 8, "deprel": "punct",
             "start_char": 45, "end_char": 46},
        ]
        markers = {
            tuple(
                (span["start"], span["end"])
                for span in item["target_spans"]
            ): item["answer"]
            for item in FORMAL_ENGINE.clause_specs(words, text, {})
            if item["dimension"] == "clause_marker"
        }
        self.assertEqual("Relative pronoun", markers[((9, 13),)])
        self.assertEqual("Complementizer", markers[((22, 26),)])

    def test_complete_remapper_reproduces_reviewed_106_contract(self) -> None:
        cases = REMAPPING_CONTRACT["cases"]
        self.assertEqual(106, len(cases))
        coverage = json.loads(
            (ROOT / "reports/remap_contract_coverage.json").read_text(
                encoding="utf-8"
            )
        )
        replay = json.loads(
            (ROOT / "reports/remap_gold_replay.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(106, coverage["case_count"])
        self.assertEqual(
            {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20},
            coverage["expected_decision_counts"],
        )
        self.assertEqual({"matched": 106}, replay["status_counts"])
        self.assertEqual(0, replay["manual_cases_auto_published"])

    def test_pos_guards_copulas_and_independent_determiners(self) -> None:
        copula = {
            "id": 1, "text": "is", "lemma": "be", "upos": "AUX",
            "xpos": "VBZ", "head": 2, "deprel": "cop",
            "start_char": 0, "end_char": 2,
        }
        auxiliary = {
            "id": 2, "text": "has", "lemma": "have", "upos": "AUX",
            "xpos": "VBZ", "head": 3, "deprel": "aux",
            "start_char": 3, "end_char": 6,
        }
        independent_all = {
            "id": 3, "text": "All", "lemma": "all", "upos": "DET",
            "xpos": "DT", "head": 4, "deprel": "nsubj",
            "start_char": 7, "end_char": 10,
        }
        attributive_all = {
            "id": 4, "text": "all", "lemma": "all", "upos": "DET",
            "xpos": "DT", "head": 5, "deprel": "det",
            "start_char": 11, "end_char": 14,
        }
        specs = FORMAL_ENGINE.word_class_specs(
            [copula, auxiliary, independent_all, attributive_all],
            {},
        )
        by_token_id = {
            item["matched_evidence"]["token_ids"][0]: (
                item["answer"],
                item["rule_id"],
            )
            for item in specs
        }
        self.assertNotIn(1, by_token_id)
        self.assertEqual(
            ("Auxiliary verb", "pos.primary.auxiliary"),
            by_token_id[2],
        )
        self.assertNotIn(3, by_token_id)
        self.assertEqual(
            ("Determiner", "pos.det"),
            by_token_id[4],
        )

    def test_generated_span_excludes_boundary_punctuation(self) -> None:
        words = [
            {"id": 1, "text": ",", "upos": "PUNCT",
             "start_char": 0, "end_char": 1},
            {"id": 2, "text": "working", "upos": "VERB",
             "start_char": 2, "end_char": 9},
            {"id": 3, "text": "carefully", "upos": "ADV",
             "start_char": 10, "end_char": 19},
            {"id": 4, "text": ",", "upos": "PUNCT",
             "start_char": 19, "end_char": 20},
        ]
        self.assertEqual(
            {"start": 2, "end": 19},
            contiguous_span(words),
        )

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

    def test_materialised_selection_is_exact_and_records_fallback(self) -> None:
        report = json.loads(
            (ROOT / "reports/selection_report.json").read_text(encoding="utf-8")
        )
        corpus_path = ROOT / "data/corpus/sentences_10k.jsonl"
        self.assertEqual(10_000, report["accepted_sentence_count"])
        self.assertEqual(10_000, report["unique_sentence_id_count"])
        self.assertEqual(10_000, report["unique_normalized_text_count"])
        self.assertTrue(report["oanc_fallback_needed"])
        self.assertEqual(
            hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            report["selected_jsonl_sha256"],
        )
        corpus = read_jsonl(corpus_path)
        for sentence in corpus:
            self.assertIsNone(
                select_sentences.UNSUITABLE_RE.search(sentence["text"]),
                sentence["sentence_id"],
            )
            self.assertIsNone(
                select_sentences.PUBLIC_TECHNICAL_RE.search(sentence["text"]),
                sentence["sentence_id"],
            )
            self.assertIsNone(
                select_sentences.MALFORMED_TEXT_RE.search(sentence["text"]),
                sentence["sentence_id"],
            )

    def test_selection_rejects_public_technical_terms_and_profanity(self) -> None:
        base = {
            "words": [
                {"text": "Students", "upos": "NOUN", "xpos": "NNS",
                 "start_char": 0, "end_char": 8},
                {"text": "review", "upos": "VERB", "xpos": "VBP",
                 "start_char": 9, "end_char": 15},
            ],
        }
        for text in (
            "Students review the parser mapping in class.",
            "Students review this goddamn example in class.",
            "Students review a dierent example in class.",
            "Students review the code. // This is a comment.",
            "Students review several items:\n·first item\n·second item.",
        ):
            record = {**base, "text": text}
            reasons = select_sentences.rejection_reasons(
                record, minimum=1, maximum=40
            )
            self.assertTrue(
                {
                    "public_technical_terminology",
                    "unsuitable_content",
                    "source_extraction_artifact",
                    "markup_or_formula",
                    "header_or_list_fragment",
                }
                & set(reasons)
            )


if __name__ == "__main__":
    unittest.main()
