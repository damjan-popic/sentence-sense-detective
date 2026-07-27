#!/usr/bin/env python3
"""Validate the canonical imported formal-remap contract without rewriting it."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter

from pipeline_common import ROOT

DATA_ROOT = ROOT / "data/remap/en"
CONTRACT_PATH = DATA_ROOT / "martin_contract_106.json"
TSV_PATH = DATA_ROOT / "martin_contract_106.tsv"
SEED_PATH = DATA_ROOT / "case_to_rule_seed.json"
SCHEMA_PATH = ROOT / "config/remap/en/rule.schema.json"
IMPORT_REPORT_PATH = DATA_ROOT / "import_report.json"
EXPECTED_CONTRACT_SHA256 = (
    "6b3be571df252b662e2df5f0f4ea8063714f71535728fccc878f35f056dc2e4f"
)
EXPECTED_SOURCE_SHA256 = (
    "f62fcfcdc35d43d8425b63266b86ae54c3bd688d37ca5e47e0dab432f767a51d"
)
EXPECTED_DECISIONS = Counter(
    {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20}
)


def validate() -> dict:
    contract_bytes = CONTRACT_PATH.read_bytes()
    if hashlib.sha256(contract_bytes).hexdigest() != EXPECTED_CONTRACT_SHA256:
        raise ValueError("canonical formal contract SHA-256 differs")
    contract = json.loads(contract_bytes)
    report = json.loads(IMPORT_REPORT_PATH.read_text(encoding="utf-8"))
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cases = contract["cases"]
    case_ids = [case["case_id"] for case in cases]
    decisions = Counter(
        case["reference"]["expected_decision"] for case in cases
    )
    if len(cases) != 106 or len(set(case_ids)) != 106:
        raise ValueError("formal contract must contain 106 unique cases")
    if decisions != EXPECTED_DECISIONS:
        raise ValueError(f"unexpected decision counts: {dict(decisions)}")
    if contract["metadata"]["source_sha256"] != EXPECTED_SOURCE_SHA256:
        raise ValueError("source workbook SHA-256 differs")
    if report.get("contract_sha256") != EXPECTED_CONTRACT_SHA256:
        raise ValueError("import report contract SHA-256 differs")
    if [row["case_id"] for row in seed["rows"]] != case_ids:
        raise ValueError("case-to-rule seed order differs from the contract")
    with TSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        tsv_ids = [row["case_id"] for row in csv.DictReader(handle, delimiter="\t")]
    if tsv_ids != case_ids:
        raise ValueError("TSV and JSON contract case orders differ")
    if (
        not schema.get("$id")
        or schema.get("title")
        != "Sentence Sense Detective formal remapping rule"
    ):
        raise ValueError("formal rule schema identity is invalid")
    return {
        "case_count": len(cases),
        "decision_counts": dict(sorted(decisions.items())),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "contract_sha256": EXPECTED_CONTRACT_SHA256,
    }


def main() -> int:
    try:
        result = validate()
        print(
            "Formal contract validation passed: "
            f"{result['case_count']} cases, "
            f"source SHA-256 {result['source_sha256']}."
        )
        return 0
    except (OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as error:
        print(f"Formal contract validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
