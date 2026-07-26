#!/usr/bin/env python3
"""One-time migration from the v0.2 monolith to v0.3 canonical JSONL records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ID = "ssd-english-pilot"
VERSION = "0.3.0"


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(compact_json(record) + "\n" for record in records), encoding="utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def nth_span(sentence: str, text: str, occurrence: int) -> dict[str, int]:
    folded_sentence = sentence.casefold()
    folded_text = text.casefold()
    cursor = 0
    start = -1
    for _ in range(occurrence + 1):
        start = folded_sentence.find(folded_text, cursor)
        if start < 0:
            raise ValueError(f"Target {text!r} occurrence {occurrence} not found in {sentence!r}")
        cursor = start + len(folded_text)
    end = start + len(text)
    if sentence[start:end].casefold() != text.casefold():
        raise ValueError(f"Target {text!r} cannot be represented by code-point offsets")
    return {"start": start, "end": end}


def dimension_for(question: dict) -> str:
    if question["mode"] == "parts-of-speech":
        return "word_class"
    if question["mode"] == "sentence-elements":
        return "sentence_element"
    return {
        "Clause type": "clause_class",
        "Clause marker": "marker_type",
        "Clause structure": "clause_structure",
        "Clause function": "clause_function",
    }[question["subskill"]]


def annotation_id(question_id: str) -> str:
    digest = sha256_bytes(question_id.encode("utf-8"))[:12]
    return f"en-pa-{digest}"


def migrate(source_path: Path) -> None:
    legacy = json.loads(source_path.read_text(encoding="utf-8"))
    legacy_questions = legacy["questions"]

    sentence_ids: OrderedDict[str, str] = OrderedDict()
    for question in legacy_questions:
        sentence_ids.setdefault(question["sentence"], f"en-s{len(sentence_ids) + 1:06d}")

    annotations: list[dict] = []
    questions: list[dict] = []
    annotation_ids_by_sentence: dict[str, list[str]] = {
        sentence_id: [] for sentence_id in sentence_ids.values()
    }
    sentence_status: dict[str, str] = {
        sentence_id: "provisional" for sentence_id in sentence_ids.values()
    }

    for legacy_question in legacy_questions:
        sentence_id = sentence_ids[legacy_question["sentence"]]
        current_annotation_id = annotation_id(legacy_question["id"])
        review_status = (
            "teacher-reviewed"
            if legacy_question["status"] == "teacher-reviewed"
            else "provisional"
        )
        spans = [
            nth_span(
                legacy_question["sentence"],
                target["text"],
                int(target.get("occurrence", 0)),
            )
            for target in legacy_question["targets"]
        ]
        annotations.append(
            {
                "id": current_annotation_id,
                "sentence_id": sentence_id,
                "language": legacy_question["language"],
                "mode": legacy_question["mode"],
                "subskill": legacy_question["subskill"],
                "dimension": dimension_for(legacy_question),
                "target_spans": spans,
                "label": legacy_question["answer"],
                "review_status": review_status,
                "source_question_id": legacy_question["id"],
            }
        )
        questions.append(
            {
                "id": legacy_question["id"],
                "source_id": legacy_question["source_id"],
                "sentence_id": sentence_id,
                "annotation_id": current_annotation_id,
                "language": legacy_question["language"],
                "mode": legacy_question["mode"],
                "subskill": legacy_question["subskill"],
                "prompt": legacy_question["prompt"],
                "answer": legacy_question["answer"],
                "options": legacy_question["options"],
                "explanation": legacy_question["explanation"],
                "review_status": review_status,
            }
        )
        annotation_ids_by_sentence[sentence_id].append(current_annotation_id)
        if review_status == "teacher-reviewed":
            sentence_status[sentence_id] = "teacher-reviewed"

    sentences = [
        {
            "id": sentence_id,
            "language": "en",
            "text": text,
            "source": {
                "source_id": DEFAULT_SOURCE_ID,
                "document_id": None,
                "licence": "CC-BY-4.0",
                "attribution": "Sentence Sense Detective contributors",
            },
            "pedagogical_annotations": annotation_ids_by_sentence[sentence_id],
            "review_status": sentence_status[sentence_id],
        }
        for text, sentence_id in sentence_ids.items()
    ]
    reviewed_questions = [q for q in questions if q["review_status"] == "teacher-reviewed"]
    provisional_questions = [q for q in questions if q["review_status"] == "provisional"]

    sentence_path = ROOT / "data" / "corpus" / "en" / "sentences-0001.jsonl"
    machine_path = ROOT / "data" / "annotations" / "en" / "machine-annotations.jsonl"
    pedagogical_path = ROOT / "data" / "annotations" / "en" / "pedagogical-annotations.jsonl"
    reviewed_path = ROOT / "data" / "questions" / "en" / "reviewed-core.jsonl"
    provisional_path = ROOT / "data" / "questions" / "en" / "provisional-0001.jsonl"
    write_jsonl(sentence_path, sentences)
    write_jsonl(machine_path, [])
    write_jsonl(pedagogical_path, annotations)
    write_jsonl(reviewed_path, reviewed_questions)
    write_jsonl(provisional_path, provisional_questions)

    source_record = {
        "id": DEFAULT_SOURCE_ID,
        "language": "en",
        "title": "Sentence Sense Detective English pilot",
        "licence": "CC-BY-4.0",
        "attribution": "Sentence Sense Detective contributors",
        "rights_status": "cleared-for-publication",
    }
    write_json(ROOT / "data" / "sources" / "en-sources.json", [source_record])

    config = {
        "schema_version": 1,
        "title": legacy["metadata"]["title"],
        "language": "en",
        "version": VERSION,
        "round_size": legacy["metadata"]["round_size"],
        "scoring": legacy["metadata"]["scoring"],
        "sampling_policy": {
            "reviewed_core_share": 0.2,
            "recent_history_limit": 500,
        },
        "report_issue_url": (
            "https://github.com/damjan-popic/sentence-sense-detective/issues/new"
            "?template=content-correction.md"
        ),
        "modes": legacy["modes"],
    }
    write_json(ROOT / "data" / "questions" / "en" / "config.json", config)

    corpus_manifest = {
        "schema_version": 1,
        "language": "en",
        "sentence_count": len(sentences),
        "shard_size": 500,
        "shards": [
            {
                "path": "sentences-0001.jsonl",
                "count": len(sentences),
                "bytes": sentence_path.stat().st_size,
                "sha256": sha256_file(sentence_path),
            }
        ],
    }
    write_json(ROOT / "data" / "corpus" / "en" / "manifest.json", corpus_manifest)

    question_files = [
        ("reviewed-core.jsonl", reviewed_path, len(reviewed_questions)),
        ("provisional-0001.jsonl", provisional_path, len(provisional_questions)),
    ]
    question_manifest = {
        "schema_version": 1,
        "language": "en",
        "question_count": len(questions),
        "files": [
            {
                "path": name,
                "count": count,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for name, path, count in question_files
        ],
    }
    write_json(ROOT / "data" / "questions" / "en" / "manifest.json", question_manifest)

    old_highlight_contract = [
        {
            "id": q["id"],
            "sentence": q["sentence"],
            "targets": q["targets"],
        }
        for q in legacy_questions
    ]
    old_full_contract = [
        {
            field: q[field]
            for field in (
                "id",
                "source_id",
                "mode",
                "subskill",
                "sentence",
                "targets",
                "prompt",
                "answer",
            )
        }
        for q in legacy_questions
    ]
    try:
        source_label = source_path.relative_to(ROOT).as_posix()
    except ValueError:
        source_label = source_path.name
    report = {
        "migration": "v0.2.1 target text/occurrence to v0.3.0 Unicode code-point offsets",
        "source": source_label,
        "counts": {
            "sentences": len(sentences),
            "questions": len(questions),
            "pedagogical_annotations": len(annotations),
            "machine_annotations": 0,
            "teacher_reviewed": len(reviewed_questions),
            "provisional": len(provisional_questions),
            "by_mode": dict(Counter(q["mode"] for q in questions)),
        },
        "legacy_contract_sha256": {
            "highlights": sha256_bytes(compact_json(old_highlight_contract).encode("utf-8")),
            "questions": sha256_bytes(compact_json(old_full_contract).encode("utf-8")),
        },
    }
    write_json(ROOT / "reports" / "migration-0.3.0.json", report)

    print(f"Migrated {len(questions)} questions across {len(sentences)} unique sentences.")
    print(f"Reviewed: {len(reviewed_questions)}; provisional: {len(provisional_questions)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="path to the legacy v0.2 questions.json",
    )
    args = parser.parse_args()
    migrate(args.source.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
