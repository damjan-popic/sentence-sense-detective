#!/usr/bin/env python3
"""Replay all 106 Martin-reviewed cases through the formal remap engine."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from formal_remap_engine import FormalRemapEngine
from pipeline_common import ROOT, write_json, write_jsonl

CONTRACT = ROOT / "data/remap/en/martin_contract_106.json"
EXPECTATIONS = ROOT / "data/gold/remapping_contract_106.json"
SOURCE_FIXTURE = ROOT / "data/gold/remapping_stanza_1.14.0.jsonl"
DATA_FIXTURE = ROOT / "data/remap/en/gold_replay_stanza.jsonl"
TEST_FIXTURE = ROOT / "tests/fixtures/martin_106_stanza.jsonl"
DEFAULT_RESULTS = ROOT / "data/remap/en/gold_replay_results.jsonl"
DEFAULT_REPORT = ROOT / "reports/remap_gold_replay.json"
DEFAULT_MARKDOWN = ROOT / "reports/remap_gold_replay.md"

DIMENSION_MAP = {
    "sentence_element": "sentence_element",
    "clause_class": "clause_type",
    "marker_type": "clause_marker",
    "clause_structure": "clause_structure",
    "clause_function": "clause_function",
}


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def span_texts(text: str, spans: list[dict]) -> list[str]:
    return [text[span["start"] : span["end"]] for span in spans]


def result_status(
    candidate: dict | None,
    expected_answer: str,
    expected_spans: list[dict],
    expected_action: str,
) -> str:
    if candidate is None:
        return "parser_mismatch"
    if candidate["answer"] != expected_answer:
        return "label_mismatch"
    if candidate["target_spans"] != expected_spans:
        return "span_mismatch"
    if candidate["action"] != expected_action:
        return "action_mismatch"
    return "matched"


def markdown(report: dict) -> str:
    lines = [
        "# Formal remap gold replay",
        "",
        f"- Profile: `{report['profile_id']}`",
        f"- Profile SHA-256: `{report['profile_sha256']}`",
        f"- Cases replayed: {report['case_count']}",
        f"- Matched: {report['status_counts'].get('matched', 0)}",
        f"- Parser mismatches: {report['status_counts'].get('parser_mismatch', 0)}",
        f"- Label mismatches: {report['status_counts'].get('label_mismatch', 0)}",
        f"- Span mismatches: {report['status_counts'].get('span_mismatch', 0)}",
        f"- Action mismatches: {report['status_counts'].get('action_mismatch', 0)}",
        (
            "- Manual-review cases auto-published: "
            f"{report['manual_cases_auto_published']}"
        ),
        "",
        "## Non-matches",
        "",
    ]
    failures = [row for row in report["results"] if row["status"] != "matched"]
    if not failures:
        lines.append("- None.")
    else:
        for row in failures:
            lines.append(
                f"- `{row['case_id']}`: {row['status']} "
                f"(rules: {', '.join(row['matched_rule_ids']) or 'none'})"
            )
    lines.append("")
    return "\n".join(lines)


def replay(engine: FormalRemapEngine) -> tuple[list[dict], dict]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expectation_document = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    expectations = {
        case["id"]: case for case in expectation_document["cases"]
    }
    fixtures = {
        row["sentence"]: row for row in read_jsonl(SOURCE_FIXTURE)
    }
    results = []
    for case in contract["cases"]:
        case_id = case["case_id"]
        expectation = expectations[case_id]
        public = expectation["public_contract"]
        expected_decision = case["reference"]["expected_decision"]
        expected_action = (
            "review"
            if expected_decision == "Needs manual review"
            else "publish"
        )
        if case_id == "CL-MARK-10":
            rules = [
                rule
                for rule in engine.rules
                if case_id in rule["source_case_ids"]
            ]
            candidate = (
                {
                    "answer": rules[0]["output"]["label"],
                    "target_spans": [],
                    "action": rules[0]["action"],
                    "rule_id": rules[0]["rule_id"],
                    "source_case_ids": rules[0]["source_case_ids"],
                }
                if rules
                else None
            )
            fixture = fixtures[case["example"]]
            candidates = []
        else:
            fixture = fixtures[case["example"]]
            metadata = fixture.get("annotation", {})
            candidates = (
                engine.sentence_element_specs(
                    fixture["tokens"],
                    case["example"],
                    metadata,
                )
                if public["dimension"] == "sentence_element"
                else engine.clause_specs(
                    fixture["tokens"],
                    case["example"],
                    metadata,
                )
            )
            dimension = DIMENSION_MAP[public["dimension"]]
            exact_case_candidates = [
                item
                for item in candidates
                if case_id in item["source_case_ids"]
                and item["dimension"] == dimension
            ]
            candidate = next(
                (
                    item
                    for item in exact_case_candidates
                    if item["answer"] == public["answer"]
                    and item["target_spans"] == public["target_spans"]
                ),
                exact_case_candidates[0] if exact_case_candidates else None,
            )
        status = (
            (
                "parser_mismatch"
                if candidate is None
                else "label_mismatch"
                if candidate["answer"] != public["answer"]
                else "action_mismatch"
                if candidate["action"] != expected_action
                else "matched"
            )
            if case_id == "CL-MARK-10"
            else result_status(
                candidate,
                public["answer"],
                public["target_spans"],
                expected_action,
            )
        )
        results.append(
            {
                "case_id": case_id,
                "source_item_id": case["source_item_id"],
                "sentence": case["example"],
                "focus_span": case["focus_span"],
                "expected_decision": expected_decision,
                "expected_action": expected_action,
                "expected_dimension": public["dimension"],
                "expected_answer": public["answer"],
                "expected_target_spans": public["target_spans"],
                "expected_target_texts": public["target_texts"],
                "matched_rule_ids": (
                    [candidate["rule_id"]] if candidate else []
                ),
                "matched_source_case_ids": (
                    candidate.get("source_case_ids", []) if candidate else []
                ),
                "actual_action": candidate.get("action") if candidate else None,
                "actual_answer": candidate.get("answer") if candidate else None,
                "actual_target_spans": (
                    candidate.get("target_spans", []) if candidate else []
                ),
                "actual_target_texts": (
                    span_texts(
                        case["example"],
                        candidate.get("target_spans", []),
                    )
                    if candidate
                    else []
                ),
                "parser_mismatch": status == "parser_mismatch",
                "target_disposition": (
                    "non-highlightable zero marker; no synthetic source span"
                    if case_id == "CL-MARK-10"
                    else "overt source span"
                ),
                "status": status,
                "martin_comment": case.get("martin_comment"),
            }
        )
    statuses = Counter(row["status"] for row in results)
    report = {
        "profile_id": engine.profile_id,
        "profile_sha256": engine.profile_sha256,
        "case_count": len(results),
        "decision_counts": dict(
            sorted(
                Counter(row["expected_decision"] for row in results).items()
            )
        ),
        "status_counts": dict(sorted(statuses.items())),
        "manual_cases_auto_published": sum(
            row["expected_action"] == "review"
            and row["actual_action"] == "publish"
            for row in results
        ),
        "results": results,
    }
    return results, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        DATA_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        TEST_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_FIXTURE, DATA_FIXTURE)
        shutil.copyfile(SOURCE_FIXTURE, TEST_FIXTURE)
        results, report = replay(FormalRemapEngine())
        write_jsonl(args.results, results)
        write_json(args.report, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(report), encoding="utf-8")
        print(
            f"Replayed {len(results)} cases: "
            + ", ".join(
                f"{key}={value}"
                for key, value in sorted(report["status_counts"].items())
            )
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Gold replay failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
