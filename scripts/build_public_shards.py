#!/usr/bin/env python3
"""Build deterministic browser-safe gold data, shards, and a small manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from pipeline_common import ROOT, canonical_json_bytes, read_json, read_jsonl, write_json

LANGUAGE = "en"
DATA_ROOT = ROOT / "data"
OUTPUT_ROOT = ROOT / "docs" / "data"
CONFIG_PATH = DATA_ROOT / "questions" / LANGUAGE / "config.json"
CORPUS_CONFIG = ROOT / "config" / "corpus_10k.yaml"
SOURCE_MANIFEST = ROOT / "config" / "source_manifest.json"
GENERATED_QUESTIONS = DATA_ROOT / "generated" / "accepted_questions.jsonl.gz"
SHARD_QUESTION_LIMIT = 400
SHARD_MAX_BYTES = 500_000
MANIFEST_MAX_BYTES = 250_000
INITIAL_TRANSFER_MAX_BYTES = 500_000
MODE_PREFIX = {
    "parts-of-speech": "pos",
    "sentence-elements": "se",
    "clauses": "clause",
}
PUBLIC_QUESTION_FIELDS = (
    "id",
    "sentence_id",
    "language",
    "mode",
    "subskill",
    "dimension",
    "sentence",
    "target_spans",
    "prompt",
    "answer",
    "options",
    "explanation",
    "difficulty",
)


def encoded_json(value: object, *, pretty: bool = False) -> bytes:
    return canonical_json_bytes(value, pretty=pretty)


def pilot_difficulty(sentence: str) -> str:
    words = sentence.split()
    if len(words) <= 10:
        return "basic"
    if len(words) <= 22:
        return "intermediate"
    return "advanced"


def load_pilot() -> tuple[dict, list[dict], list[dict]]:
    config = read_json(CONFIG_PATH)
    sentences = []
    for path in sorted((DATA_ROOT / "corpus" / LANGUAGE).glob("sentences-*.jsonl")):
        sentences.extend(read_jsonl(path))
    annotations = list(
        read_jsonl(DATA_ROOT / "annotations" / LANGUAGE / "pedagogical-annotations.jsonl")
    )
    questions = list(
        read_jsonl(DATA_ROOT / "questions" / LANGUAGE / "reviewed-core.jsonl")
    )
    for path in sorted(
        (DATA_ROOT / "questions" / LANGUAGE).glob("provisional-*.jsonl")
    ):
        questions.extend(read_jsonl(path))
    sentence_by_id = {record["id"]: record for record in sentences}
    annotation_by_id = {record["id"]: record for record in annotations}
    public = []
    internal = []
    for question in questions:
        sentence = sentence_by_id[question["sentence_id"]]["text"]
        annotation = annotation_by_id[question["annotation_id"]]
        record = {
            "id": question["id"],
            "sentence_id": question["sentence_id"],
            "language": question["language"],
            "mode": question["mode"],
            "subskill": question["subskill"],
            "dimension": annotation["dimension"],
            "sentence": sentence,
            "target_spans": annotation["target_spans"],
            "prompt": question["prompt"],
            "answer": question["answer"],
            "options": question["options"],
            "explanation": question["explanation"],
            "difficulty": pilot_difficulty(sentence),
        }
        public.append({field: record[field] for field in PUBLIC_QUESTION_FIELDS})
        internal.append(
            {
                "review_status": (
                    "martin-reviewed"
                    if question["review_status"] == "teacher-reviewed"
                    else "pilot-scaffold"
                ),
                "source_corpus": "English pilot",
                "rule_group": "martin-reviewed-core",
            }
        )
    return config, public, internal


def load_generated() -> tuple[list[dict], list[dict]]:
    if not GENERATED_QUESTIONS.exists():
        return [], []
    public = []
    internal = []
    for question in read_jsonl(GENERATED_QUESTIONS):
        record = {
            "id": question["question_id"],
            "sentence_id": question["sentence_id"],
            "language": LANGUAGE,
            "mode": question["mode"],
            "subskill": question["subskill"],
            "dimension": question["dimension"],
            "sentence": question["sentence"],
            "target_spans": question["target_spans"],
            "prompt": question["prompt"],
            "answer": question["answer"],
            "options": question["options"],
            "explanation": question["explanation"],
            "difficulty": question["difficulty"],
        }
        public.append({field: record[field] for field in PUBLIC_QUESTION_FIELDS})
        internal.append(
            {
                "review_status": question["review_status"],
                "source_corpus": question["source_corpus"],
                "rule_group": question["remap_rule_id"],
            }
        )
    return public, internal


def packed_shards(records: list[dict], mode: str) -> list[list[dict]]:
    shards = []
    current = []
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
            or len(encoded_json(payload)) > SHARD_MAX_BYTES
        ):
            shards.append(current)
            current = [record]
        else:
            current = candidate
    if current:
        shards.append(current)
    return shards


def nested_counts(records: list[dict], field: str) -> dict:
    return dict(sorted(Counter(record[field] for record in records).items()))


def build_timestamp() -> str:
    manifest = read_json(SOURCE_MANIFEST)
    masc = next(
        source for source in manifest["sources"] if source.get("corpus") == "MASC"
    )
    value = masc.get("retrieved_at_utc")
    if not value:
        raise ValueError("source manifest does not contain the MASC retrieval timestamp")
    return value


def build_files() -> dict[Path, bytes]:
    config, pilot_public, pilot_internal = load_pilot()
    generated_public, generated_internal = load_generated()
    if not generated_public:
        raise ValueError(
            "no generated questions exist; run the corpus annotation and generation stages"
        )
    pairs = list(zip(pilot_public + generated_public, pilot_internal + generated_internal, strict=True))
    gold = [
        public
        for public, internal in pairs
        if internal["review_status"] == "martin-reviewed"
    ]
    if len(gold) != 106:
        raise ValueError(f"expected 106 reviewed gold questions, found {len(gold)}")
    non_gold_pairs = [
        (public, internal)
        for public, internal in pairs
        if internal["review_status"] != "martin-reviewed"
    ]
    non_gold_pairs.sort(key=lambda pair: (pair[0]["mode"], pair[0]["id"]))

    generated: dict[Path, bytes] = {}
    gold_payload = {
        "schema_version": 1,
        "language": LANGUAGE,
        "questions": gold,
    }
    gold_content = encoded_json(gold_payload)
    generated[Path("gold.json")] = gold_content
    gold_entry = {
        "path": "gold.json",
        "count": len(gold),
        "bytes": len(gold_content),
        "sha256": hashlib.sha256(gold_content).hexdigest(),
        "by_mode": nested_counts(gold, "mode"),
    }

    shard_entries = []
    mode_order = [mode["id"] for mode in config["modes"]]
    for mode in mode_order:
        records = [public for public, _ in non_gold_pairs if public["mode"] == mode]
        for index, shard_records in enumerate(packed_shards(records, mode)):
            filename = f"{MODE_PREFIX[mode]}-{index:03d}.json"
            relative_path = Path("shards") / filename
            payload = {
                "schema_version": 1,
                "language": LANGUAGE,
                "mode": mode,
                "questions": shard_records,
            }
            content = encoded_json(payload)
            if len(content) > SHARD_MAX_BYTES:
                raise ValueError(
                    f"{relative_path} is {len(content)} bytes; limit is {SHARD_MAX_BYTES}"
                )
            generated[relative_path] = content
            shard_entries.append(
                {
                    "id": filename.removesuffix(".json"),
                    "mode": mode,
                    "path": relative_path.as_posix(),
                    "count": len(shard_records),
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "difficulty": nested_counts(shard_records, "difficulty"),
                    "by_label": nested_counts(shard_records, "answer"),
                    "by_dimension": nested_counts(
                        shard_records, "dimension"
                    ),
                    "by_subskill": nested_counts(shard_records, "subskill"),
                }
            )

    all_public = [public for public, _ in pairs]
    all_internal = [internal for _, internal in pairs]
    unique_sentences = {record["sentence_id"] for record in all_public}
    corpus_sentence_ids = {
        record["sentence_id"]
        for record, internal in pairs
        if internal["source_corpus"] in {"MASC", "OANC"}
    }
    subskills_by_mode = {
        mode: sorted(
            {
                record["subskill"]
                for record in all_public
                if record["mode"] == mode
            }
        )
        for mode in mode_order
    }
    manifest = {
        "schema_version": 2,
        "title": config["title"],
        "language": config["language"],
        "version": "1.0.0",
        "corpus_version": "MASC-3.0.0-SSD-10K-1.0.0",
        "build_timestamp_utc": build_timestamp(),
        "round_size": config["round_size"],
        "scoring": config["scoring"],
        "sampling_policy": {
            "reviewed_item_weight": 0.15,
            "recent_question_ids_per_mode": 250,
            "recent_sentence_ids_per_mode": 150,
            "max_answer_label_per_round": 3,
            "max_subskill_per_round": 4,
            "subskills_by_mode": subskills_by_mode,
            "difficulty": {
                "basic": 0.35,
                "intermediate": 0.45,
                "advanced": 0.20,
            },
        },
        "report_issue_url": config.get("report_issue_url"),
        "modes": config["modes"],
        "totals": {
            "sentences": len(unique_sentences),
            "corpus_sentences": len(corpus_sentence_ids),
            "questions": len(all_public),
            "reviewed_questions": len(gold),
            "by_mode": nested_counts(all_public, "mode"),
            "by_subskill": nested_counts(all_public, "subskill"),
            "by_dimension": nested_counts(all_public, "dimension"),
            "by_difficulty": nested_counts(all_public, "difficulty"),
            "by_source_corpus": dict(
                sorted(Counter(item["source_corpus"] for item in all_internal).items())
            ),
            "internal_rule_groups_at_build_time": len(
                {item["rule_group"] for item in all_internal}
            ),
        },
        "gold": gold_entry,
        "shards": shard_entries,
    }
    manifest_content = encoded_json(manifest, pretty=True)
    if len(manifest_content) > MANIFEST_MAX_BYTES:
        raise ValueError(
            f"manifest is {len(manifest_content)} bytes; limit is {MANIFEST_MAX_BYTES}"
        )
    generated[Path("manifest.json")] = manifest_content
    return generated


def existing_json_files() -> set[Path]:
    if not OUTPUT_ROOT.exists():
        return set()
    return {
        path.relative_to(OUTPUT_ROOT)
        for path in OUTPUT_ROOT.rglob("*.json")
        if path.is_file()
    }


def build_report(generated: dict[Path, bytes]) -> dict:
    manifest = json.loads(generated[Path("manifest.json")])
    generation = read_json(
        ROOT / "data" / "generated" / "generation_report.json"
    )
    remap = read_json(
        ROOT / "data" / "remap" / "en" / "remap_10k_report.json"
    )
    shard_sizes = [entry["bytes"] for entry in manifest["shards"]]
    static_files = [
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "assets" / "styles.css",
        ROOT / "docs" / "assets" / "round-state.js",
        ROOT / "docs" / "assets" / "question-bank.js",
        ROOT / "docs" / "assets" / "app.js",
    ]
    initial_bytes = sum(path.stat().st_size for path in static_files) + len(
        generated[Path("manifest.json")]
    )
    site_bytes = sum(
        path.stat().st_size
        for path in (ROOT / "docs").rglob("*")
        if path.is_file()
    )
    return {
        "public_sentence_count": manifest["totals"]["sentences"],
        "corpus_sentence_count": manifest["totals"]["corpus_sentences"],
        "public_question_count": manifest["totals"]["questions"],
        "reviewed_question_count": manifest["totals"]["reviewed_questions"],
        "formal_candidate_count": remap["candidate_count"],
        "presented_candidate_count": generation["candidate_count"],
        "generated_publishable_count": generation["accepted_count"],
        "generated_review_only_count": generation["review_needed_count"],
        "pilot_question_count": (
            manifest["totals"]["questions"] - generation["accepted_count"]
        ),
        "question_counts_by_mode": manifest["totals"]["by_mode"],
        "round_sampling": manifest["sampling_policy"],
        "shard_count": len(shard_sizes),
        "smallest_shard_bytes": min(shard_sizes) if shard_sizes else 0,
        "largest_shard_bytes": max(shard_sizes) if shard_sizes else 0,
        "initial_transfer_bytes": initial_bytes,
        "initial_transfer_budget_bytes": INITIAL_TRANSFER_MAX_BYTES,
        "initial_transfer_within_budget": initial_bytes <= INITIAL_TRANSFER_MAX_BYTES,
        "total_public_site_bytes": site_bytes,
    }


def markdown_report(report: dict) -> str:
    return "\n".join(
        [
            "# Public build report",
            "",
            f"- Corpus sentences: {report['corpus_sentence_count']}",
            f"- Public sentence IDs: {report['public_sentence_count']}",
            f"- Public questions: {report['public_question_count']}",
            f"- Reviewed gold questions: {report['reviewed_question_count']}",
            f"- Formal candidates before presentation selection: "
            f"{report['formal_candidate_count']}",
            f"- Presented generated candidates: "
            f"{report['presented_candidate_count']}",
            f"- Published generated questions: "
            f"{report['generated_publishable_count']}",
            f"- Review-only generated questions: "
            f"{report['generated_review_only_count']}",
            f"- Preserved pilot questions: {report['pilot_question_count']}",
            (
                "- Ordinary-round answer-label cap: "
                f"{report['round_sampling']['max_answer_label_per_round']}"
            ),
            f"- Shards: {report['shard_count']}",
            (
                f"- Shard size range: {report['smallest_shard_bytes']}–"
                f"{report['largest_shard_bytes']} bytes"
            ),
            f"- Initial transfer: {report['initial_transfer_bytes']} bytes",
            f"- Total public site: {report['total_public_site_bytes']} bytes",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if committed public data differs from canonical data",
    )
    args = parser.parse_args()
    try:
        generated = build_files()
        expected_paths = set(generated)
        if args.check:
            failures = []
            for relative_path, expected in generated.items():
                actual_path = OUTPUT_ROOT / relative_path
                if not actual_path.exists() or actual_path.read_bytes() != expected:
                    failures.append(relative_path.as_posix())
            failures.extend(
                sorted(
                    path.as_posix()
                    for path in existing_json_files() - expected_paths
                )
            )
            if failures:
                print("Public data is stale: " + ", ".join(failures), file=sys.stderr)
                return 1
            print(
                f"Public manifest, gold file, and {len(generated) - 2} shards are up to date."
            )
            return 0

        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        for relative_path in existing_json_files() - expected_paths:
            (OUTPUT_ROOT / relative_path).unlink()
        legacy = OUTPUT_ROOT / "en"
        if legacy.exists() and not any(legacy.rglob("*.json")):
            shutil.rmtree(legacy)
        for relative_path, content in generated.items():
            path = OUTPUT_ROOT / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            print(f"Wrote {path.relative_to(ROOT)} ({len(content)} bytes)")
        report = build_report(generated)
        write_json(ROOT / "reports" / "public_build_report.json", report)
        write_json(ROOT / "reports" / "remap_public_build.json", report)
        (ROOT / "reports" / "public_build_report.md").write_text(
            markdown_report(report), encoding="utf-8"
        )
        (ROOT / "reports" / "remap_public_build.md").write_text(
            markdown_report(report), encoding="utf-8"
        )
        if not report["initial_transfer_within_budget"]:
            raise ValueError("initial transfer exceeds the 500 KB budget")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Public build failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
