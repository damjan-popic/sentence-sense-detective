#!/usr/bin/env python3
"""Build deterministic browser-safe question shards and their manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGE = "en"
DATA_ROOT = ROOT / "data"
OUTPUT_ROOT = ROOT / "docs" / "data" / LANGUAGE
CONFIG_PATH = DATA_ROOT / "questions" / LANGUAGE / "config.json"
SHARD_QUESTION_LIMIT = 400
TARGET_SHARD_BYTES = 500 * 1024
HARD_SHARD_BYTES = 1024 * 1024

PUBLIC_QUESTION_FIELDS = (
    "id",
    "sentence_id",
    "language",
    "mode",
    "subskill",
    "sentence",
    "target_spans",
    "prompt",
    "answer",
    "options",
    "explanation",
)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
    return records


def encoded_json(value: object, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    return text.encode("utf-8")


def load_canonical() -> tuple[dict, list[dict], list[dict], list[dict]]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source_records = json.loads(
        (DATA_ROOT / "sources" / f"{LANGUAGE}-sources.json").read_text(encoding="utf-8")
    )
    source_by_id = {record["id"]: record for record in source_records}
    sentences = []
    for path in sorted((DATA_ROOT / "corpus" / LANGUAGE).glob("sentences-*.jsonl")):
        sentences.extend(read_jsonl(path))
    annotations = read_jsonl(
        DATA_ROOT / "annotations" / LANGUAGE / "pedagogical-annotations.jsonl"
    )
    questions = read_jsonl(DATA_ROOT / "questions" / LANGUAGE / "reviewed-core.jsonl")
    for path in sorted((DATA_ROOT / "questions" / LANGUAGE).glob("provisional-*.jsonl")):
        questions.extend(read_jsonl(path))
    for sentence in sentences:
        source_id = sentence.get("source", {}).get("source_id")
        source = source_by_id.get(source_id)
        if not source or source.get("rights_status") != "cleared-for-publication":
            raise ValueError(
                f"{sentence.get('id', '<missing>')}: source {source_id!r} is not "
                "cleared for public output"
            )
    return config, sentences, annotations, questions


def joined_public_questions(
    sentences: list[dict],
    annotations: list[dict],
    questions: list[dict],
) -> list[dict]:
    sentence_by_id = {record["id"]: record for record in sentences}
    annotation_by_id = {record["id"]: record for record in annotations}
    public_questions = []
    for question in questions:
        sentence = sentence_by_id[question["sentence_id"]]
        annotation = annotation_by_id[question["annotation_id"]]
        record = {
            "id": question["id"],
            "sentence_id": question["sentence_id"],
            "language": question["language"],
            "mode": question["mode"],
            "subskill": question["subskill"],
            "sentence": sentence["text"],
            "target_spans": annotation["target_spans"],
            "prompt": question["prompt"],
            "answer": question["answer"],
            "options": question["options"],
            "explanation": question["explanation"],
        }
        public_questions.append({field: record[field] for field in PUBLIC_QUESTION_FIELDS})
    return public_questions


def packed_shards(records: list[dict], mode: str) -> list[list[dict]]:
    shards: list[list[dict]] = []
    current: list[dict] = []
    for record in records:
        candidate = current + [record]
        payload = {
            "schema_version": 1,
            "language": LANGUAGE,
            "mode": mode,
            "questions": candidate,
        }
        if current and (
            len(candidate) > SHARD_QUESTION_LIMIT
            or len(encoded_json(payload)) > TARGET_SHARD_BYTES
        ):
            shards.append(current)
            current = [record]
        else:
            current = candidate
    if current:
        shards.append(current)
    return shards


def build_files() -> dict[Path, bytes]:
    config, sentences, annotations, questions = load_canonical()
    public_questions = joined_public_questions(sentences, annotations, questions)
    generated: dict[Path, bytes] = {}
    shard_entries = []

    mode_order = [mode["id"] for mode in config["modes"]]
    for mode in mode_order:
        for tier, review_status in (
            ("reviewed-core", "teacher-reviewed"),
            ("provisional", "provisional"),
        ):
            selected = [
                public
                for public, canonical in zip(public_questions, questions, strict=True)
                if canonical["mode"] == mode
                and canonical["review_status"] == review_status
            ]
            for index, shard_records in enumerate(packed_shards(selected, mode), 1):
                filename = f"{tier}-{index:04d}.json"
                relative_path = Path(mode) / filename
                payload = {
                    "schema_version": 1,
                    "language": LANGUAGE,
                    "mode": mode,
                    "questions": shard_records,
                }
                content = encoded_json(payload)
                if len(content) > HARD_SHARD_BYTES:
                    raise ValueError(
                        f"{relative_path} is {len(content)} bytes; hard limit is "
                        f"{HARD_SHARD_BYTES} bytes"
                    )
                generated[relative_path] = content
                shard_id = f"en-{mode}-{tier}-{index:04d}"
                shard_entries.append(
                    {
                        "id": shard_id,
                        "mode": mode,
                        "tier": tier,
                        "path": relative_path.as_posix(),
                        "count": len(shard_records),
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )

    review_counts = Counter(question["review_status"] for question in questions)
    mode_counts = Counter(question["mode"] for question in questions)
    manifest = {
        "schema_version": 1,
        "title": config["title"],
        "language": config["language"],
        "version": config["version"],
        "round_size": config["round_size"],
        "scoring": config["scoring"],
        "sampling_policy": config["sampling_policy"],
        "report_issue_url": config.get("report_issue_url"),
        "modes": config["modes"],
        "totals": {
            "sentences": len(sentences),
            "questions": len(questions),
            "teacher_reviewed": review_counts["teacher-reviewed"],
            "provisional": review_counts["provisional"],
            "by_mode": {
                mode: mode_counts[mode]
                for mode in mode_order
            },
        },
        "shards": shard_entries,
    }
    generated[Path("manifest.json")] = encoded_json(manifest, pretty=True)
    return generated


def existing_json_files() -> set[Path]:
    if not OUTPUT_ROOT.exists():
        return set()
    return {
        path.relative_to(OUTPUT_ROOT)
        for path in OUTPUT_ROOT.rglob("*.json")
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if committed public shards differ from canonical data",
    )
    args = parser.parse_args()
    generated = build_files()

    if args.check:
        failures = []
        for relative_path, expected in generated.items():
            actual_path = OUTPUT_ROOT / relative_path
            if not actual_path.exists() or actual_path.read_bytes() != expected:
                failures.append(relative_path.as_posix())
        stale = existing_json_files() - set(generated)
        failures.extend(sorted(path.as_posix() for path in stale))
        if failures:
            print("Public shards are stale: " + ", ".join(failures), file=sys.stderr)
            print("Run: python3 scripts/build_public_shards.py", file=sys.stderr)
            return 1
        print(f"Public manifest and {len(generated) - 1} shards are up to date.")
        return 0

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for relative_path in existing_json_files() - set(generated):
        (OUTPUT_ROOT / relative_path).unlink()
    for relative_path, content in generated.items():
        path = OUTPUT_ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"Wrote {path.relative_to(ROOT)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
