#!/usr/bin/env python3
"""Import and validate the authoritative formal-remap handover package."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from pipeline_common import ROOT

PACKAGE_PREFIX = "sentence_sense_detective_formal_remap_handover"
MEMBERS = {
    "CODEX_HANDOVER_FORMAL_REMAP_ENGINE.md": (
        ROOT / "CODEX_HANDOVER_FORMAL_REMAP_ENGINE.md"
    ),
    "contracts/martin_reviewed_remap_contract_106.json": (
        ROOT / "data/remap/en/martin_contract_106.json"
    ),
    "contracts/martin_reviewed_remap_contract_106.tsv": (
        ROOT / "data/remap/en/martin_contract_106.tsv"
    ),
    "contracts/case_to_rule_matrix_seed.json": (
        ROOT / "data/remap/en/case_to_rule_seed.json"
    ),
    "schema/formal_remap_rule.schema.json": (
        ROOT / "config/remap/en/rule.schema.json"
    ),
}
EXPECTED_SOURCE_SHA256 = (
    "f62fcfcdc35d43d8425b63266b86ae54c3bd688d37ca5e47e0dab432f767a51d"
)
EXPECTED_DECISIONS = Counter(
    {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20}
)


def package_member(relative: str) -> str:
    return str(PurePosixPath(PACKAGE_PREFIX) / relative)


def validate_payloads(payloads: dict[str, bytes]) -> dict:
    contract = json.loads(
        payloads["contracts/martin_reviewed_remap_contract_106.json"]
    )
    seed = json.loads(payloads["contracts/case_to_rule_matrix_seed.json"])
    cases = contract.get("cases", [])
    metadata = contract.get("metadata", {})
    case_ids = [case.get("case_id") for case in cases]
    decisions = Counter(
        case.get("reference", {}).get("expected_decision") for case in cases
    )
    seed_ids = [row.get("case_id") for row in seed.get("rows", [])]
    if metadata.get("source_sha256") != EXPECTED_SOURCE_SHA256:
        raise ValueError("formal-remap contract records an unexpected workbook hash")
    if len(cases) != 106 or len(set(case_ids)) != 106:
        raise ValueError("formal-remap contract must contain 106 unique case IDs")
    if decisions != EXPECTED_DECISIONS:
        raise ValueError(f"unexpected decision inventory: {dict(decisions)}")
    if seed_ids != case_ids:
        raise ValueError("case-to-rule seed order/IDs differ from the contract")
    return {
        "contract_version": metadata.get("contract_version"),
        "source_file": metadata.get("source_file"),
        "source_sha256": metadata.get("source_sha256"),
        "case_count": len(cases),
        "decision_counts": dict(sorted(decisions.items())),
        "contract_sha256": hashlib.sha256(
            payloads["contracts/martin_reviewed_remap_contract_106.json"]
        ).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    with ZipFile(args.package) as archive:
        payloads = {
            relative: archive.read(package_member(relative))
            for relative in MEMBERS
        }
    report = validate_payloads(payloads)
    for relative, destination in MEMBERS.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payloads[relative])
        print(f"Wrote {destination.relative_to(ROOT)}")
    report_path = ROOT / "data/remap/en/import_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "Imported formal-remap contract: "
        f"{report['case_count']} cases, source SHA-256 {report['source_sha256']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
