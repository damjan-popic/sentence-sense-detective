#!/usr/bin/env python3
"""Build the browser-safe Sentence Sense Detective question payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "questions.json"
PUBLIC_JSON = ROOT / "docs" / "data" / "questions.json"
PUBLIC_JS = ROOT / "docs" / "data" / "questions.js"

PUBLIC_QUESTION_FIELDS = (
    "id",
    "language",
    "mode",
    "subskill",
    "sentence",
    "targets",
    "prompt",
    "answer",
    "options",
    "explanation",
)
PUBLIC_METADATA_FIELDS = (
    "title",
    "language",
    "version",
    "round_size",
    "question_count",
    "scoring",
)


def build_payload() -> dict:
    canonical = json.loads(SOURCE.read_text(encoding="utf-8"))
    public_metadata = {
        field: canonical["metadata"][field]
        for field in PUBLIC_METADATA_FIELDS
    }
    public_questions = [
        {field: question[field] for field in PUBLIC_QUESTION_FIELDS}
        for question in canonical["questions"]
    ]
    return {
        "metadata": public_metadata,
        "modes": canonical["modes"],
        "questions": public_questions,
    }


def rendered_files(payload: dict) -> tuple[str, str]:
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    js_text = (
        "window.SENTENCE_SENSE_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    return json_text, js_text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed public copies are stale",
    )
    args = parser.parse_args()

    payload = build_payload()
    expected_json, expected_js = rendered_files(payload)

    if args.check:
        failures = []
        if not PUBLIC_JSON.exists() or PUBLIC_JSON.read_text(encoding="utf-8") != expected_json:
            failures.append(str(PUBLIC_JSON.relative_to(ROOT)))
        if not PUBLIC_JS.exists() or PUBLIC_JS.read_text(encoding="utf-8") != expected_js:
            failures.append(str(PUBLIC_JS.relative_to(ROOT)))
        if failures:
            print("Public data is stale: " + ", ".join(failures), file=sys.stderr)
            print("Run: python scripts/build_public_data.py", file=sys.stderr)
            return 1
        print("Public data is up to date.")
        return 0

    PUBLIC_JSON.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_JSON.write_text(expected_json, encoding="utf-8")
    PUBLIC_JS.write_text(expected_js, encoding="utf-8")
    print(f"Wrote {PUBLIC_JSON.relative_to(ROOT)}")
    print(f"Wrote {PUBLIC_JS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
