#!/usr/bin/env python3
"""Prepare deterministic rows for the full review pack and 100-question sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from pipeline_common import ROOT, SEED, read_jsonl, write_json

DEFAULT_INPUT = ROOT / "data" / "generated" / "question_candidates.jsonl"
DEFAULT_ROWS = ROOT / "external" / "review" / "review_pack_rows.json"
DEFAULT_SAMPLE = ROOT / "external" / "review" / "review_sample_100_rows.json"

HEADERS = [
    "question ID",
    "sentence ID",
    "genre",
    "sentence",
    "highlighted target",
    "mode",
    "subskill",
    "proposed answer",
    "four options",
    "explanation",
    "confidence",
    "rule ID",
    "accept / correct / reject",
    "corrected target",
    "corrected answer",
    "corrected explanation",
    "reviewer",
    "review date",
    "note",
]


def target_text(question: dict) -> str:
    return " … ".join(
        question["sentence"][span["start"]:span["end"]]
        for span in question["target_spans"]
    )


def review_row(question: dict) -> list:
    return [
        question["question_id"],
        question["sentence_id"],
        question["genre"],
        question["sentence"],
        target_text(question),
        question["mode"],
        question["subskill"],
        question["answer"],
        "\n".join(question["options"]),
        question["explanation"],
        float(question["confidence"]),
        question["rule_id"],
        "",
        "",
        "",
        "",
        "",
        None,
        "",
    ]


def sample_key(question: dict) -> str:
    return hashlib.sha256(
        f"{SEED}\0review-sample\0{question['question_id']}".encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--sample-size", type=int, default=100)
    args = parser.parse_args()
    try:
        questions = list(read_jsonl(args.input))
        if not questions:
            raise ValueError("question candidate input is empty")
        payload = {
            "headers": HEADERS,
            "rows": [review_row(question) for question in questions],
            "metadata": {
                "seed": SEED,
                "candidate_count": len(questions),
                "purpose": "full generated-candidate review pack",
            },
        }
        sample_questions = sorted(questions, key=sample_key)[: args.sample_size]
        sample = {
            "headers": HEADERS,
            "rows": [review_row(question) for question in sample_questions],
            "metadata": {
                "seed": SEED,
                "sample_count": len(sample_questions),
                "candidate_count": len(questions),
                "purpose": "deterministic 100-question dry-run review sample",
            },
        }
        write_json(args.rows, payload)
        write_json(args.sample, sample)
        print(
            f"Prepared {len(questions)} review rows and a "
            f"{len(sample_questions)}-question sample."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Review-row preparation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
