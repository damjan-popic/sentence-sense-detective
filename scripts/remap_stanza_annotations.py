#!/usr/bin/env python3
"""Materialise formal pedagogical candidates from pinned Stanza annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from formal_remap_engine import FormalRemapEngine
from pipeline_common import ROOT, read_jsonl, write_json, write_jsonl

DEFAULT_SENTENCES = ROOT / "data/corpus/sentences_10k.jsonl"
DEFAULT_ANNOTATIONS = ROOT / "data/corpus/sentences_10k.annotations.jsonl"
DEFAULT_OUTPUT = ROOT / "data/remap/en/pedagogical_candidates_10k.jsonl.gz"
DEFAULT_REPORT = ROOT / "data/remap/en/remap_10k_report.json"


def stable_id(sentence_id: str, item: dict) -> str:
    key = json.dumps(
        [
            sentence_id,
            item["dimension"],
            item["target_spans"],
            item["remap_rule_id"],
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "REMAP-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def remap(
    sentences: list[dict],
    annotations: list[dict],
    engine: FormalRemapEngine,
) -> tuple[list[dict], dict]:
    annotation_by_id = {
        record["sentence_id"]: record for record in annotations
    }
    records = []
    sentence_actions = {}
    for index, sentence in enumerate(sentences, 1):
        annotation = annotation_by_id.get(sentence["sentence_id"])
        if not annotation or annotation.get("text") != sentence["text"]:
            raise ValueError(
                f"{sentence['sentence_id']}: annotation text mismatch"
            )
        words = annotation["tokens"]
        metadata = annotation.get("annotation", {})
        items = [
            *engine.word_class_specs(words, metadata),
            *engine.sentence_element_specs(words, sentence["text"], metadata),
            *engine.clause_specs(words, sentence["text"], metadata),
        ]
        actions = Counter(item["action"] for item in items)
        sentence_actions[sentence["sentence_id"]] = actions
        for item in items:
            records.append(
                {
                    "remap_candidate_id": stable_id(
                        sentence["sentence_id"], item
                    ),
                    "sentence_id": sentence["sentence_id"],
                    **item,
                }
            )
        if index % 1000 == 0:
            print(
                f"Formally remapped {index}/{len(sentences)} sentences.",
                flush=True,
            )
    records.sort(key=lambda item: item["remap_candidate_id"])
    report = {
        "profile_id": engine.profile_id,
        "profile_sha256": engine.profile_sha256,
        "sentence_count": len(sentences),
        "candidate_count": len(records),
        "action_counts": dict(
            sorted(Counter(item["action"] for item in records).items())
        ),
        "dimension_counts": dict(
            sorted(Counter(item["dimension"] for item in records).items())
        ),
        "rule_counts": dict(
            sorted(Counter(item["remap_rule_id"] for item in records).items())
        ),
        "sentences_without_publishable_candidate": sum(
            actions.get("publish", 0) == 0
            for actions in sentence_actions.values()
        ),
    }
    return records, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", type=Path, default=DEFAULT_SENTENCES)
    parser.add_argument(
        "--annotations", type=Path, default=DEFAULT_ANNOTATIONS
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        records, report = remap(
            list(read_jsonl(args.sentences)),
            list(read_jsonl(args.annotations)),
            FormalRemapEngine(),
        )
        write_jsonl(args.output, records)
        write_json(args.report, report)
        print(
            f"Wrote {len(records)} formal candidates: "
            + ", ".join(
                f"{key}={value}"
                for key, value in report["action_counts"].items()
            )
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Formal 10K remap failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
