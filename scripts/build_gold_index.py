#!/usr/bin/env python3
"""Materialise the immutable 106-question reviewed reference index."""

from __future__ import annotations

import shutil
from pathlib import Path

from pipeline_common import ROOT, read_jsonl, sha256_file, write_json

SOURCE = ROOT / "data" / "questions" / "en" / "reviewed-core.jsonl"
OUTPUT = ROOT / "data" / "gold" / "reviewed_106.jsonl"
INDEX = ROOT / "data" / "gold" / "index.json"


def main() -> int:
    records = list(read_jsonl(SOURCE))
    if len(records) != 106 or len({record["id"] for record in records}) != 106:
        raise ValueError("the reviewed source must contain exactly 106 unique question IDs")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, OUTPUT)
    write_json(
        INDEX,
        {
            "version": "1.0.0",
            "question_count": 106,
            "source": str(SOURCE.relative_to(ROOT)),
            "file": str(OUTPUT.relative_to(ROOT)),
            "sha256": sha256_file(OUTPUT),
            "locked_contracts": {
                "reviewed_mapping_contract_sha256": (
                    "a6a15b586f8542e9792194e8f745951ef19c6030abf1fe1c71cdc8f41ff5d9a8"
                ),
                "highlight_contract_sha256": (
                    "3688077b0bf6e345e98ef88e85afc734660a79cf893ff2a1c9ffbe09a92d3a39"
                ),
            },
        },
    )
    print(f"Wrote immutable gold index for {len(records)} reviewed questions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
