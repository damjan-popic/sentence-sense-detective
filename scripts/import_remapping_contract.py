#!/usr/bin/env python3
"""Import the reviewed UD-to-pedagogical contract without private review notes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from pipeline_common import ROOT, canonical_json_bytes, read_jsonl, write_json, write_jsonl

DEFAULT_OUTPUT = ROOT / "data" / "gold" / "remapping_contract_106.json"
DEFAULT_FIXTURE = ROOT / "data" / "gold" / "remapping_stanza_1.14.0.jsonl"
SAFE_FIELDS = (
    "id",
    "language",
    "dimension",
    "dimension_label",
    "ud_signal",
    "sentence",
    "focus",
    "gold_mapping",
    "answer_code",
    "mapping_kind",
    "manual_review",
    "rule",
    "explanation",
    "teaching_note",
    "dimension_note",
    "features",
    "review_status",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_public_contract() -> dict[str, dict]:
    questions = {
        item["id"]: item
        for item in read_jsonl(ROOT / "data" / "questions" / "en" / "reviewed-core.jsonl")
    }
    annotations = {
        item["id"]: item
        for item in read_jsonl(
            ROOT / "data" / "annotations" / "en" / "pedagogical-annotations.jsonl"
        )
    }
    sentences = {
        item["id"]: item
        for item in read_jsonl(ROOT / "data" / "corpus" / "en" / "sentences-0001.jsonl")
    }
    result = {}
    for identifier, question in questions.items():
        annotation = annotations[question["annotation_id"]]
        sentence = sentences[question["sentence_id"]]
        result[identifier] = {
            "mode": question["mode"],
            "subskill": question["subskill"],
            "dimension": annotation["dimension"],
            "answer": question["answer"],
            "target_spans": annotation["target_spans"],
            "target_texts": [
                sentence["text"][span["start"]:span["end"]]
                for span in annotation["target_spans"]
            ],
        }
    return result


def import_contract(source: Path) -> dict:
    raw = json.loads(source.read_text(encoding="utf-8"))
    cases = raw.get("cases")
    if not isinstance(cases, list) or len(cases) != 106:
        raise ValueError("the remapping source must contain exactly 106 cases")
    if len({case.get("id") for case in cases}) != 106:
        raise ValueError("the remapping source contains duplicate or missing IDs")
    public = canonical_public_contract()
    if set(public) != {case["id"] for case in cases}:
        raise ValueError("reviewed question IDs do not match the remapping source")
    safe_cases = []
    for case in cases:
        safe = {field: case.get(field) for field in SAFE_FIELDS}
        safe["public_contract"] = public[case["id"]]
        safe_cases.append(safe)
    mapping_digest = hashlib.sha256(
        canonical_json_bytes(
            [
                {
                    field: case[field]
                    for field in (
                        "id",
                        "dimension",
                        "ud_signal",
                        "gold_mapping",
                        "answer_code",
                        "mapping_kind",
                        "manual_review",
                        "rule",
                        "features",
                    )
                }
                for case in safe_cases
            ]
        )
    ).hexdigest()
    return {
        "metadata": {
            "title": raw["metadata"]["title"],
            "version": raw["metadata"]["version"],
            "case_count": 106,
            "source_sha256": sha256(source),
            "mapping_contract_sha256": mapping_digest,
            "private_review_fields_removed": ["source_review_note_sl"],
            "purpose": (
                "Internal regression contract for the pedagogical remapper; "
                "never copied into docs/."
            ),
        },
        "cases": safe_cases,
    }


def fixture_records(contract: dict, stanza_path: Path) -> list[dict]:
    parsed = json.loads(stanza_path.read_text(encoding="utf-8"))
    parses = parsed.get("parses", {})
    case_ids: dict[str, list[str]] = defaultdict(list)
    for case in contract["cases"]:
        case_ids[case["sentence"]].append(case["id"])
    if set(case_ids) != set(parses):
        missing = sorted(set(case_ids) - set(parses))
        extra = sorted(set(parses) - set(case_ids))
        raise ValueError(
            f"Stanza fixture sentence mismatch; missing={missing[:3]}, extra={extra[:3]}"
        )
    return [
        {
            "sentence": sentence,
            "case_ids": sorted(case_ids[sentence]),
            "annotation": {
                "engine": "stanza",
                "stanza_version": "1.14.0",
                "package": "combined",
                "processors": ["tokenize", "mwt", "pos", "lemma", "depparse"],
            },
            "tokens": parses[sentence],
        }
        for sentence in sorted(case_ids)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stanza-parses", type=Path)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    try:
        contract = import_contract(args.source.resolve())
        write_json(args.output, contract)
        if args.stanza_parses:
            records = fixture_records(contract, args.stanza_parses.resolve())
            write_jsonl(args.fixture, records)
            print(
                f"Wrote {args.output} and {args.fixture} "
                f"({len(records)} unique regression sentences)."
            )
        else:
            print(f"Wrote {args.output}.")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Remapping contract import failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
