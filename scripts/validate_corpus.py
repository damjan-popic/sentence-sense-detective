#!/usr/bin/env python3
"""Validate canonical sentence, annotation, provenance, and question records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from corpus_io import BCP47, sha256_file
from pipeline_common import read_jsonl

ROOT = Path(__file__).resolve().parents[1]
VALID_MODES = {"parts-of-speech", "sentence-elements", "clauses"}
VALID_DIMENSIONS = {
    "word_class",
    "sentence_element",
    "clause_class",
    "marker_type",
    "clause_structure",
    "clause_function",
}
VALID_STATUSES = {"teacher-reviewed", "provisional"}
GENERATED_STATUSES = {
    "auto-high-confidence",
    "human-reviewed",
    "needs-review",
    "rejected",
}


def duplicate_values(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def validate_expanded(data_root: Path, errors: list[str]) -> dict:
    sentences_path = data_root / "corpus" / "sentences_10k.jsonl"
    annotations_path = data_root / "corpus" / "sentences_10k.annotations.jsonl"
    conllu_path = data_root / "corpus" / "sentences_10k.conllu"
    candidates_path = data_root / "generated" / "question_candidates.jsonl.gz"
    accepted_path = data_root / "generated" / "accepted_questions.jsonl.gz"
    remapped_path = (
        data_root / "remap" / "en" / "pedagogical_candidates_10k.jsonl.gz"
    )
    compiled_path = data_root / "remap" / "en" / "compiled_rules.json"
    case_matrix_path = data_root / "remap" / "en" / "case_to_rule.json"
    replay_path = ROOT / "reports" / "remap_gold_replay.json"
    if not all(
        path.exists()
        for path in (
            sentences_path,
            annotations_path,
            conllu_path,
            candidates_path,
            accepted_path,
            remapped_path,
            compiled_path,
            case_matrix_path,
            replay_path,
        )
    ):
        errors.append("the materialised 10K corpus outputs are incomplete")
        return {}

    sentences = read_jsonl(sentences_path)
    sentence_by_id = {record.get("sentence_id"): record for record in sentences}
    if len(sentences) != 10_000:
        errors.append(f"expected 10,000 selected sentences, found {len(sentences)}")
    if len(sentence_by_id) != len(sentences):
        errors.append("10K sentence IDs are not unique")
    normalized = [normalized_text(record.get("text", "")) for record in sentences]
    if len(set(normalized)) != len(sentences):
        errors.append("10K normalized sentence texts are not unique")
    document_counts = Counter()
    difficulty_counts = Counter()
    source_counts = Counter()
    excluded = {"spam", "twitter", "jokes"}
    for record in sentences:
        sentence_id = record.get("sentence_id", "<missing>")
        if record.get("language") != "en" or record.get("variety") != "en-US":
            errors.append(f"{sentence_id}: invalid language or variety")
        source = record.get("source", {})
        for field in (
            "corpus",
            "corpus_version",
            "document_id",
            "genre",
            "source_path",
            "licence",
            "attribution",
            "sentence_index",
        ):
            if source.get(field) in ("", None):
                errors.append(f"{sentence_id}: missing source {field}")
        if source.get("genre") in excluded:
            errors.append(f"{sentence_id}: excluded source genre is present")
        document_counts[(source.get("corpus"), source.get("document_id"))] += 1
        difficulty = record.get("selection", {}).get("difficulty")
        difficulty_counts[difficulty] += 1
        source_counts[source.get("corpus")] += 1
        if record.get("selection", {}).get("seed") != 20260726:
            errors.append(f"{sentence_id}: selection seed changed")
    if document_counts and max(document_counts.values()) > 75:
        errors.append("a source document contributes more than 75 selected sentences")
    if difficulty_counts != Counter(
        {"basic": 3500, "intermediate": 4500, "advanced": 2000}
    ):
        errors.append(f"unexpected 10K difficulty distribution: {dict(difficulty_counts)}")

    annotations = read_jsonl(annotations_path)
    annotation_by_id = {record.get("sentence_id"): record for record in annotations}
    if len(annotations) != 10_000 or set(annotation_by_id) != set(sentence_by_id):
        errors.append("Stanza JSONL must cover every selected sentence exactly once")
    for sentence_id, annotation in annotation_by_id.items():
        source = sentence_by_id.get(sentence_id)
        if not source:
            continue
        if annotation.get("text") != source.get("text"):
            errors.append(f"{sentence_id}: annotation text differs from selected text")
            continue
        for token in annotation.get("tokens", []):
            start, end = token.get("start_char"), token.get("end_char")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or not 0 <= start < end <= len(source["text"])
                or source["text"][start:end] != token.get("text")
            ):
                errors.append(f"{sentence_id}: token character offsets do not align")
                break
        metadata = annotation.get("annotation", {})
        if not metadata.get("stanza_version") or not metadata.get("model_bundle_sha256"):
            errors.append(f"{sentence_id}: Stanza/model versions are missing")
    conllu_text = conllu_path.read_text(encoding="utf-8")
    if conllu_text.count("# sent_id = ") != 10_000:
        errors.append("CoNLL-U output does not contain exactly 10,000 sentences")
    for line_number, line in enumerate(conllu_text.splitlines(), 1):
        if line and not line.startswith("#") and len(line.split("\t")) != 10:
            errors.append(f"CoNLL-U line {line_number} does not have ten columns")
            break

    tagset = json.loads(
        (ROOT / "config" / "pedagogical_tagset_en.json").read_text(encoding="utf-8")
    )
    labels = {
        dimension: set(value["labels"])
        for dimension, value in tagset["dimensions"].items()
    }
    compiled = json.loads(compiled_path.read_text(encoding="utf-8"))
    compiled_rules = {
        rule["rule_id"]: rule for rule in compiled.get("rules", [])
    }
    if len(compiled_rules) != 99:
        errors.append(
            f"expected 99 unique formal rules, found {len(compiled_rules)}"
        )
    case_matrix = json.loads(case_matrix_path.read_text(encoding="utf-8"))
    matrix_rows = case_matrix.get("rows", [])
    if len(matrix_rows) != 106 or len(
        {row.get("case_id") for row in matrix_rows}
    ) != 106:
        errors.append("the formal case-to-rule matrix must cover 106 unique cases")
    expected_decisions = Counter(
        row.get("expected_decision") for row in matrix_rows
    )
    if expected_decisions != Counter(
        {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20}
    ):
        errors.append(
            f"formal decision counts differ from 26/60/20: "
            f"{dict(expected_decisions)}"
        )
    manual_case_ids = {
        row["case_id"]
        for row in matrix_rows
        if row.get("expected_decision") == "Needs manual review"
    }
    for rule in compiled_rules.values():
        if (
            rule.get("action") == "publish"
            and manual_case_ids.intersection(rule.get("source_case_ids", []))
        ):
            errors.append(
                f"{rule['rule_id']}: a manual-review source case can publish"
            )
    pos_rules = [
        rule
        for rule in compiled_rules.values()
        if rule.get("dimension") == "word_class"
    ]
    if not pos_rules or any(
        rule.get("source_case_ids") != ["POS-PROFILE-EN-1.0.0"]
        for rule in pos_rules
    ):
        errors.append("word-class rules are not isolated in the provisional POS profile")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    if (
        replay.get("case_count") != 106
        or replay.get("status_counts") != {"matched": 106}
        or replay.get("manual_cases_auto_published") != 0
    ):
        errors.append("formal gold replay is not a clean 106/106 match")

    remapped = read_jsonl(remapped_path)
    remap_ids = [record.get("remap_candidate_id") for record in remapped]
    if duplicate_values(remap_ids):
        errors.append("formal remap candidate IDs are not unique")
    remap_report = json.loads(
        (data_root / "remap" / "en" / "remap_10k_report.json").read_text(
            encoding="utf-8"
        )
    )
    if remap_report.get("candidate_count") != len(remapped):
        errors.append("formal remap report candidate count differs")
    if remap_report.get("profile_sha256") != compiled.get("profile_sha256"):
        errors.append("formal remap output uses a different compiled profile")
    required_provenance = {
        "remap_profile",
        "remap_profile_sha256",
        "remap_rule_id",
        "decision_class",
        "action",
        "source_case_ids",
        "matched_evidence",
        "stanza_version",
        "model_bundle_sha256",
    }
    for item in remapped:
        remap_id = item.get("remap_candidate_id", "<missing>")
        if required_provenance - set(item):
            errors.append(f"{remap_id}: formal provenance is incomplete")
            continue
        rule = compiled_rules.get(item.get("remap_rule_id"))
        if not rule:
            errors.append(f"{remap_id}: formal rule is absent from the profile")
            continue
        if item.get("remap_profile_sha256") != compiled.get("profile_sha256"):
            errors.append(f"{remap_id}: formal profile hash differs")
        conflict_downgrade = (
            rule.get("action") == "publish"
            and item.get("action") == "review"
            and str(item.get("review_reason") or "").startswith(
                "Incompatible formal rules"
            )
        )
        if item.get("action") != rule.get("action") and not conflict_downgrade:
            errors.append(f"{remap_id}: action differs from formal rule")
        if item.get("source_case_ids") != rule.get("source_case_ids"):
            errors.append(f"{remap_id}: source cases differ from formal rule")
        if (
            item.get("action") == "publish"
            and manual_case_ids.intersection(item.get("source_case_ids", []))
        ):
            errors.append(f"{remap_id}: manual-review case was auto-published")

    candidates = read_jsonl(candidates_path)
    accepted = read_jsonl(accepted_path)
    candidate_ids = [record.get("question_id") for record in candidates]
    if duplicate_values(candidate_ids):
        errors.append("generated question IDs are not unique")
    accepted_sentence_counts = Counter()
    for question in candidates:
        question_id = question.get("question_id", "<missing>")
        if question.get("review_status") not in GENERATED_STATUSES:
            errors.append(f"{question_id}: invalid generated review status")
        if (
            question.get("review_status") == "needs-review"
            and not str(question.get("review_reason") or "").strip()
        ):
            errors.append(f"{question_id}: needs-review candidate has no reason")
        missing_provenance = required_provenance - set(question)
        if missing_provenance:
            errors.append(
                f"{question_id}: missing formal provenance "
                f"{sorted(missing_provenance)}"
            )
        rule = compiled_rules.get(question.get("remap_rule_id"))
        if not rule:
            errors.append(f"{question_id}: unknown formal remap rule")
        elif (
            question.get("rule_id") != rule["rule_id"]
            or question.get("source_case_ids") != rule["source_case_ids"]
        ):
            errors.append(f"{question_id}: provenance differs from formal rule")
        expected_status = {
            "publish": "auto-high-confidence",
            "review": "needs-review",
            "reject": "rejected",
        }.get(question.get("action"))
        if question.get("review_status") != expected_status:
            errors.append(f"{question_id}: action and review status disagree")
        if question.get("answer") not in labels.get(question.get("dimension"), set()):
            errors.append(f"{question_id}: answer is outside controlled vocabulary")
        options = question.get("options")
        if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4:
            errors.append(f"{question_id}: options must be four unique values")
        elif question.get("answer") not in options:
            errors.append(f"{question_id}: answer is absent from options")
        sentence = sentence_by_id.get(question.get("sentence_id"))
        if not sentence or sentence["text"] != question.get("sentence"):
            errors.append(f"{question_id}: sentence text or ID is invalid")
            continue
        for span in question.get("target_spans", []):
            if not (
                isinstance(span.get("start"), int)
                and isinstance(span.get("end"), int)
                and 0 <= span["start"] < span["end"] <= len(sentence["text"])
            ):
                errors.append(f"{question_id}: target offsets are invalid")
    for question in accepted:
        accepted_sentence_counts[question.get("sentence_id")] += 1
    if set(accepted_sentence_counts) != set(sentence_by_id):
        errors.append("every selected sentence must yield at least one accepted question")
    accepted_by_target = defaultdict(list)
    for question in accepted:
        target_key = (
            question.get("sentence_id"),
            question.get("dimension"),
            json.dumps(question.get("target_spans", []), sort_keys=True),
        )
        accepted_by_target[target_key].append(question)
    conflicting_targets = [
        questions
        for questions in accepted_by_target.values()
        if len({question.get("answer") for question in questions}) > 1
    ]
    if conflicting_targets:
        example = conflicting_targets[0]
        errors.append(
            "accepted questions assign contradictory answers to the same "
            f"sentence/dimension/target; first conflict: "
            f"{example[0].get('sentence_id')} "
            f"{sorted({question.get('answer') for question in example})}"
        )

    gold_path = data_root / "gold" / "reviewed_106.jsonl"
    gold_index_path = data_root / "gold" / "index.json"
    gold = read_jsonl(gold_path)
    gold_index = json.loads(gold_index_path.read_text(encoding="utf-8"))
    if len(gold) != 106 or gold_index.get("question_count") != 106:
        errors.append("the immutable gold copy does not contain 106 questions")
    if hashlib.sha256(gold_path.read_bytes()).hexdigest() != gold_index.get("sha256"):
        errors.append("the immutable gold file hash differs from its index")

    contract_path = data_root / "gold" / "remapping_contract_106.json"
    fixture_path = data_root / "gold" / "remapping_stanza_1.14.0.jsonl"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_cases = contract.get("cases", [])
    contract_ids = {case.get("id") for case in contract_cases}
    gold_ids = {case.get("id") for case in gold}
    if len(contract_cases) != 106 or contract_ids != gold_ids:
        errors.append("the remapping contract must match all 106 immutable gold IDs")
    matrix_ids = {row.get("case_id") for row in matrix_rows}
    if contract_ids != matrix_ids:
        errors.append("the formal case matrix does not anchor all 106 gold IDs")
    fixtures = read_jsonl(fixture_path)
    fixture_case_ids = {
        case_id for fixture in fixtures for case_id in fixture.get("case_ids", [])
    }
    if len(fixtures) != 91 or fixture_case_ids != contract_ids:
        errors.append("the Stanza remapping fixture does not cover the 106-case contract")

    return {
        "expanded_sentences": len(sentences),
        "expanded_annotations": len(annotations),
        "generated_candidates": len(candidates),
        "accepted_questions": len(accepted),
        "expanded_by_source": dict(sorted(source_counts.items())),
        "expanded_by_difficulty": dict(sorted(difficulty_counts.items())),
    }


def validate(data_root: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    sources_path = data_root / "sources" / "en-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sentences = []
    corpus_dir = data_root / "corpus" / "en"
    for path in sorted(corpus_dir.glob("sentences-*.jsonl")):
        sentences.extend(read_jsonl(path))
    annotations = read_jsonl(
        data_root / "annotations" / "en" / "pedagogical-annotations.jsonl"
    )
    machine = read_jsonl(
        data_root / "annotations" / "en" / "machine-annotations.jsonl"
    )
    questions = read_jsonl(data_root / "questions" / "en" / "reviewed-core.jsonl")
    for path in sorted((data_root / "questions" / "en").glob("provisional-*.jsonl")):
        questions.extend(read_jsonl(path))

    source_by_id = {source.get("id"): source for source in sources}
    if len(source_by_id) != len(sources):
        errors.append("source IDs must be unique")
    for source in sources:
        for field in ("id", "language", "title", "licence", "attribution", "rights_status"):
            if not source.get(field):
                errors.append(f"source {source.get('id', '<missing>')}: missing {field}")
        if source.get("rights_status") not in {
            "cleared-for-publication", "rights-pending", "blocked"
        }:
            errors.append(f"source {source.get('id')}: invalid rights_status")

    sentence_ids = [record.get("id") for record in sentences]
    for duplicate in duplicate_values(sentence_ids):
        errors.append(f"duplicate sentence ID: {duplicate}")
    sentence_by_id = {record.get("id"): record for record in sentences}
    for sentence in sentences:
        sentence_id = sentence.get("id", "<missing>")
        if not sentence.get("text"):
            errors.append(f"{sentence_id}: sentence text is required")
        if not BCP47.fullmatch(str(sentence.get("language", ""))):
            errors.append(f"{sentence_id}: invalid language")
        if sentence.get("review_status") not in VALID_STATUSES:
            errors.append(f"{sentence_id}: invalid review status")
        provenance = sentence.get("source", {})
        source = source_by_id.get(provenance.get("source_id"))
        if not source:
            errors.append(f"{sentence_id}: unknown source {provenance.get('source_id')!r}")
        for field in ("licence", "attribution"):
            if not provenance.get(field):
                errors.append(f"{sentence_id}: missing source {field}")
            elif source and provenance[field] != source[field]:
                errors.append(f"{sentence_id}: {field} differs from source registry")

    annotation_ids = [record.get("id") for record in annotations]
    for duplicate in duplicate_values(annotation_ids):
        errors.append(f"duplicate pedagogical annotation ID: {duplicate}")
    annotation_by_id = {record.get("id"): record for record in annotations}
    for annotation in annotations:
        annotation_id = annotation.get("id", "<missing>")
        sentence = sentence_by_id.get(annotation.get("sentence_id"))
        if not sentence:
            errors.append(f"{annotation_id}: unknown sentence")
            continue
        if annotation.get("mode") not in VALID_MODES:
            errors.append(f"{annotation_id}: invalid mode")
        if annotation.get("dimension") not in VALID_DIMENSIONS:
            errors.append(f"{annotation_id}: invalid or conflated analysis dimension")
        if annotation.get("review_status") not in VALID_STATUSES:
            errors.append(f"{annotation_id}: invalid review status")
        spans = annotation.get("target_spans")
        if not isinstance(spans, list) or not spans:
            errors.append(f"{annotation_id}: at least one target span is required")
            continue
        previous_end = -1
        for span in sorted(spans, key=lambda value: (value.get("start", -1), value.get("end", -1))):
            start = span.get("start")
            end = span.get("end")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start < 0
                or end <= start
                or end > len(sentence["text"])
            ):
                errors.append(f"{annotation_id}: invalid Unicode code-point span {span!r}")
                continue
            if start < previous_end:
                errors.append(f"{annotation_id}: target spans overlap")
            previous_end = end

    annotation_ids_by_sentence: dict[str, set[str]] = {
        sentence_id: set() for sentence_id in sentence_by_id
    }
    for annotation in annotations:
        if annotation.get("sentence_id") in annotation_ids_by_sentence:
            annotation_ids_by_sentence[annotation["sentence_id"]].add(annotation["id"])
    for sentence in sentences:
        linked = set(sentence.get("pedagogical_annotations", []))
        expected = annotation_ids_by_sentence[sentence["id"]]
        if linked != expected:
            errors.append(
                f"{sentence['id']}: pedagogical annotation links differ from records"
            )

    question_ids = [record.get("id") for record in questions]
    for duplicate in duplicate_values(question_ids):
        errors.append(f"duplicate question ID: {duplicate}")
    for question in questions:
        question_id = question.get("id", "<missing>")
        sentence = sentence_by_id.get(question.get("sentence_id"))
        annotation = annotation_by_id.get(question.get("annotation_id"))
        if not sentence:
            errors.append(f"{question_id}: unknown sentence")
        if not annotation:
            errors.append(f"{question_id}: unknown pedagogical annotation")
            continue
        if annotation.get("sentence_id") != question.get("sentence_id"):
            errors.append(f"{question_id}: question and annotation sentence differ")
        if annotation.get("source_question_id") != question_id:
            errors.append(f"{question_id}: annotation source question ID differs")
        for field in ("mode", "subskill", "language", "review_status"):
            if annotation.get(field) != question.get(field):
                errors.append(f"{question_id}: question and annotation {field} differ")
        if annotation.get("label") != question.get("answer"):
            errors.append(f"{question_id}: answer differs from pedagogical label")
        options = question.get("options")
        if not isinstance(options, list) or len(options) != 4 or len(set(options)) != 4:
            errors.append(f"{question_id}: options must contain four unique values")
        elif question.get("answer") not in options:
            errors.append(f"{question_id}: answer is absent from options")
        for field in ("prompt", "answer", "explanation"):
            if not str(question.get(field, "")).strip():
                errors.append(f"{question_id}: {field} is required")

    for record in machine:
        if record.get("sentence_id") not in sentence_by_id:
            errors.append(f"{record.get('id', '<missing>')}: machine annotation has unknown sentence")

    corpus_manifest_path = corpus_dir / "manifest.json"
    corpus_manifest = json.loads(corpus_manifest_path.read_text(encoding="utf-8"))
    manifest_count = 0
    for shard in corpus_manifest.get("shards", []):
        path = corpus_dir / shard["path"]
        if not path.exists():
            errors.append(f"corpus manifest references missing {shard['path']}")
            continue
        records = read_jsonl(path)
        manifest_count += len(records)
        if shard.get("count") != len(records):
            errors.append(f"{shard['path']}: manifest count differs")
        if shard.get("bytes") != path.stat().st_size:
            errors.append(f"{shard['path']}: manifest byte count differs")
        if shard.get("sha256") != sha256_file(path):
            errors.append(f"{shard['path']}: manifest hash differs")
    if manifest_count != len(sentences) or corpus_manifest.get("sentence_count") != len(sentences):
        errors.append("corpus manifest total differs from sentence records")

    question_dir = data_root / "questions" / "en"
    question_manifest = json.loads(
        (question_dir / "manifest.json").read_text(encoding="utf-8")
    )
    question_manifest_count = 0
    for item in question_manifest.get("files", []):
        path = question_dir / item["path"]
        if not path.exists():
            errors.append(f"question manifest references missing {item['path']}")
            continue
        records = read_jsonl(path)
        question_manifest_count += len(records)
        if item.get("count") != len(records):
            errors.append(f"{item['path']}: question manifest count differs")
        if item.get("bytes") != path.stat().st_size:
            errors.append(f"{item['path']}: question manifest byte count differs")
        if item.get("sha256") != sha256_file(path):
            errors.append(f"{item['path']}: question manifest hash differs")
    if (
        question_manifest_count != len(questions)
        or question_manifest.get("question_count") != len(questions)
    ):
        errors.append("question manifest total differs from question records")

    stats = {
        "sentences": len(sentences),
        "pedagogical_annotations": len(annotations),
        "machine_annotations": len(machine),
        "questions": len(questions),
        "teacher_reviewed": sum(q.get("review_status") == "teacher-reviewed" for q in questions),
        "provisional": sum(q.get("review_status") == "provisional" for q in questions),
        "by_mode": dict(Counter(q.get("mode") for q in questions)),
    }
    stats.update(validate_expanded(data_root, errors))
    return errors, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    try:
        errors, stats = validate(args.data_root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Canonical corpus validation failed: {error}", file=sys.stderr)
        return 1
    if errors:
        print("Canonical corpus validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Canonical corpus validation passed.")
    for label, value in stats.items():
        print(f"- {label.replace('_', ' ').title()}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
