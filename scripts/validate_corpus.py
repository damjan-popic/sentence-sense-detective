#!/usr/bin/env python3
"""Validate canonical sentence, annotation, provenance, and question records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from corpus_io import BCP47, read_jsonl, sha256_file

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


def duplicate_values(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


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
