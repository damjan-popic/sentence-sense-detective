#!/usr/bin/env python3
"""Report metadata-only sharding capacity without creating corpus text."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from corpus_io import write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentence-count", type=int, default=10_000)
    parser.add_argument("--sentence-shard-size", type=int, default=500)
    parser.add_argument("--public-question-shard-size", type=int, default=400)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if min(
        args.sentence_count,
        args.sentence_shard_size,
        args.public_question_shard_size,
    ) < 1:
        parser.error("all counts must be positive")
    report = {
        "kind": "metadata-only capacity dry run",
        "hypothetical_sentence_count": args.sentence_count,
        "corpus_materialized": False,
        "corpus_supplied": False,
        "source_rights_confirmed": False,
        "sentence_shard_size": args.sentence_shard_size,
        "hypothetical_sentence_shards": math.ceil(
            args.sentence_count / args.sentence_shard_size
        ),
        "public_question_shard_size": args.public_question_shard_size,
        "hypothetical_question_count": None,
        "hypothetical_public_question_shards": None,
        "stop_condition": (
            "Question and byte totals require a team-supplied corpus with confirmed "
            "licensing; no sentences were sourced, generated, or published."
        ),
    }
    if args.output:
        write_json(args.output, report)
    print(f"Hypothetical sentences: {args.sentence_count}")
    print(f"Sentence shards at {args.sentence_shard_size} records: "
          f"{report['hypothetical_sentence_shards']}")
    print("Question/shard byte totals: unknown until a licensed corpus is supplied.")
    print("No corpus text was sourced, generated, written, or published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
